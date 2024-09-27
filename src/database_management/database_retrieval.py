import pandas as pd
from .databse_connection import DatabaseConnection
import os
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base


def get_connection():
    mydb_dict = {
        'host': os.getenv("DATABASE_HOST"),
        'user': os.getenv("DATABASE_USER"),
        'password': os.getenv("DATABASE_PASSWORD"),
        'database': os.getenv("DATABASE_REF"),
        'port': os.getenv("DATABASE_PORT")
    }

    connection_string = f"mariadb+mariadbconnector://{mydb_dict['user']}:{mydb_dict['password']}@{mydb_dict['host']}:{mydb_dict['port']}/{mydb_dict['database']}"
    engine = sqlalchemy.create_engine(connection_string)
    return engine

def registration_data():
    engine = get_connection()
    if engine is None:
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

    with engine.connect() as conn:
        df = pd.read_sql(
            sql=query,
            con=conn.connection
        )
    engine.dispose()

    return df

def faculty_pref():
    engine = get_connection()
    if engine is None:
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
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=query,
            con=conn.connection
        )

    return df