import pandas as pd
from .dbconnection import get_db_session
from .models import User, Course, CourseStud, Slot, ProfessorBusySlot, CourseProfessor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import aliased
import logging

logger = logging.getLogger(__name__)

def registration_data(db_path):
    """
    Fetch registration data (student enrollments) using SQLAlchemy.
    Now handles multiple professors per course.
    
    :param db_path: Path to the database file
    :return: DataFrame containing registration data
    """
    with get_db_session(db_path) as session:
        try:
            # Create aliases for users table to distinguish between students and professors
            Student = aliased(User)
            Professor = aliased(User)
            
            # Query to get student registration data with joins
            # Use GROUP_CONCAT to combine multiple professors for a course
            query = session.query(
                Student.Email.label('Roll No.'),
                Course.CourseName.label('G CODE'),
                func.group_concat(Professor.Email.distinct()).label('Professor'),
                Course.CourseType.label('Type'),
                Course.Credits.label('Credit')
            ).select_from(CourseStud)\
             .join(Student, CourseStud.StudentID == Student.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .join(CourseProfessor, Course.CourseID == CourseProfessor.CourseID)\
             .join(Professor, CourseProfessor.ProfessorID == Professor.UserID)\
             .filter(Student.Role == 'Student')\
             .filter(Professor.Role == 'Professor')\
             .group_by(Student.Email, Course.CourseName, Course.CourseType, Course.Credits)
            
            results = []
            for row in query.all():
                results.append({
                    'Roll No.': row._asdict()['Roll No.'],
                    'G CODE': row._asdict()['G CODE'],
                    'Professor': row._asdict()['Professor'],
                    'Type': row._asdict()['Type'],
                    'Credit': row._asdict()['Credit']
                })
            
            return pd.DataFrame(results)
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching registration data: {e}")
            return pd.DataFrame()

def registration_data_with_sections(db_path):
    """
    Fetch registration data with section information for section-aware timetable generation.
    
    :param db_path: Path to the database file
    :return: DataFrame containing registration data with section information
    """
    with get_db_session(db_path) as session:
        try:
            # Query to get student registration data with section information
            query = session.query(
                User.Email.label('Roll No.'),
                Course.CourseName.label('BaseCourse'),
                CourseStud.SectionNumber,
                Course.CourseType.label('Type'),
                Course.Credits.label('Credit'),
                Course.NumberOfSections
            ).select_from(CourseStud)\
             .join(User, CourseStud.StudentID == User.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .filter(User.Role == 'Student')\
             .order_by(User.Email, Course.CourseName, CourseStud.SectionNumber)
            
            results = []
            for row in query.all():
                # Create course identifier based on number of sections
                base_course = row.BaseCourse
                section_num = row.SectionNumber
                num_sections = row.NumberOfSections
                
                if num_sections == 1:
                    # Single section: just use course name
                    course_identifier = base_course
                else:
                    # Multiple sections: use course-A, course-B format
                    section_letter = chr(ord('A') + section_num - 1)  # Convert 1->A, 2->B, etc.
                    course_identifier = f"{base_course}-{section_letter}"
                
                # Get professor for this specific section
                section_prof = get_professor_for_section(session, base_course, section_num)
                
                results.append({
                    'Roll No.': row._asdict()['Roll No.'],
                    'G CODE': course_identifier,
                    'BaseCourse': base_course,
                    'SectionNumber': section_num,
                    'Professor': section_prof,
                    'Type': row._asdict()['Type'],
                    'Credit': row._asdict()['Credit'],
                    'NumberOfSections': num_sections
                })
            
            return pd.DataFrame(results)
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching registration data with sections: {e}")
            return pd.DataFrame()

def get_professor_for_section(session, course_name, section_number):
    """
    Get the professor assigned to a specific section of a course using round-robin logic.
    
    :param session: Database session
    :param course_name: Name of the course
    :param section_number: Section number
    :return: Professor email or None
    """
    try:
        # Get all professors for this course from CourseProfessor table
        query = session.query(User.Email)\
                      .join(CourseProfessor, User.UserID == CourseProfessor.ProfessorID)\
                      .join(Course, CourseProfessor.CourseID == Course.CourseID)\
                      .filter(Course.CourseName == course_name)\
                      .filter(User.Role == 'Professor')\
                      .order_by(User.Email)  # Ensure consistent ordering
        
        professors = [prof.Email for prof in query.all()]
        
        if not professors:
            return None
        
        # Use round-robin assignment: section 1 -> prof 0, section 2 -> prof 1, etc.
        prof_index = (section_number - 1) % len(professors)
        return professors[prof_index]
        
    except Exception as e:
        logger.error(f"Error getting professor for section {section_number} of {course_name}: {e}")
        return None

def faculty_pref(db_path):
    """
    Fetch professor preferences for busy slots using SQLAlchemy.

    :param db_path: Path to the database file
    :return: DataFrame containing professor names and their busy time slots.
    """
    with get_db_session(db_path) as session:
        try:
            # Query to get professor busy slots
            query = session.query(
                User.Email.label('Name'),
                (Slot.Day + ' ' + Slot.StartTime).label('Busy Slot')
            ).select_from(User)\
             .join(ProfessorBusySlot, User.UserID == ProfessorBusySlot.ProfessorID)\
             .join(Slot, ProfessorBusySlot.SlotID == Slot.SlotID)\
             .filter(User.Role == 'Professor')\
             .order_by(User.Email, Slot.Day, Slot.StartTime)
            
            results = []
            for row in query.all():
                results.append({
                    'Name': row.Name,
                    'Busy Slot': row._asdict()['Busy Slot']
                })
            
            return pd.DataFrame(results)
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching faculty preferences: {e}")
            return pd.DataFrame()

def student_pref(db_path):
    """
    Fetch student preferences for busy slots using SQLAlchemy.
    Note: This function seems to have an incorrect query in the original.
    Students don't have a CourseID field directly.

    :param db_path: Path to the database file
    :return: DataFrame containing student names and their busy time slots.
    """
    with get_db_session(db_path) as session:
        try:
            # Query to get all students (the original query had an error)
            query = session.query(User.Email.label('Name'))\
                          .filter(User.Role == 'Student')\
                          .order_by(User.Email)
            
            results = []
            for row in query.all():
                results.append({
                    'Name': row.Name,
                    'Busy Slot': None  # No busy slot information available for students
                })
            
            return pd.DataFrame(results)
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching student preferences: {e}")
            return pd.DataFrame()

def get_all_time_slots(db_path):
    """
    Retrieves all time slots from the Slots table using SQLAlchemy.
    
    :param db_path: Path to the database file
    :return: List of strings in the format "Day HH:MM".
    """
    with get_db_session(db_path) as session:
        try:
            # Query to get all time slots
            query = session.query(
                Slot.Day,
                Slot.StartTime
            ).order_by(Slot.Day, Slot.StartTime)
            
            time_slots = []
            for row in query.all():
                time_slots.append(f"{row.Day} {row.StartTime}")
            
            return time_slots
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching time slots: {e}")
            return []

def get_course_professor_mapping(db_path):
    """
    Get a mapping of courses to their professors (handles multiple professors per course).
    
    :param db_path: Path to the database file
    :return: Dictionary mapping course names to list of professor emails
    """
    with get_db_session(db_path) as session:
        try:
            query = session.query(
                Course.CourseName,
                User.Email
            ).select_from(Course)\
             .join(CourseProfessor, Course.CourseID == CourseProfessor.CourseID)\
             .join(User, CourseProfessor.ProfessorID == User.UserID)\
             .filter(User.Role == 'Professor')\
             .order_by(Course.CourseName, User.Email)
            
            course_prof_mapping = {}
            for row in query.all():
                course_name = row.CourseName
                prof_email = row.Email
                
                if course_name not in course_prof_mapping:
                    course_prof_mapping[course_name] = []
                course_prof_mapping[course_name].append(prof_email)
            
            return course_prof_mapping
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching course-professor mapping: {e}")
            return {}

def get_course_section_professor_mapping(db_path):
    """
    Get a mapping of course sections to their professors using round-robin logic.
    
    :param db_path: Path to the database file
    :return: Dictionary mapping course identifiers to professor emails
    """
    with get_db_session(db_path) as session:
        try:
            # Get all courses with their professors
            query = session.query(
                Course.CourseName,
                Course.NumberOfSections,
                User.Email
            ).select_from(Course)\
             .join(CourseProfessor, Course.CourseID == CourseProfessor.CourseID)\
             .join(User, CourseProfessor.ProfessorID == User.UserID)\
             .filter(User.Role == 'Professor')\
             .order_by(Course.CourseName, User.Email)
            
            # Group professors by course
            course_professors = {}
            for row in query.all():
                course_name = row.CourseName
                prof_email = row.Email
                num_sections = row.NumberOfSections
                
                if course_name not in course_professors:
                    course_professors[course_name] = {
                        'professors': [],
                        'num_sections': num_sections
                    }
                course_professors[course_name]['professors'].append(prof_email)
            
            # Create section-professor mapping using round-robin
            section_prof_mapping = {}
            for course_name, course_info in course_professors.items():
                professors = course_info['professors']
                num_sections = course_info['num_sections']
                
                for section_num in range(1, num_sections + 1):
                    # Use round-robin assignment
                    prof_index = (section_num - 1) % len(professors)
                    prof_email = professors[prof_index]
                    
                    # Create course identifier based on number of sections
                    if num_sections == 1:
                        course_identifier = course_name
                    else:
                        section_letter = chr(ord('A') + section_num - 1)
                        course_identifier = f"{course_name}-{section_letter}"
                    
                    section_prof_mapping[course_identifier] = prof_email
            
            return section_prof_mapping
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching course-section-professor mapping: {e}")
            return {}