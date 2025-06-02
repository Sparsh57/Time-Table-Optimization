import pandas as pd
from .dbconnection import get_db_session
from .models import User
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


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

    # Process professor data
    filtered_prof_column = course_data['Faculty Name'].dropna().drop_duplicates()
    filtered_prof_column = pd.DataFrame(filtered_prof_column, columns=['Faculty Name'])
    filtered_prof_column["Role"] = "Professor"
    filtered_prof_column.rename(columns={'Faculty Name': 'Email'}, inplace=True)

    # Process student data
    filtered_stud_column = stud_course_data['Roll No.'].dropna().drop_duplicates()
    filtered_stud_column = pd.DataFrame(filtered_stud_column, columns=['Roll No.'])
    filtered_stud_column["Role"] = "Student"
    filtered_stud_column.rename(columns={'Roll No.': 'Email'}, inplace=True)

    # Combine professor and student data
    final_data = pd.concat([filtered_prof_column, filtered_stud_column])
    final_data.reset_index(drop=True, inplace=True)
    # Use email as name for now (can be updated later if actual names are available)
    final_data['Name'] = final_data['Email']

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