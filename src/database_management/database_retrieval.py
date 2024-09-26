import pandas as pd
from .databse_connection import DatabaseConnection
import os


def registration_data():
    mydb_dict = {'host': os.getenv("DATABASE_HOST"),
                 'user': os.getenv("DATABASE_USER"),
                 'password': os.getenv("DATABASE_PASSWORD"),
                 'database': os.getenv("DATABASE_REF"),
                 'port': os.getenv("DATABASE_PORT")}

    db = DatabaseConnection(
        host=mydb_dict["host"],
        port=int(mydb_dict["port"]),
        user=mydb_dict["user"],
        password=mydb_dict["password"],
        database=mydb_dict["database"]  # Added database parameter
    )
    connection = db.connect()
    if connection is None:
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
    df = pd.read_sql_query(query, connection)
    db.close()

    return df

def faculty_pref():
    mydb_dict = {'host': os.getenv("DATABASE_HOST"),
                 'user': os.getenv("DATABASE_USER"),
                 'password': os.getenv("DATABASE_PASSWORD"),
                 'database': os.getenv("DATABASE_REF"),
                 'port': os.getenv("DATABASE_PORT")}

    db = DatabaseConnection(
        host=mydb_dict["host"],
        port=int(mydb_dict["port"]),
        user=mydb_dict["user"],
        password=mydb_dict["password"],
        database=mydb_dict["database"]  # Added database parameter
    )
    connection = db.connect()
    if connection is None:
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
    df = pd.read_sql_query(query, connection)
    db.close()

    return df
Changed from Mysql to Mariadb. Also imported port in every file required.