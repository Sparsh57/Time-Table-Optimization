from .dbconnection import get_db_session, create_tables
from .models import User, Course, CourseStud, ProfessorBusySlot, Schedule, CourseProfessor
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy import text
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()


def truncate_detail(db_path):
    """
    Deletes all data from the tables while handling foreign key constraints using SQLAlchemy.
    Now includes the CourseProfessor table, with graceful handling for existing databases.
    
    :param db_path: Path to the database file.
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if tables exist by querying them
            session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        # If tables don't exist, create all tables
        logger.info("Tables not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            # Delete in proper order to handle foreign key constraints
            deleted_schedule = session.query(Schedule).delete()
            deleted_busy_slots = session.query(ProfessorBusySlot).delete()
            deleted_course_stud = session.query(CourseStud).delete()
            
            # Try to delete from CourseProfessor table, but handle case where it doesn't exist
            deleted_course_professor = 0
            try:
                deleted_course_professor = session.query(CourseProfessor).delete()
            except OperationalError as e:
                if "no such table: Course_Professor" in str(e):
                    logger.info("Course_Professor table doesn't exist yet - skipping deletion")
                    deleted_course_professor = 0
                else:
                    raise  # Re-raise if it's a different error
            
            deleted_courses = session.query(Course).delete()
            deleted_users = session.query(User).filter(User.Role != 'Admin').delete()
            
            session.commit()
            
            logger.info(f"Truncation completed: "
                       f"Schedule({deleted_schedule}), "
                       f"BusySlots({deleted_busy_slots}), "
                       f"CourseStud({deleted_course_stud}), "
                       f"CourseProfessor({deleted_course_professor}), "
                       f"Courses({deleted_courses}), "
                       f"Users({deleted_users})")
            
            print("Tables truncated successfully.")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error truncating database: {e}")
            raise
