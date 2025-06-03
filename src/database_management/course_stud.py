from .dbconnection import get_db_session
from .models import User, Course, CourseStud
from .section_allocation import run_section_allocation
from .migration import migrate_database_for_sections, check_migration_needed
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def insert_course_students(file, db_path):
    """
    Inserts student course enrollments from a CSV file into the database using SQLAlchemy.
    Now includes section allocation for multi-section courses.

    :param file: The CSV file containing student registration data.
    :param db_path: Path to the database file.
    """
    df_courses = file
    print(f"Inserting course students into database: {db_path}")

    # Check if migration is needed and run it
    if check_migration_needed(db_path):
        print("Database migration needed for sections support...")
        migrate_database_for_sections(db_path)
        print("Database migration completed.")

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
            df_merged['SectionNumber'] = 1  # Default section

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
                    # Handle section information in G CODE
                    if "(" in g_code and ")" in g_code:
                        # Extract course code and section from format like "COURSE123(Sec1)"
                        course = g_code.split("(")[0].strip()
                        section_info = g_code.split("(")[1].replace(")", "").strip()
                        
                        # Extract section number if it's in format "Sec1", "Sec2", etc.
                        if section_info.startswith("Sec"):
                            try:
                                section_num = int(section_info.replace("Sec", ""))
                                df_merged.loc[index, "SectionNumber"] = section_num
                            except ValueError:
                                df_merged.loc[index, "SectionNumber"] = 1
                        # Handle letter format like "A", "B", "C"
                        elif len(section_info) == 1 and section_info.isalpha():
                            try:
                                section_num = ord(section_info.upper()) - ord('A') + 1  # Convert A->1, B->2, etc.
                                df_merged.loc[index, "SectionNumber"] = section_num
                            except ValueError:
                                df_merged.loc[index, "SectionNumber"] = 1
                    else:
                        # No section info in G CODE, use course as-is
                        course = g_code.strip()

                    # Debugging output
                    if course != g_code:
                        print(f"Original G CODE: {g_code}, Processed Course: {course}")

                    # Map the cleaned course to CourseID
                    df_merged.loc[index, "CourseID"] = int(course_dict[course])

                except KeyError:
                    logger.warning(f"Course {course} not found in database")
                    continue
                except Exception as e:
                    logger.error(f"Error processing G CODE {g_code}: {e}")
                    continue

            # Drop rows where either UserID or CourseID is missing (NaN values)
            df_merged.dropna(subset=['UserID', 'CourseID'], inplace=True)
            df_merged = df_merged[['UserID', 'CourseID', 'SectionNumber']]

            # Convert to integers
            df_merged['UserID'] = df_merged['UserID'].astype(int)
            df_merged['CourseID'] = df_merged['CourseID'].astype(int)
            df_merged['SectionNumber'] = df_merged['SectionNumber'].astype(int)

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
                            CourseID=row[1],
                            SectionNumber=row[2]
                        )
                        session.add(new_enrollment)
                    else:
                        # Update section number if different
                        if existing_enrollment.SectionNumber != row[2]:
                            existing_enrollment.SectionNumber = row[2]
                            
                except Exception as e:
                    logger.error(f"Error inserting enrollment for student {row[0]}, course {row[1]}: {e}")

            session.commit()
            logger.info(f"Inserted course-student enrollments into database")
            print("Course-student enrollments inserted successfully.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting course-student data: {e}")
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