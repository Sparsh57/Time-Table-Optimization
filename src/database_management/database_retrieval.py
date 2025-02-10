import pandas as pd
from .databse_connection import DatabaseConnection
import os


def registration_data(db_config):
    """
    Fetch registration data of students, including roll numbers, course names, and professor emails.

    Returns:
        pd.DataFrame: DataFrame containing the registration data.
    """
    # Initialize the database connection
    db = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        port=db_config["port"],
        password=db_config["password"],
        database=db_config["database"]).connect()

    if db is None:
        return pd.DataFrame()  # Return an empty DataFrame if connection fails

    query = """
    SELECT 
        u.Email AS 'Roll No.', 
        c.CourseName AS 'G CODE', 
        p.Email AS 'Professor'
    FROM Course_Stud cs
    JOIN Users u ON cs.StudentID = u.UserID
    JOIN Courses c ON cs.CourseID = c.CourseID
    JOIN Users p ON c.ProfessorID = p.UserID
    LEFT JOIN Professor_BusySlots ps ON p.UserID = ps.ProfessorID
    GROUP BY u.Email, c.CourseName, p.Email;
    """

    try:
        # Execute the query using the fetch_query method from DatabaseConnection

        result = db.fetch_query(query)
        # Convert the result to a pandas DataFrame
        df = pd.DataFrame(result, columns=['Roll No.', 'G CODE', 'Professor'])

    finally:
        # Ensure the database connection is closed after query execution
        db.close()

    return df


def faculty_pref(db_config):
    """
    Fetch professor preferences for busy slots.

    Returns:
        pd.DataFrame: DataFrame containing professor names and their busy time slots.
    """
    # Initialize the database connection
    db = DatabaseConnection(host=db_config["host"],
        user=db_config["user"],
        port=db_config["port"],
        password=db_config["password"],
        database=db_config["database"]).connect()

    if db is None:
        return pd.DataFrame()  # Return an empty DataFrame if connection fails

    query = """
    SELECT 
        u.Email AS 'Name', 
        CONCAT(s.Day, ' ', TIME_FORMAT(s.StartTime, '%H:%i')) AS 'Busy Slot'
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