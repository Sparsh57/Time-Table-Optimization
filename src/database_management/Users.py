import pandas as pd
from .dbconnection import get_db_session, create_tables, is_postgresql, get_organization_database_url
from .models import User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def parse_faculty_names(faculty_name_str):
    """
    Parse faculty names separated by commas, ampersands, or both and return a list of cleaned names.
    
    :param faculty_name_str: String containing one or more faculty names separated by commas, ampersands, or both
    :return: List of faculty names
    """
    if pd.isna(faculty_name_str):
        return []
    
    # Handle both comma and ampersand separators
    faculty_str = str(faculty_name_str)
    
    # First split by commas, then by ampersands
    names = []
    for part in faculty_str.split(','):
        for name in part.split('&'):
            cleaned_name = name.strip()
            if cleaned_name:  # Remove empty strings
                names.append(cleaned_name)
    
    return names


def insert_user_data(list_files, db_path):
    """
    Inserts user data (professors and students) using bulk operations.

    :param list_files: A tuple containing two DataFrames:
                       - course_data: DataFrame with faculty information.
                       - stud_course_data: DataFrame with student registration data.
    :param db_path: Path to the database file or schema identifier.
    """
    print("Bulk inserting user data")
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    course_data, stud_course_data = list_files

    # Process professor data - parse multiple professors per course
    all_professors = set()
    for faculty_name_str in course_data['Faculty Name'].dropna():
        professors = parse_faculty_names(faculty_name_str)
        all_professors.update(professors)
    
    # Convert to list of dictionaries for bulk insert
    prof_data = []
    for prof_name in all_professors:
        prof_data.append({
            'Email': prof_name,
            'Name': prof_name,
            'Role': 'Professor'
        })

    # Process student data
    filtered_stud_column = stud_course_data['Roll No.'].dropna().drop_duplicates()
    stud_data = []
    for student_email in filtered_stud_column:
        stud_data.append({
            'Email': student_email,
            'Name': student_email,  # Using email as name for now
            'Role': 'Student'
        })

    # Combine all user data
    all_users = prof_data + stud_data
    print(f"Prepared {len(all_users)} users for bulk insertion ({len(prof_data)} professors, {len(stud_data)} students)")

    # First, ensure tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Users\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        logger.info("Users table not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        logger.info("Tables created successfully")

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            # Get existing users to avoid duplicates
            existing_emails = {user.Email for user in session.query(User.Email).all()}
            
            # Filter out existing users
            new_users = [user for user in all_users if user['Email'] not in existing_emails]
            
            if new_users:
                # Bulk insert new users
                session.bulk_insert_mappings(User, new_users)
                session.commit()
                logger.info(f"Bulk inserted {len(new_users)} users into database")
                print(f"Successfully bulk inserted {len(new_users)} users")
            else:
                logger.info("No new users to insert")
                print("No new users to insert")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error bulk inserting user data: {e}")
            raise


def fetch_user_data(db_path):
    """
    Fetches user data of professors from the database using SQLAlchemy.

    :param db_path: Path to the database file or schema identifier.
    :return: List of tuples containing user data.
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            professors = session.query(User).filter_by(Role='Professor').all()
            result = [(prof.UserID, prof.Email, prof.Name, prof.Role) for prof in professors]
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user data: {e}")
            return []


def fetch_professor_emails(db_path):
    """
    Fetches email addresses of professors from the database using SQLAlchemy.

    :param db_path: Path to the database file or schema identifier.
    :return: List of email addresses.
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            professors = session.query(User.Email).filter_by(Role='Professor').all()
            emails = [prof.Email for prof in professors]
            return emails
        except SQLAlchemyError as e:
            logger.error(f"Error fetching professor emails: {e}")
            return []


def fetch_admin_emails(db_path):
    """
    Fetches email addresses of admins from the database using SQLAlchemy.

    :param db_path: Path to the database file or schema identifier.
    :return: List of email addresses.
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            admins = session.query(User.Email).filter_by(Role='Admin').all()
            emails = [admin.Email for admin in admins]
            return emails
        except SQLAlchemyError as e:
            logger.error(f"Error fetching admin emails: {e}")
            return []


def add_admin(user_name: str, email: str, db_path: str, role: str):
    """
    Adds an admin to the organization's database using SQLAlchemy.
    
    :param user_name: Name of the user
    :param email: Email of the user
    :param db_path: Path to the database file or schema identifier
    :param role: Role of the user (e.g., "Admin")
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            # Check if user already exists
            existing_user = session.query(User).filter_by(Email=email).first()
            if not existing_user:
                new_user = User(
                    Name=user_name,
                    Email=email,
                    Role=role
                )
                session.add(new_user)
                session.commit()
                print(f"{role} '{user_name}' added successfully to the database at {db_path}.")
            else:
                print(f"User with email {email} already exists in the database.")
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding admin: {e}")
            raise