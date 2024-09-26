from .databse_connection import DatabaseConnection
import numpy as np


def insert_professor_busy_slots(file, db_config):
    """
    Inserts professor busy slots from a CSV file into a database.

    :param file: The CSV file containing faculty preferences.
    :param db_config: A dictionary containing the database configuration (host, user, password, database).
    """
    df_courses = file  # Read the CSV into a DataFrame

    # Initialize the database connection
    db = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        port=db_config["port"],
        password=db_config["password"],
        database=db_config["database"]
    )
    db.connect()  # Connect to the database

    # Fetch the user information (UserID and Email) for professors
    fetch_user = db.fetch_query("SELECT UserID, Email FROM Users WHERE Role='Professor'")
    # Create a dictionary mapping emails (values) to UserIDs (keys)
    dict_user = {value: key for key, value in fetch_user}

    # Fetch available slots (SlotID, Day, StartTime)
    fetch_slot = db.fetch_query("SELECT SlotID, Day, StartTime FROM Slots")
    # Create a dictionary mapping day and time (concatenated as string) to SlotID
    dict_slot = {days + " " + start: key for key, days, start in fetch_slot}

    # Create a copy of relevant columns from the dataframe (Name and Busy Slot)
    df_merged = df_courses[['Name', 'Busy Slot']].copy()
    df_merged['ProfessorID'] = np.nan  # Initialize ProfessorID column as NaN
    df_merged['SlotID'] = np.nan  # Initialize SlotID column as NaN

    # Loop through each professor's name and assign their corresponding UserID from the dictionary
    for name in df_merged["Name"]:
        try:
            df_merged.loc[df_merged["Name"] == name, "ProfessorID"] = int(dict_user[name])
        except KeyError:
            continue  # If the professor's name is not found in the dictionary, skip

    # Loop through each busy slot and assign corresponding SlotID from the dictionary
    for time in df_merged["Busy Slot"]:
        try:
            df_merged.loc[df_merged["Busy Slot"] == time, "SlotID"] = int(dict_slot[time])
        except KeyError:
            continue  # If the slot is not found in the dictionary, skip

    # Drop rows where either ProfessorID or SlotID is missing (NaN values)
    df_merged.dropna(subset=['ProfessorID', 'SlotID'], inplace=True)
    df_merged = df_merged[['ProfessorID', 'SlotID']]  # Keep only relevant columns

    # Convert ProfessorID and SlotID to integers
    df_merged['ProfessorID'] = df_merged['ProfessorID'].astype(int)
    df_merged['SlotID'] = df_merged['SlotID'].astype(int)

    # SQL query to insert data into the Professor_BusySlots table
    insert_query = """
        INSERT INTO Professor_BusySlots (ProfessorID, SlotID)
        VALUES (%s, %s)
    """

    # Iterate over each row in the DataFrame and insert the data into the database
    for row in df_merged.itertuples(index=False, name=None):
        try:
            db.execute_query(insert_query, (row[0], row[1]))  # Insert ProfessorID and SlotID into the table
        except Exception as e:
            print(f"Error inserting row {row}: {e}")  # Print error if insertion fails

    # Close the database connection once all operations are complete
    db.close()
