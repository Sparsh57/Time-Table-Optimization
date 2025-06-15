from .dbconnection import get_db_session, create_tables
from .models import User, Slot, ProfessorBusySlot
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import numpy as np
import logging

logger = logging.getLogger(__name__)


def insert_professor_busy_slots(file, db_path):
    """
    Inserts professor busy slots from a CSV file into database using SQLAlchemy.

    :param file: The CSV file containing faculty preferences.
    :param db_path: Path to the database file.
    """
    df_courses = file
    logger.info(f"Starting busy slot insertion for database: {db_path}")

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Professor_BusySlots table exists by querying it
            session.execute(text("SELECT 1 FROM Professor_BusySlots LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Professor_BusySlots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            # Fetch professors and slots
            professors = session.query(User).filter_by(Role='Professor').all()
            slots = session.query(Slot).all()
            
            # Create dictionaries for mapping
            prof_dict = {prof.Email: prof.UserID for prof in professors}
            slot_dict = {f"{slot.Day} {slot.StartTime}": slot.SlotID for slot in slots}

            # Process the data
            df_merged = df_courses[['Name', 'Busy Slot']].copy()
            
            for index, row in df_merged.iterrows():
                try:
                    prof_id = prof_dict.get(row['Name'])
                    slot_id = slot_dict.get(row['Busy Slot'])
                    
                    if prof_id and slot_id:
                        # Check if busy slot already exists
                        existing = session.query(ProfessorBusySlot).filter_by(
                            ProfessorID=prof_id, SlotID=slot_id).first()
                        
                        if not existing:
                            new_busy_slot = ProfessorBusySlot(
                                ProfessorID=prof_id,
                                SlotID=slot_id
                            )
                            session.add(new_busy_slot)
                            
                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")

            session.commit()
            logger.info("Professor busy slots inserted successfully")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting busy slots: {e}")
            raise


def empty_professor_busy_slots(db_path):
    """
    Empties all records from the Professor_BusySlots table using SQLAlchemy.
    
    :param db_path: Path to the database file.
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Professor_BusySlots table exists by querying it
            session.execute(text("SELECT 1 FROM Professor_BusySlots LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Professor_BusySlots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            deleted_count = session.query(ProfessorBusySlot).delete()
            session.commit()
            logger.info(f"Deleted {deleted_count} professor busy slot records")
            print(f"All {deleted_count} records deleted successfully from Professor_BusySlots.")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deleting busy slots: {e}")
            raise


def fetch_professor_busy_slots(db_path):
    """
    Fetches all records from the Professor_BusySlots table using SQLAlchemy.

    :param db_path: Path to the database file.
    :return: List of tuples (ProfessorID, SlotID).
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Professor_BusySlots table exists by querying it
            session.execute(text("SELECT 1 FROM Professor_BusySlots LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Professor_BusySlots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            busy_slots = session.query(ProfessorBusySlot).all()
            result = [(bs.ProfessorID, bs.SlotID) for bs in busy_slots]
            print(result)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching busy slots: {e}")
            return []


def insert_professor_busy_slots_from_ui(slots, professor_id, db_path):
    """
    Inserts professor busy slots into the database from UI input using SQLAlchemy.

    :param slots: List of SlotIDs.
    :param professor_id: Professor's UserID.
    :param db_path: Path to the database file.
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Professor_BusySlots table exists by querying it
            session.execute(text("SELECT 1 FROM Professor_BusySlots LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Professor_BusySlots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    with get_db_session(db_path) as session:
        try:
            for slot_id in slots:
                # Check if busy slot already exists
                existing = session.query(ProfessorBusySlot).filter_by(
                    ProfessorID=professor_id, SlotID=slot_id).first()
                
                if not existing:
                    new_busy_slot = ProfessorBusySlot(
                        ProfessorID=professor_id,
                        SlotID=slot_id
                    )
                    session.add(new_busy_slot)
                    
            session.commit()
            logger.info(f"Inserted busy slots for professor {professor_id}")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting busy slots from UI: {e}")
            raise


def fetch_user_id(email, db_path):
    """
    Fetches the UserID of a professor based on email using SQLAlchemy.

    :param email: Email of the professor.
    :param db_path: Path to the database file.
    :return: UserID of the professor or None.
    """
    with get_db_session(db_path) as session:
        try:
            user = session.query(User).filter_by(Email=email).first()
            return user.UserID if user else None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user ID: {e}")
            return None
