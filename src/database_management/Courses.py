from .dbconnection import get_db_session
from .models import User, Course, CourseProfessor, CourseSection
from .migration import migrate_database_for_sections, check_migration_needed
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


def parse_faculty_names(faculty_name_str):
    """
    Parse comma-separated faculty names and return a list of cleaned names.
    
    :param faculty_name_str: String containing one or more faculty names separated by commas
    :return: List of faculty names
    """
    if pd.isna(faculty_name_str):
        return []
    
    # Split by comma and strip whitespace
    faculty_names = [name.strip() for name in str(faculty_name_str).split(',')]
    return [name for name in faculty_names if name]  # Remove empty strings


def insert_courses_professors(file, db_path):
    """
    Inserts course information with section support from a CSV file into the database using SQLAlchemy.
    Handles multiple professors per course separated by commas and creates sections accordingly.

    :param file: The CSV file containing courses and faculty names.
    :param db_path: Path to the database file.
    """
    print("INSERTING COURSES")
    df_courses = file

    # Check if migration is needed and run it
    if check_migration_needed(db_path):
        print("Database migration needed for sections support...")
        migrate_database_for_sections(db_path)
        print("Database migration completed.")

    with get_db_session(db_path) as session:
        try:
            # Fetch user information (UserID and Email) for professors
            professors = session.query(User).filter_by(Role='Professor').all()
            prof_dict = {prof.Email: prof.UserID for prof in professors}

            # Process each course
            for index, row in df_courses.iterrows():
                try:
                    course_code = row['Course code']
                    faculty_names_str = row['Faculty Name']
                    course_type = map_course_type(row['Type'])
                    credits = row['Credits']
                    
                    # Get number of sections (default to 1 if not provided)
                    num_sections = row.get('Number of Sections', 1)
                    if pd.isna(num_sections):
                        num_sections = 1
                    num_sections = int(num_sections)

                    # Parse faculty names (handles comma-separated values)
                    faculty_names = parse_faculty_names(faculty_names_str)
                    
                    if not faculty_names:
                        logger.warning(f"No valid faculty names found for course {course_code}")
                        continue

                    # Check if course already exists, if not create it
                    existing_course = session.query(Course).filter_by(CourseName=course_code).first()
                    if not existing_course:
                        new_course = Course(
                            CourseName=course_code,
                            CourseType=course_type,
                            Credits=credits,
                            NumberOfSections=num_sections
                        )
                        session.add(new_course)
                        session.flush()  # Get the CourseID
                        course_id = new_course.CourseID
                    else:
                        course_id = existing_course.CourseID
                        # Update existing course with new section count if different
                        if existing_course.NumberOfSections != num_sections:
                            existing_course.NumberOfSections = num_sections

                    # Create sections and assign professors
                    _create_course_sections(session, course_id, num_sections, faculty_names, prof_dict, course_code)

                    # Maintain backward compatibility: also add to CourseProfessor table
                    for faculty_name in faculty_names:
                        professor_id = prof_dict.get(faculty_name)
                        if professor_id:
                            # Check if this course-professor relationship already exists
                            existing_relation = session.query(CourseProfessor).filter_by(
                                CourseID=course_id,
                                ProfessorID=professor_id
                            ).first()
                            
                            if not existing_relation:
                                course_professor = CourseProfessor(
                                    CourseID=course_id,
                                    ProfessorID=professor_id
                                )
                                session.add(course_professor)

                except Exception as e:
                    logger.error(f"Error processing course {row.get('Course code', 'Unknown')}: {e}")

            session.commit()
            logger.info(f"Inserted courses with sections and professor relationships into database")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting courses: {e}")
            raise


def _create_course_sections(session, course_id, num_sections, faculty_names, prof_dict, course_code):
    """
    Creates course sections and assigns professors to them.
    
    :param session: Database session
    :param course_id: Course ID
    :param num_sections: Number of sections to create
    :param faculty_names: List of faculty names
    :param prof_dict: Dictionary mapping faculty names to IDs
    :param course_code: Course code for logging
    """
    # Clear existing sections for this course
    session.query(CourseSection).filter_by(CourseID=course_id).delete()
    
    # Create sections
    for section_num in range(1, num_sections + 1):
        # Assign professor using round-robin distribution
        faculty_index = (section_num - 1) % len(faculty_names)
        faculty_name = faculty_names[faculty_index]
        professor_id = prof_dict.get(faculty_name)
        
        if professor_id:
            course_section = CourseSection(
                CourseID=course_id,
                SectionNumber=section_num,
                ProfessorID=professor_id
            )
            session.add(course_section)
            logger.info(f"Created section {section_num} for course {course_code} with professor {faculty_name}")
        else:
            logger.warning(f"Professor {faculty_name} not found for section {section_num} of course {course_code}")


def fetch_course_data(db_path):
    """
    Fetches all course data from the Courses table using SQLAlchemy.
    Now returns courses with their associated professors.

    :param db_path: Path to the database file.
    :return: List of all course data with professor information.
    """
    with get_db_session(db_path) as session:
        try:
            # Query courses with their professors
            query = session.query(
                Course.CourseID,
                Course.CourseName,
                Course.CourseType,
                Course.Credits,
                User.Email.label('ProfessorEmail'),
                User.Name.label('ProfessorName')
            ).select_from(Course)\
             .join(CourseProfessor, Course.CourseID == CourseProfessor.CourseID)\
             .join(User, CourseProfessor.ProfessorID == User.UserID)\
             .order_by(Course.CourseName, User.Email)
            
            result = []
            for row in query.all():
                result.append((
                    row.CourseID,
                    row.CourseName,
                    row.ProfessorEmail,
                    row.CourseType,
                    row.Credits,
                    row.ProfessorName
                ))
            
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching course data: {e}")
            return []


def get_professors_for_course(course_name, db_path):
    """
    Get all professors assigned to a specific course.
    
    :param course_name: Name of the course
    :param db_path: Path to the database file
    :return: List of professor emails
    """
    with get_db_session(db_path) as session:
        try:
            query = session.query(User.Email)\
                          .join(CourseProfessor, User.UserID == CourseProfessor.ProfessorID)\
                          .join(Course, CourseProfessor.CourseID == Course.CourseID)\
                          .filter(Course.CourseName == course_name)
            
            professors = [prof.Email for prof in query.all()]
            return professors
        except SQLAlchemyError as e:
            logger.error(f"Error fetching professors for course {course_name}: {e}")
            return []