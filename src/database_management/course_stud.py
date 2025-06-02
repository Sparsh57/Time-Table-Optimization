from .dbconnection import get_db_session
from .models import User, Course, CourseStud
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def insert_course_students(file, db_path):
    """
    Inserts student course enrollments from a CSV file into the database using SQLAlchemy.

    :param file: The CSV file containing student registration data.
    :param db_path: Path to the database file.
    """
    df_courses = file
    print(f"Inserting course students into database: {db_path}")

    with get_db_session(db_path) as session:
        try:
            # Fetch user information (UserID and Email) for students
            students = session.query(User).filter_by(Role='Student').all()
            student_dict = {student.Email: student.UserID for student in students}

            # Fetch available courses (CourseID and CourseName)
            courses = session.query(Course).all()
            course_dict = {course.CourseName: course.CourseID for course in courses}

            # Create a new DataFrame with relevant columns (G CODE and Roll No.)
            df_merged = df_courses[['G CODE', 'Roll No.', 'Sections']].copy()
            df_merged['UserID'] = np.nan
            df_merged['CourseID'] = np.nan

            # Map Roll No. to UserID using the student_dict
            for roll_no in df_merged["Roll No."]:
                try:
                    df_merged.loc[df_merged["Roll No."] == roll_no, "UserID"] = int(student_dict[roll_no])
                except KeyError:
                    continue

            # Map G CODE to CourseID using the course_dict
            for index, row in df_merged.iterrows():
                g_code = row["G CODE"]
                section = row["Sections"]

                try:
                    # Assuming the section is in parentheses like G CODE (Section)
                    course = g_code.replace(f"({section})", "").strip()

                    # Debugging output
                    if course != g_code:
                        print(f"Original G CODE: {g_code}, Processed Course: {course}")

                    # Map the cleaned course to CourseID
                    df_merged.loc[index, "CourseID"] = int(course_dict[course])

                except KeyError:
                    continue

            # Drop rows where either UserID or CourseID is missing (NaN values)
            df_merged.dropna(subset=['UserID', 'CourseID'], inplace=True)
            df_merged = df_merged[['UserID', 'CourseID']]

            # Convert UserID and CourseID to integers
            df_merged['UserID'] = df_merged['UserID'].astype(int)
            df_merged['CourseID'] = df_merged['CourseID'].astype(int)

            # Insert course-student relationships into the database
            for row in df_merged.itertuples(index=False, name=None):
                try:
                    # Check if relationship already exists
                    existing_enrollment = session.query(CourseStud).filter_by(
                        StudentID=row[0], 
                        CourseID=row[1]
                    ).first()
                    
                    if not existing_enrollment:
                        new_enrollment = CourseStud(
                            StudentID=row[0],
                            CourseID=row[1]
                        )
                        session.add(new_enrollment)
                except Exception as e:
                    logger.error(f"Error inserting enrollment for student {row[0]}, course {row[1]}: {e}")

            session.commit()
            logger.info(f"Inserted course-student enrollments into database")
            print("Course-student enrollments inserted successfully.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting course-student data: {e}")
            raise