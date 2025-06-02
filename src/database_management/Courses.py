from .dbconnection import get_db_session
from .models import User, Course
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def map_course_type(course_type):
    """
    Maps the course type to either 'Elective' or 'Required'.

    :param course_type: The original course type value.
    :return: 'Elective' if 'Elective' is in the value, else 'Required'.
    """
    if 'Elective' in course_type:
        return 'Elective'
    else:
        return 'Required'


def insert_courses_professors(file, db_path):
    """
    Inserts course information associated with professors from a CSV file into the database using SQLAlchemy.

    :param file: The CSV file containing courses and faculty names.
    :param db_path: Path to the database file.
    """
    print("INSERTING COURSES")
    df_courses = file

    with get_db_session(db_path) as session:
        try:
            # Fetch user information (UserID and Email) for professors
            professors = session.query(User).filter_by(Role='Professor').all()
            prof_dict = {prof.Email: prof.UserID for prof in professors}

            # Create a new DataFrame with relevant columns (Course code and Faculty Name)
            df_merged = df_courses[['Course code', 'Faculty Name', 'Type', 'Credits']].copy()
            df_merged['UserID'] = np.nan

            # Map Faculty Name to UserID
            for faculty_name in df_merged["Faculty Name"]:
                try:
                    df_merged.loc[df_merged["Faculty Name"] == faculty_name, "UserID"] = int(prof_dict[faculty_name])
                except KeyError:
                    continue

            # Apply the mapping function to convert Course Type to either 'Elective' or 'Required'
            df_merged['Course Type'] = df_merged['Type'].apply(map_course_type)

            # Keep only relevant columns and rename
            df_merged = df_merged[['Course code', 'UserID', 'Course Type', 'Credits']]
            df_merged.rename(columns={'Course code': 'Course', 'Course Type': 'Type'}, inplace=True)

            # Drop rows with missing UserID
            df_merged.dropna(inplace=True)
            df_merged['UserID'] = df_merged['UserID'].astype(int)

            # Insert courses into the database
            for row in df_merged.itertuples(index=False):
                try:
                    # Check if course already exists
                    existing_course = session.query(Course).filter_by(CourseName=row.Course).first()
                    if not existing_course:
                        new_course = Course(
                            CourseName=row.Course,
                            ProfessorID=row.UserID,
                            CourseType=row.Type,
                            Credits=row.Credits
                        )
                        session.add(new_course)
                except Exception as e:
                    logger.error(f"Error inserting course {row.Course}: {e}")

            session.commit()
            logger.info(f"Inserted courses into database")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting courses: {e}")
            raise


def fetch_course_data(db_path):
    """
    Fetches all course data from the Courses table using SQLAlchemy.

    :param db_path: Path to the database file.
    :return: List of all course data.
    """
    with get_db_session(db_path) as session:
        try:
            courses = session.query(Course).all()
            result = [(course.CourseID, course.CourseName, course.ProfessorID, 
                      course.CourseType, course.Credits) for course in courses]
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching course data: {e}")
            return []