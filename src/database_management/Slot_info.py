from .dbconnection import get_db_session, create_tables
from .models import Slot
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import pandas as pd
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)
load_dotenv()


def insert_time_slots(input_data, db_path):
    """
    Deletes existing time slots and inserts new dynamic time slots using bulk operations.
    
    :param input_data: A dictionary where keys are week days and values are lists of tuples containing start and end times.
    :param db_path: Path to the database file.
    """
    print(f"Bulk inserting time slots into database: {db_path}")
    
    # Create the data for bulk insertion
    slots_to_insert = []
    for day, time_slots in input_data.items():
        for start, end in time_slots:
            slots_to_insert.append({
                'StartTime': start,
                'EndTime': end,
                'Day': day
            })

    print(f"Prepared {len(slots_to_insert)} time slots for bulk insertion")

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Slots LIMIT 1"))
    except Exception:
        logger.info("Slots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    # Now proceed with bulk insertion
    with get_db_session(db_path) as session:
        try:
            # Delete existing time slots
            deleted_count = session.query(Slot).delete()
            logger.info(f"Deleted {deleted_count} existing time slots")

            # Bulk insert new time slots
            if slots_to_insert:
                session.bulk_insert_mappings(Slot, slots_to_insert)
                logger.info(f"Bulk inserted {len(slots_to_insert)} time slots")
                print(f"Successfully bulk inserted {len(slots_to_insert)} time slots.")

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error in bulk inserting time slots: {e}")
            raise





def fetch_slots(db_path):
    """
    Fetches slot data from the database using SQLAlchemy.

    :param db_path: Path to the database file.
    :return: List of tuples containing slot data.
    """
    with get_db_session(db_path) as session:
        try:
            slots = session.query(Slot).order_by(Slot.Day, Slot.StartTime).all()
            result = [(slot.SlotID, slot.Day, slot.StartTime, slot.EndTime) for slot in slots]
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching slots: {e}")
            return []


# Input Data
insert_time = {
    "Monday": [
        ["08:30", "10:30"],
        ["10:30", "12:30"]
    ],
    "Tuesday": [
        ["08:00", "09:30"],
        ["09:30", "11:00"],
        ["11:00", "12:30"]
    ],
    "Wednesday": [
        ["08:30", "10:30"],
        ["10:30", "12:30"],
        ["13:00", "15:00"]
    ],
    "Thursday": [
        ["09:00", "11:00"],
        ["11:00", "13:00"]
    ],
    "Friday": [
        ["10:30", "12:30"],
        ["12:30", "14:30"],
        ["14:30", "16:30"]
    ]
}

# Uncomment to insert time slots into the database
# insert_time_slots(insert_time, "path/to/database.db")

# Fetch and display slot data
# slot_data = fetch_slots("path/to/database.db")
# print(slot_data)
