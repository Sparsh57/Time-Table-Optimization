from .dbconnection import get_db_session, create_tables
from .models import User, Course, CourseStud
from .section_allocation import run_section_allocation
from .migration import migrate_database_for_sections, check_migration_needed
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def insert_course_students(file, db_path):
    """
    Inserts student course enrollments using bulk operations.
    Includes section allocation for multi-section courses.

    :param file: The CSV file containing student registration data.
    :param db_path: Path to the database file.
    """
    df_courses = file
    print(f"Bulk inserting course students into database: {db_path}")

    # Check if migration is needed and run it
    if check_migration_needed(db_path):
        print("Database migration needed for sections support...")
        migrate_database_for_sections(db_path)
        print("Database migration completed.")

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Course_Stud table exists by querying it
            session.execute(text("SELECT 1 FROM Course_Stud LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Course_Stud table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

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
            
            # Prepare data for bulk insert
            enrollments_to_insert = []

            # Process enrollments
            for index, row in df_merged.iterrows():
                try:
                    g_code = row["G CODE"]
                    roll_no = row["Roll No."]
                    section = row["Sections"]
                    
                    # Get student ID
                    student_id = student_dict.get(roll_no)
                    if not student_id:
                        continue

                    section_number = 1  # Default section

                    # Handle section information in G CODE
                    if "(" in g_code and ")" in g_code:
                        # Extract course code and section from format like "COURSE123(Sec1)"
                        course = g_code.split("(")[0].strip()
                        section_info = g_code.split("(")[1].replace(")", "").strip()
                        
                        # Extract section number if it's in format "Sec1", "Sec2", etc.
                        if section_info.startswith("Sec"):
                            try:
                                section_number = int(section_info.replace("Sec", ""))
                            except ValueError:
                                section_number = 1
                        # Handle letter format like "A", "B", "C"
                        elif len(section_info) == 1 and section_info.isalpha():
                            try:
                                section_number = ord(section_info.upper()) - ord('A') + 1  # Convert A->1, B->2, etc.
                            except ValueError:
                                section_number = 1
                    elif "-" in g_code and g_code.split("-")[-1].isalpha() and len(g_code.split("-")[-1]) == 1:
                        # Handle dash-separated format like "DATA201-A", "DATA201-B"
                        parts = g_code.split("-")
                        course = "-".join(parts[:-1])  # Everything except the last part
                        section_letter = parts[-1].upper()
                        
                        # Convert section letter to number (A=1, B=2, etc.)
                        try:
                            section_number = ord(section_letter) - ord('A') + 1
                        except ValueError:
                            section_number = 1
                    else:
                        # No section info in G CODE, use course as-is
                        course = g_code.strip()

                    # Get course ID
                    course_id = course_dict.get(course)
                    if not course_id:
                        logger.warning(f"Course {course} not found in database")
                        continue

                    # Add to bulk insert list
                    enrollments_to_insert.append({
                        'StudentID': student_id,
                        'CourseID': course_id,
                        'SectionNumber': section_number
                    })

                except Exception as e:
                    logger.error(f"Error processing enrollment for G CODE {g_code}: {e}")
                    continue

            # Get existing enrollments to avoid duplicates
            existing_enrollments = set()
            for enrollment in session.query(CourseStud).all():
                existing_enrollments.add((enrollment.StudentID, enrollment.CourseID))

            # Filter out existing enrollments
            new_enrollments = [
                enrollment for enrollment in enrollments_to_insert
                if (enrollment['StudentID'], enrollment['CourseID']) not in existing_enrollments
            ]

            # Bulk insert new enrollments
            if new_enrollments:
                session.bulk_insert_mappings(CourseStud, new_enrollments)
                session.commit()
                logger.info(f"Bulk inserted {len(new_enrollments)} course-student enrollments")
                print(f"Successfully bulk inserted {len(new_enrollments)} course-student enrollments.")
            else:
                logger.info("No new course-student enrollments to insert")
                print("No new course-student enrollments to insert.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error bulk inserting course-student data: {e}")
            raise

    # After inserting enrollments, run section allocation for multi-section courses
    try:
        print("Running section allocation for multi-section courses...")
        section_assignments = run_section_allocation(db_path)
        if section_assignments:
            print(f"Successfully allocated {len(section_assignments)} students to sections")
        else:
            print("No section allocation needed (no multi-section courses found)")
    except Exception as e:
        logger.error(f"Error in section allocation: {e}")
        print(f"Warning: Section allocation failed: {e}")





def get_student_section_info(db_path):
    """
    Retrieve student section assignments for all courses.
    
    :param db_path: Path to the database
    :return: DataFrame with student section information
    """
    with get_db_session(db_path) as session:
        try:
            query = session.query(
                User.Email.label('Roll_No'),
                User.Name.label('Student_Name'),
                Course.CourseName.label('Course'),
                CourseStud.SectionNumber
            ).select_from(CourseStud)\
             .join(User, CourseStud.StudentID == User.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .filter(User.Role == 'Student')\
             .order_by(Course.CourseName, CourseStud.SectionNumber, User.Email)
            
            return pd.DataFrame(query.all())
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching student section info: {e}")
            return pd.DataFrame()