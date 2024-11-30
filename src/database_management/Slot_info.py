from databse_connection import DatabaseConnection
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()


def insert_time_slots(input_data):
    """
    Inserts dynamic time slots into the SQLite database based on the input data.

    :param input_data: A dictionary with keys "days" and "times".
                       "days" is a list of week days,
                       "times" is a list of tuples containing start and end times.
    """
    # Extract days and times from input_data
    week_days = input_data["days"]
    time_slots = input_data["times"]  # List of (start, end) tuples

    # Create the data for the pandas DataFrame
    data = []
    for day in week_days:
        for start, end in time_slots:
            data.append([start, end, day])

    # Create the DataFrame without SlotID (auto-increment in the database)
    df = pd.DataFrame(data, columns=["StartTime", "EndTime", "Day"])

    # Display the DataFrame (for debugging purposes)
    print(df)

    # Initialize the database connection
    db = DatabaseConnection()
    db = db.get_connection()

    # Insert time slots into the database
    for index, row in df.iterrows():
        try:
            query = """INSERT INTO Slots (StartTime, EndTime, Day) VALUES (?, ?, ?)"""
            params = (row['StartTime'], row['EndTime'], row['Day'])
            db.execute_query(query, params)
        except Exception as e:
            print(f"Failed to insert row {index}: {e}")  # Print error if insertion fails

    db.close()  # Close the database connection


def fetch_slot_data():
    """
    Fetches all time slot data from the SQLite database.

    :return: List of tuples containing time slot data.
    """
    db = DatabaseConnection().get_connection()
    try:
        query = "SELECT * FROM Slots"
        result = db.fetch_query(query)
        return result
    finally:
        db.close()


# Input Data
insert_time = {
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "times": [
        ["08:30", "10:30"],
        ["10:30", "12:30"],
        ["12:30", "14:30"],
        ["14:30", "16:30"],
        ["16:30", "18:30"],
        ["18:30", "20:30"]
    ]
}

# Uncomment to insert time slots into the database
insert_time_slots(insert_time)

# Fetch and display slot data
slot_data = fetch_slot_data()
print(slot_data)