from databse_connection import DatabaseConnection
import pandas as pd
import numpy as np
import os
from pathlib import Path


def insert_courses_professors(file_name, db_config):
    """
    Inserts course information associated with professors from a CSV file into the database.

    :param file_name: The file name for the CSV file containing courses and faculty names.
    :param db_config: A dictionary containing the database configuration (host, user, password, database).
    """
    # Getting the file location for the faculty preference CSV file
    file_loc = os.path.join(Path(__file__).resolve().parents[2], 'data', file_name)
    # Read the CSV into a DataFrame
    df_courses = pd.read_csv(file_loc)

    # Initialize the database connection
    db = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"]
    )
    db.connect()  # Connect to the database

    # Fetch user information (UserID and Email) for professors
    fetch_user = db.fetch_query("SELECT UserID, Email FROM Users WHERE Role='Professor'")
    # Create a dictionary mapping faculty names (values) to UserIDs (keys)
    dict_user = {value: key for key, value in fetch_user}

    # Create a new DataFrame with relevant columns (Course code and Faculty Name)
    df_merged = df_courses[['Course code', 'Faculty Name']].copy()
    df_merged['UserID'] = np.nan  # Initialize UserID column as NaN

    # Map Faculty Name to UserID
    for faculty_name in df_merged["Faculty Name"]:
        try:
            df_merged.loc[df_merged["Faculty Name"] == faculty_name, "UserID"] = int(dict_user[faculty_name])
        except KeyError:
            continue  # Skip if Faculty Name is not found in the dictionary

    # Keep only relevant columns and rename
    df_merged = df_merged[['Course code', 'UserID']]
    df_merged.rename(columns={'Course code': 'Course'}, inplace=True)

    # Drop rows with missing UserID
    df_merged.dropna(inplace=True)
    df_merged['UserID'] = df_merged['UserID'].astype(int)

    # SQL query to insert data into the Courses table
    insert_query = """
        INSERT INTO Courses (CourseName, ProfessorID)
        VALUES (%s, %s)
    """

    # Iterate over each row in the DataFrame and insert the data into the database
    for row in df_merged.itertuples(index=False):
        try:
            db.execute_query(insert_query, (row.Course, row.UserID))  # Insert Course and UserID
        except Exception as e:
            print(f"Error inserting row {row}: {e}")  # Print error if insertion fails

    # Close the database connection once all operations are complete
    db.close()