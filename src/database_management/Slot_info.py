from .databse_connection import DatabaseConnection
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def insert_time_slots(db_config, input_data):
    """
    Inserts dynamic time slots into the database based on the input data.

    :param db_config: A dictionary containing the database configuration (host, user, password, database).
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
    db = DatabaseConnection.get_connection()

    # Insert time slots into the database
    for index, row in df.iterrows():
        try:
            query = """INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)"""
            params = (row['StartTime'], row['EndTime'], row['Day'])
            db.execute_query(query, params)
        except Exception as e:
            print(f"Failed to insert row {index}: {e}")  # Print error if insertion fails

    db.close()  # Close the database connection





def fetch_slot_data():
    db = DatabaseConnection.get_connection()
    try:
        query = """
        SELECT * from Slots
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()

db_config = {'host': os.getenv("DATABASE_HOST"),
             'user': os.getenv("DATABASE_USER"),
             'port': os.getenv("DATABASE_PORT"),
             'password': os.getenv("DATABASE_PASSWORD"),
             'database': os.getenv("DATABASE_REF"),}

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
#insert_time_slots(db_config, insert_time)
print(fetch_slot_data())