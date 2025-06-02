from .dbconnection import get_db_session
from .models import User, Course, CourseStud, ProfessorBusySlot, Schedule
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()


def truncate_detail(db_path):
    """
    Deletes all data from the tables while handling foreign key constraints using SQLAlchemy.
    
    :param db_path: Path to the database file.
    """
    with get_db_session(db_path) as session:
        try:
            # Delete in proper order to handle foreign key constraints
            deleted_schedule = session.query(Schedule).delete()
            deleted_busy_slots = session.query(ProfessorBusySlot).delete()
            deleted_course_stud = session.query(CourseStud).delete()
            deleted_courses = session.query(Course).delete()
            deleted_users = session.query(User).filter(User.Role != 'Admin').delete()
            
            session.commit()
            
            logger.info(f"Truncation completed: "
                       f"Schedule({deleted_schedule}), "
                       f"BusySlots({deleted_busy_slots}), "
                       f"CourseStud({deleted_course_stud}), "
                       f"Courses({deleted_courses}), "
                       f"Users({deleted_users})")
            
            print("Tables truncated successfully.")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error truncating database: {e}")
            raise
