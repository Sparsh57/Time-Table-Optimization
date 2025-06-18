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
    
    :param db_path: Path to the database file or schema identifier.
    """
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    truncate_schedule = True

    # Step 1: Check if Schedule table exists
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Schedule\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Schedule LIMIT 1"))
    except OperationalError as e:
        if "no such table: Schedule" in str(e) or "does not exist" in str(e):
            logger.info("Schedule table doesn't exist - skipping Schedule truncation")
            truncate_schedule = False
        else:
            raise

    # Step 2: Ensure all tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Users\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        logger.info("Tables not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        logger.info("Tables created successfully")

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    # Step 3: Truncate data
    with session_context as session:
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