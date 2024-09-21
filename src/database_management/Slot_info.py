from databse_connection import DatabaseConnection
import pandas as pd


def insert_time_slots(db_config):
    """
    Inserts predefined time slots into the database.

    :param db_config: A dictionary containing the database configuration (host, user, password, database).
    """
    # Define start times, end times, and week days
    start_times = ["08:30", "10:30", "12:30", "14:30", "16:30", "18:30"]
    end_times = ["10:30", "12:30", "14:30", "16:30", "18:30", "20:30"]
    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Create the data for the pandas DataFrame
    data = []
    for day in week_days:
        for start, end in zip(start_times, end_times):
            data.append([start, end, day])

    # Create the DataFrame without SlotID (auto-increment in the database)
    df = pd.DataFrame(data, columns=["StartTime", "EndTime", "Day"])

    # Display the DataFrame
    print(df)

    # Initialize the database connection
    mydb = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"]
    )
    mydb.connect()  # Connect to the database

    # Insert time slots into the database
    for index, row in df.iterrows():
        try:
            query = """INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)"""
            params = (row['StartTime'], row['EndTime'], row['Day'])
            mydb.execute_query(query, params)
        except Exception as e:
            print(f"Failed to insert row {index}: {e}")  # Print error if insertion fails

    mydb.close()  # Close the database connection
