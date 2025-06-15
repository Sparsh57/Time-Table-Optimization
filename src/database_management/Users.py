import pandas as pd
from .dbconnection import get_db_session, create_tables
from .models import User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def parse_faculty_names(faculty_name_str):
    """
    Parse ampersand-separated faculty names and return a list of cleaned names.
    
    :param faculty_name_str: String containing one or more faculty names separated by ampersands
    :return: List of faculty names
    """
    if pd.isna(faculty_name_str):
        return []
    
    # Split by ampersand and strip whitespace
    faculty_names = [name.strip() for name in str(faculty_name_str).split('&')]
    return [name for name in faculty_names if name]  # Remove empty strings


def insert_user_data(list_files, db_path):
    """
    Inserts user data (professors and students) into the database using SQLAlchemy.

    :param list_files: A tuple containing two DataFrames:
                       - course_data: DataFrame with faculty information.
                       - stud_course_data: DataFrame with student registration data.
    :param db_path: Path to the database file.
    """
    print("Inserting user data")
    
    course_data, stud_course_data = list_files

    # Process professor data - parse multiple professors per course
    all_professors = set()
    for faculty_name_str in course_data['Faculty Name'].dropna():
        professors = parse_faculty_names(faculty_name_str)
        all_professors.update(professors)
    
    # Convert to DataFrame
    prof_data = []
    for prof_name in all_professors:
        prof_data.append({
            'Email': prof_name,  # Using name as email for now
            'Name': prof_name,
            'Role': 'Professor'
        })
    
    filtered_prof_column = pd.DataFrame(prof_data)

    # Process student data
    filtered_stud_column = stud_course_data['Roll No.'].dropna().drop_duplicates()
    filtered_stud_column = pd.DataFrame(filtered_stud_column, columns=['Roll No.'])
    filtered_stud_column["Role"] = "Student"
    filtered_stud_column.rename(columns={'Roll No.': 'Email'}, inplace=True)
    # Use email as name for now (can be updated later if actual names are available)
    filtered_stud_column['Name'] = filtered_stud_column['Email']

    # Combine professor and student data
    final_data = pd.concat([filtered_prof_column, filtered_stud_column], ignore_index=True)

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Users table exists by querying it
            session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Users table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            for index, row in final_data.iterrows():
                # Check if user already exists
                existing_user = session.query(User).filter_by(Email=row['Email']).first()
                if not existing_user:
                    new_user = User(
                        Name=row['Name'],
                        Email=row['Email'],
                        Role=row['Role']
                    )
                    session.add(new_user)
            
            session.commit()
            logger.info(f"Inserted {len(final_data)} users into database")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting user data: {e}")
            raise


def fetch_user_data(db_path):
    """
    Fetches user data of professors from the database using SQLAlchemy.

    :param db_path: Path to the database file.
    :return: List of tuples containing user data.
    """
    with get_db_session(db_path) as session:
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

    :param db_path: Path to the database file.
    :return: List of email addresses.
    """
    with get_db_session(db_path) as session:
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

    :param db_path: Path to the database file.
    :return: List of email addresses.
    """
    with get_db_session(db_path) as session:
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
    :param db_path: Path to the database file
    :param role: Role of the user (e.g., "Admin")
    """
    with get_db_session(db_path) as session:
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