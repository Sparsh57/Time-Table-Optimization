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
    If the Schedule table doesn't exist, skips truncating it and proceeds with others.
    """
    truncate_schedule = True

    # Step 1: Check if Schedule table exists
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Schedule LIMIT 1"))
    except OperationalError as e:
        if "no such table: Schedule" in str(e):
            logger.info("Schedule table doesn't exist - skipping Schedule truncation")
            truncate_schedule = False
        else:
            raise

    # Step 2: Ensure all tables exist
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        logger.info("Tables not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    # Step 3: Truncate data
    with get_db_session(db_path) as session:
        try:
            deleted_schedule = 0
            if truncate_schedule:
                deleted_schedule = session.query(Schedule).delete()

            deleted_busy_slots = session.query(ProfessorBusySlot).delete()
            deleted_course_stud = session.query(CourseStud).delete()

            deleted_course_professor = 0
            try:
                deleted_course_professor = session.query(CourseProfessor).delete()
            except OperationalError as e:
                if "no such table: Course_Professor" in str(e):
                    logger.info("Course_Professor table doesn't exist - skipping deletion")
                else:
                    raise

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