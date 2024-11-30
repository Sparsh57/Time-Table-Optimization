import pandas as pd
from .databse_connection import DatabaseConnection

def registration_data():
    db = DatabaseConnection.get_connection()
    query = """
    SELECT u.Email AS 'Roll No.', c.CourseName AS 'G CODE', p.Email AS 'Professor'
    FROM Course_Stud cs
    JOIN Users u ON cs.StudentID = u.UserID
    JOIN Courses c ON cs.CourseID = c.CourseID
    JOIN Users p ON c.ProfessorID = p.UserID
    """
    try:
        result = db.fetch_query(query)
        return pd.DataFrame(result, columns=['Roll No.', 'G CODE', 'Professor'])
    except Exception as e:
        print("Error fetching registration data:", e)
    finally:
        db.close()

def faculty_pref():
    """
    Fetch professor preferences for busy slots.

    Returns:
        pd.DataFrame: DataFrame containing professor names and their busy time slots.
    """
    # Initialize the database connection
    db = DatabaseConnection.get_connection()

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