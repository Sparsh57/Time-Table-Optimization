import pandas as pd
from .dbconnection import get_db_session
from .models import User, Course, CourseStud, Slot, ProfessorBusySlot
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import aliased
import logging

logger = logging.getLogger(__name__)

def registration_data(db_path):
    """
    Fetch registration data (student enrollments) using SQLAlchemy.
    
    :param db_path: Path to the database file
    :return: DataFrame containing registration data
    """
    with get_db_session(db_path) as session:
        try:
            # Create aliases for users table to distinguish between students and professors
            Student = aliased(User)
            Professor = aliased(User)
            
            # Query to get student registration data with joins
            query = session.query(
                Student.Email.label('Roll No.'),
                Course.CourseName.label('G CODE'),
                Professor.Email.label('Professor'),
                Course.CourseType.label('Type'),
                Course.Credits.label('Credit')
            ).select_from(CourseStud)\
             .join(Student, CourseStud.StudentID == Student.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .join(Professor, Course.ProfessorID == Professor.UserID)\
             .filter(Student.Role == 'Student')\
             .filter(Professor.Role == 'Professor')
            
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
                func.concat(Slot.Day, ' ', Slot.StartTime).label('Busy Slot')
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