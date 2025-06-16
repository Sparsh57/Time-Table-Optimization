from .dbconnection import get_db_session, create_tables
from .models import User, Course, CourseProfessor
from .migration import migrate_database_for_sections, check_migration_needed
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
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


def insert_courses_professors(file, db_path):
    """
    Inserts course information with section support using bulk operations.
    Handles multiple professors per course and creates sections accordingly.

    :param file: The CSV file containing courses and faculty names.
    :param db_path: Path to the database file.
    """
    print("BULK INSERTING COURSES")
    df_courses = file

    # Check if migration is needed and run it
    if check_migration_needed(db_path):
        print("Database migration needed for sections support...")
        migrate_database_for_sections(db_path)
        print("Database migration completed.")

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Courses table exists by querying it
            session.execute(text("SELECT 1 FROM Courses LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Courses table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            # Fetch user information (UserID and Email) for professors
            professors = session.query(User).filter_by(Role='Professor').all()
            prof_dict = {prof.Email: prof.UserID for prof in professors}
            
            print(f"Found {len(prof_dict)} professors in database: {list(prof_dict.keys())}")

            # Prepare data for bulk insert
            courses_to_insert = []
            course_professor_relationships = []
            processed_courses = set()  # Track unique courses

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

                    # Parse faculty names (handles both comma and ampersand separators)
                    faculty_names = parse_faculty_names(faculty_names_str)
                    
                    if not faculty_names:
                        logger.warning(f"No valid faculty names found for course {course_code}")
                        continue

                    print(f"Course {course_code}: Faculty string '{faculty_names_str}' -> Parsed: {faculty_names}")

                    # Add course to bulk insert list (avoid duplicates)
                    if course_code not in processed_courses:
                        courses_to_insert.append({
                            'CourseName': course_code,
                            'CourseType': course_type,
                            'Credits': credits,
                            'NumberOfSections': num_sections
                        })
                        processed_courses.add(course_code)

                    # Prepare course-professor relationships
                    for faculty_name in faculty_names:
                        professor_id = prof_dict.get(faculty_name)
                        if professor_id:
                            course_professor_relationships.append({
                                'CourseName': course_code,  # Will map to CourseID after bulk insert
                                'ProfessorID': professor_id,
                                'FacultyName': faculty_name
                            })
                            logger.info(f"Will link professor {faculty_name} to course {course_code}")
                        else:
                            logger.warning(f"Professor '{faculty_name}' not found for course {course_code}")
                            logger.warning(f"Available professors: {list(prof_dict.keys())}")

                except Exception as e:
                    logger.error(f"Error processing course {row.get('Course code', 'Unknown')}: {e}")

            # Bulk insert courses
            if courses_to_insert:
                # Check for existing courses and filter them out
                existing_courses = {course.CourseName for course in session.query(Course.CourseName).all()}
                new_courses = [course for course in courses_to_insert if course['CourseName'] not in existing_courses]
                
                if new_courses:
                    session.bulk_insert_mappings(Course, new_courses)
                    session.commit()
                    logger.info(f"Bulk inserted {len(new_courses)} courses")
                else:
                    logger.info("No new courses to insert")

            # Now get course IDs for the relationships
            courses = session.query(Course).all()
            course_id_map = {course.CourseName: course.CourseID for course in courses}

            # Prepare and bulk insert course-professor relationships
            if course_professor_relationships:
                relationships_to_insert = []
                for rel in course_professor_relationships:
                    course_id = course_id_map.get(rel['CourseName'])
                    if course_id:
                        relationships_to_insert.append({
                            'CourseID': course_id,
                            'ProfessorID': rel['ProfessorID']
                        })

                # Check for existing relationships and filter them out
                existing_relationships = set()
                for rel in session.query(CourseProfessor).all():
                    existing_relationships.add((rel.CourseID, rel.ProfessorID))

                new_relationships = [
                    rel for rel in relationships_to_insert 
                    if (rel['CourseID'], rel['ProfessorID']) not in existing_relationships
                ]

                if new_relationships:
                    session.bulk_insert_mappings(CourseProfessor, new_relationships)
                    session.commit()
                    logger.info(f"Bulk inserted {len(new_relationships)} course-professor relationships")
                else:
                    logger.info("No new course-professor relationships to insert")

            logger.info(f"Bulk inserted courses with sections and professor relationships into database")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error bulk inserting courses: {e}")
            raise





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