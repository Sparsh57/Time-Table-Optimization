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
    Deletes existing time slots and inserts new dynamic time slots into the database using SQLAlchemy.

    :param input_data: A dictionary where keys are week days and values are lists of tuples containing start and end times.
    :param db_path: Path to the database file.
    """
    print(f"Inserting time slots into database: {db_path}")
    
    # Create the data for the pandas DataFrame
    data = []
    for day, time_slots in input_data.items():
        for start, end in time_slots:
            data.append([start, end, day])

    # Create the DataFrame without SlotID (auto-increment in the database)
    df = pd.DataFrame(data, columns=["StartTime", "EndTime", "Day"])
    print("Time slots to insert:")
    print(df)

    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            # Check if Slots table exists by querying it
            session.execute(text("SELECT 1 FROM Slots LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Slots table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")

    # Now proceed with the actual time slot insertion
    with get_db_session(db_path) as session:
        try:
            # Delete existing time slots in the database
            deleted_count = session.query(Slot).delete()
            logger.info(f"Deleted {deleted_count} existing time slots")
            print(f"Deleted {deleted_count} existing time slots successfully.")

            # Insert new time slots into the database
            for index, row in df.iterrows():
                try:
                    # Check if slot already exists with same time and day
                    existing_slot = session.query(Slot).filter_by(
                        StartTime=row['StartTime'],
                        EndTime=row['EndTime'],
                        Day=row['Day']
                    ).first()
                    
                    if not existing_slot:
                        new_slot = Slot(
                            StartTime=row['StartTime'],
                            EndTime=row['EndTime'],
                            Day=row['Day']
                        )
                        session.add(new_slot)
                except Exception as e:
                    logger.error(f"Failed to insert row {index}: {e}")

            session.commit()
            logger.info(f"Inserted {len(df)} time slots into database")
            print(f"Successfully inserted {len(df)} time slots.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting time slots: {e}")
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
