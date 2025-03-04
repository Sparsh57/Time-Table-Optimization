from .databse_connection import DatabaseConnection
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

def insert_time_slots(input_data, db_path):
    """
    Deletes existing time slots and inserts new dynamic time slots into the SQLite database based on the input data.

    :param input_data: A dictionary where keys are week days and values are lists of tuples containing start and end times.
    """
    print(db_path)
    # Create the data for the pandas DataFrame
    data = []
    for day, time_slots in input_data.items():
        for start, end in time_slots:
            data.append([start, end, day])

    # Create the DataFrame without SlotID (auto-increment in the database)
    df = pd.DataFrame(data, columns=["StartTime", "EndTime", "Day"])

    # Display the DataFrame (for debugging purposes)
    print(df)

    # Initialize the database connection
    db = DatabaseConnection.get_connection(db_path)
    # Delete existing time slots in the database
    try:
        delete_query = """DELETE FROM Slots"""
        db.execute_query(delete_query)
        print("Existing time slots deleted successfully.")
    except Exception as e:
        print(f"Failed to delete existing time slots: {e}")

    # Insert new time slots into the database
    for index, row in df.iterrows():
        try:
            query = """INSERT INTO Slots (StartTime, EndTime, Day) VALUES (?, ?, ?)"""
            params = (row['StartTime'], row['EndTime'], row['Day'])
            db.execute_query(query, params)
        except Exception as e:
            print(f"Failed to insert row {index}: {e}")  # Print error if insertion fails

    db.close()  # Close the database connection

def fetch_slots(db_path):
    """
    Fetches slot data from the SQLite database.

    :return: List of tuples containing slot data.
    """
    db = DatabaseConnection.get_connection(db_path)
    try:
        query = """
        SELECT SlotID, Day, StartTime, EndTime FROM Slots
        ORDER BY Day;
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()

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
#insert_time_slots(insert_time)

# Fetch and display slot data
#slot_data = fetch_slot_data()
#print(slot_data)
