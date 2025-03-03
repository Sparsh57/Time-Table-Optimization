from .databse_connection import DatabaseConnection
import pandas as pd
import numpy as np


def insert_course_students(file, db_path):
    """
    Inserts student course enrollments from a CSV file into the SQLite database.

    :param file: The CSV file containing student registration data.
    """

    # Read the CSV into a DataFrame
    df_courses = file
    print(db_path)
    # Initialize the database connection
    db = DatabaseConnection.get_connection(db_path)

    # Fetch user information (UserID and Email) for students
    fetch_user = db.fetch_query("SELECT UserID, Email FROM Users WHERE Role='Student'")
    # Create a dictionary mapping emails (values) to UserIDs (keys)
    dict_user = {value: key for key, value in fetch_user}

    # Fetch available courses (CourseID and CourseName)
    fetch_course = db.fetch_query("SELECT CourseID, CourseName FROM Courses")
    # Create a dictionary mapping course names (values) to CourseIDs (keys)
    dict_course = {value: key for key, value in fetch_course}

    # Create a new DataFrame with relevant columns (G CODE and Roll No.)
    df_merged = df_courses[['G CODE', 'Roll No.', 'Sections']].copy()
    df_merged['UserID'] = np.nan  # Initialize UserID column as NaN
    df_merged['CourseID'] = np.nan  # Initialize CourseID column as NaN

    # Map Roll No. to UserID using the dict_user dictionary
    for roll_no in df_merged["Roll No."]:
        try:
            df_merged.loc[df_merged["Roll No."] == roll_no, "UserID"] = int(dict_user[roll_no])
        except KeyError:
            continue  # Skip if Roll No. is not found in dict_user

    # Map G CODE to CourseID using the dict_course dictionary
    for index, row in df_merged.iterrows():
        g_code = row["G CODE"]
        section = row["Sections"]

        # Try removing the section part from the G CODE
        try:
            # Assuming the section is in parentheses like G CODE (Section)
            course = g_code.replace(f"({section})", "").strip()

            # Debugging output
            if course != g_code:
                print(f"Original G CODE: {g_code}, Processed Course: {course}")

            # Map the cleaned course to CourseID
            df_merged.loc[index, "CourseID"] = int(dict_course[course])

        except KeyError:
            continue

    # Drop rows where either UserID or CourseID is missing (NaN values)
    df_merged.dropna(subset=['UserID', 'CourseID'], inplace=True)
    df_merged = df_merged[['UserID', 'CourseID']]  # Keep only relevant columns

    # Convert UserID and CourseID to integers
    df_merged['UserID'] = df_merged['UserID'].astype(int)
    df_merged['CourseID'] = df_merged['CourseID'].astype(int)

    # SQL query to insert data into the Course_Stud table
    insert_query = """
        INSERT INTO Course_Stud (StudentID, CourseID)
        VALUES (?, ?)
    """

    # Iterate over each row in the DataFrame and insert the data into the database
    for row in df_merged.itertuples(index=False, name=None):
        try:
            db.execute_query(insert_query, (row[0], row[1]))  # Insert UserID (StudentID) and CourseID
        except Exception as e:
            print(f"Error inserting row {row}: {e}")  # Print error if insertion fails

    # Close the database connection once all operations are complete
    db.close()