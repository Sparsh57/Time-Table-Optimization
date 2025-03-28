import pandas as pd
from .databse_connection import DatabaseConnection

def registration_data(db_path):
    db = DatabaseConnection.get_connection(db_path)
    query = """
    SELECT u.Email AS 'Roll No.', c.CourseName AS 'G CODE', p.Email AS 'Professor', c.CourseType AS 'Type', c.Credits AS 'Credit'
    FROM Course_Stud cs
    JOIN Users u ON cs.StudentID = u.UserID
    JOIN Courses c ON cs.CourseID = c.CourseID
    JOIN Users p ON c.ProfessorID = p.UserID
    """
    try:
        result = db.fetch_query(query)
        return pd.DataFrame(result, columns=['Roll No.', 'G CODE', 'Professor', 'Type', 'Credit'])
    except Exception as e:
        print("Error fetching registration data:", e)
    finally:
        db.close()

def faculty_pref(db_path):
    """
    Fetch professor preferences for busy slots.

    Returns:
        pd.DataFrame: DataFrame containing professor names and their busy time slots.
    """
    # Initialize the database connection
    db = DatabaseConnection.get_connection(db_path)

    if db is None:
        return pd.DataFrame()  # Return an empty DataFrame if connection fails

    query = """
    SELECT 
        u.Email AS 'Name', 
        s.Day || ' ' || TIME(s.StartTime) AS 'Busy Slot'
    FROM Users u
    JOIN Professor_BusySlots ps ON u.UserID = ps.ProfessorID
    JOIN Slots s ON ps.SlotID = s.SlotID
    WHERE u.Role = 'Professor'
    ORDER BY u.Email, s.Day, s.StartTime;
    """

    try:
        # Execute the query using the fetch_query method from DatabaseConnection
        result = db.fetch_query(query)

        # Convert the result to a pandas DataFrame
        df = pd.DataFrame(result, columns=['Name', 'Busy Slot'])

    finally:
        # Ensure the database connection is closed after query execution
        db.close()

    return df

def student_pref(db_path):
    """
    Fetch student preferences for busy slots.

    Returns:
        pd.DataFrame: DataFrame containing student names and their busy time slots.
    """
    # Initialize the database connection
    db = DatabaseConnection.get_connection(db_path)

    if db is None:
        return pd.DataFrame()  # Return an empty DataFrame if connection fails

    query = """
    SELECT 
        u.Email AS 'Name'
    FROM Users u
    JOIN Courses s ON u.CourseID = s.CourseID
    WHERE u.Role = 'Student'
    ORDER BY u.Email;
    """

    try:
        # Execute the query using the fetch_query method from DatabaseConnection
        result = db.fetch_query(query)
        # Convert the result to a pandas DataFrame
        df = pd.DataFrame(result, columns=['Name', 'Busy Slot'])

    finally:
        # Ensure the database connection is closed after query execution
        db.close()

    return df

def get_all_time_slots(db_path):
    """
    Retrieves all time slots from the Slots table in the given database.
    Returns a list of strings in the format "Day HH:MM".
    """
    db = DatabaseConnection.get_connection(db_path)
    query = """
    SELECT Day, TIME(StartTime) AS StartTime 
    FROM Slots 
    ORDER BY Day, StartTime;
    """
    try:
        result = db.fetch_query(query)
        # Construct a list of time slot strings
        time_slots = [f"{row[0]} {row[1]}" for row in result]
        return time_slots
    except Exception as e:
        print("Error fetching time slots:", e)
        return []
    finally:
        db.close()