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
    :param db_path: Path to the database file or schema identifier.
    """
    print(f"Bulk inserting time slots into database: {db_path}")
    
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
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
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Slots\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Slots LIMIT 1"))
    except Exception:
        logger.info("Slots table not found, creating tables...")
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

    # Now proceed with bulk insertion
    with session_context as session:
        try:
            # First, delete dependent records to avoid foreign key constraint violations
            from .models import ProfessorBusySlot, Schedule
            
            # Delete all Professor_BusySlots records (they reference Slots)
            busy_slots_deleted = session.query(ProfessorBusySlot).delete()
            logger.info(f"Deleted {busy_slots_deleted} professor busy slot records")
            
            # Delete all Schedule records (they reference Slots)
            schedule_deleted = session.query(Schedule).delete()
            logger.info(f"Deleted {schedule_deleted} schedule records")
            
            # Now delete existing time slots
            deleted_count = session.query(Slot).delete()
            logger.info(f"Deleted {deleted_count} existing time slots")

            # Bulk insert new time slots
            if slots_to_insert:
                session.bulk_insert_mappings(Slot, slots_to_insert)
                logger.info(f"Bulk inserted {len(slots_to_insert)} time slots")
                print(f"Successfully bulk inserted {len(slots_to_insert)} time slots.")

            session.commit()
            
            # Warn user about data that was cleared
            if busy_slots_deleted > 0 or schedule_deleted > 0:
                print(f"⚠️  Warning: Updated time slots required clearing:")
                if busy_slots_deleted > 0:
                    print(f"   - {busy_slots_deleted} professor busy slot preferences")
                if schedule_deleted > 0:
                    print(f"   - {schedule_deleted} existing schedule entries")
                print("   Please re-upload faculty preferences and regenerate the timetable if needed.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error in bulk inserting time slots: {e}")
            raise


def fetch_slots(db_path):
    """
    Fetches slot data from the database using SQLAlchemy.

    :param db_path: Path to the database file or schema identifier.
    :return: List of tuples containing slot data.
    """
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
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


def fix_corrupted_time_slots(db_path):
    """
    Fix corrupted time slots in the database by removing invalid entries
    and inserting proper educational time slots.
    
    :param db_path: Path to the database file or schema identifier
    """
    print(f"🔧 Fixing corrupted time slots in database: {db_path}")
    
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            # Check for corrupted time slots (StartTime = EndTime or invalid times)
            corrupted_count = 0
            slots = session.query(Slot).all()
            
            for slot in slots:
                # Check if StartTime equals EndTime (invalid duration)
                # Or if times are outside normal educational hours
                if (slot.StartTime == slot.EndTime or 
                    slot.StartTime in ['22:01', '23:01', '12:01', '13:01'] or
                    ':01' in slot.StartTime):  # These specific corrupt patterns
                    corrupted_count += 1
                    
            if corrupted_count > 0:
                print(f"❌ Found {corrupted_count} corrupted time slots")
                print("🗑️  Deleting all corrupted time slots...")
                
                # First, delete dependent records to avoid foreign key constraint violations
                from .models import ProfessorBusySlot, Schedule
                
                # Delete all Professor_BusySlots records (they reference Slots)
                busy_slots_deleted = session.query(ProfessorBusySlot).delete()
                print(f"   - Cleared {busy_slots_deleted} professor busy slot records")
                
                # Delete all Schedule records (they reference Slots)
                schedule_deleted = session.query(Schedule).delete()
                print(f"   - Cleared {schedule_deleted} schedule records")
                
                # Now delete all existing slots
                deleted_count = session.query(Slot).delete()
                session.commit()
                
                print(f"✅ Deleted {deleted_count} corrupted time slots")
                print("📅 Inserting proper educational time slots...")
                
                # Insert proper time slots
                insert_time_slots(insert_time, db_path)
                print("✅ Database fixed with proper time slots")
            else:
                print("✅ No corrupted time slots found")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error fixing corrupted time slots: {e}")
            raise


def ensure_default_time_slots(db_path):
    """
    Ensure that default time slots exist in the database.
    If no time slots are found, insert the default ones.
    If corrupted time slots are found, fix them.
    
    :param db_path: Path to the database file or schema identifier
    """
    print(f"Checking for time slots in database: {db_path}")
    
    slots = fetch_slots(db_path)
    if len(slots) == 0:
        print("No time slots found. Inserting default time slots...")
        insert_time_slots(insert_time, db_path)
        print("Default time slots inserted successfully.")
    else:
        print(f"Found {len(slots)} existing time slots.")
        
        # Check if any of them are corrupted
        corrupted = False
        for slot_id, day, start_time, end_time in slots:
            if (start_time == end_time or 
                start_time in ['22:01', '23:01', '12:01', '13:01'] or
                ':01' in start_time):
                corrupted = True
                break
                
        if corrupted:
            print("⚠️  Detected corrupted time slots in database!")
            fix_corrupted_time_slots(db_path)
        else:
            print("✅ Time slots appear to be valid.")


# Uncomment to insert time slots into the database
# insert_time_slots(insert_time, "path/to/database.db")

# Fetch and display slot data
# slot_data = fetch_slots("path/to/database.db")
# print(slot_data)
