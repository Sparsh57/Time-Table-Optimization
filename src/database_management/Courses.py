from .databse_connection import DatabaseConnection
import pandas as pd
import numpy as np


def map_course_type(course_type):
    """
    Maps the course type to either 'Elective' or 'Required'.

    :param course_type: The original course type value.
    :return: 'Elective' if 'Elective' is in the value, else 'Required'.
    """
    if 'Elective' in course_type:
        return 'Elective'
    else:
        return 'Required'


def insert_courses_professors(file, db_config):
    print("INSETING COURSES")
    """
    Inserts course information associated with professors from a CSV file into the database.

    :param file: The CSV file containing courses and faculty names.
    :param db_config: A dictionary containing the database configuration (host, user, password, database).
    """
    # Read the CSV into a DataFrame
    df_courses = file
    # Initialize the database connection
    db = DatabaseConnection.get_connection()

    # Fetch user information (UserID and Email) for professors
    fetch_user = db.fetch_query("SELECT UserID, Email FROM Users WHERE Role='Professor'")
    # Create a dictionary mapping faculty names (values) to UserIDs (keys)
    dict_user = {value: key for key, value in fetch_user}
    # Create a new DataFrame with relevant columns (Course code and Faculty Name)
    df_merged = df_courses[['Course code', 'Faculty Name', 'Course Type']].copy()
    df_merged['UserID'] = np.nan  # Initialize UserID column as NaN

    # Map Faculty Name to UserID
    for faculty_name in df_merged["Faculty Name"]:
        try:
            df_merged.loc[df_merged["Faculty Name"] == faculty_name, "UserID"] = int(dict_user[faculty_name])
        except KeyError:
            continue  # Skip if Faculty Name is not found in the dictionary

    # Apply the mapping function to convert Course Type to either 'Elective' or 'Required'
    df_merged['Course Type'] = df_merged['Course Type'].apply(map_course_type)

    # Keep only relevant columns and rename
    df_merged = df_merged[['Course code', 'UserID', 'Course Type']]
    df_merged.rename(columns={'Course code': 'Course', 'Course Type': 'Type'}, inplace=True)

    # Drop rows with missing UserID
    df_merged.dropna(inplace=True)
    df_merged['UserID'] = df_merged['UserID'].astype(int)

    # SQL query to insert data into the Courses table
    insert_query = """
        INSERT INTO Courses (CourseName, ProfessorID, CourseType)
        VALUES (%s, %s, %s)
    """

    # Iterate over each row in the DataFrame and insert the data into the database
    for row in df_merged.itertuples(index=False):
        try:
            db.execute_query(insert_query, (row.Course, row.UserID, row.Type))  # Insert Course and UserID
        except Exception as e:
            print(f"Error inserting row {row}: {e}")  # Print error if insertion fails
            raise e  

    # Close the database connection once all operations are complete
    db.close()

def fetch_course_data():
    db = DatabaseConnection.get_connection()
    try:
        query = """
        SELECT * from Courses
        """
        result = db.fetch_query(query)
        return result
    except Exception as e:
        print(f"Error fetching course data: {e}")
        raise e  
    finally:
        db.close()

print(fetch_course_data())
