import pandas as pd
from .databse_connection import DatabaseConnection
import os
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus


def get_connection():
    try:
        mydb_dict = {
            'host': os.getenv("DATABASE_HOST"),
            'user': os.getenv("DATABASE_USER"),
            'password': os.getenv("DATABASE_PASSWORD"),
            'database': os.getenv("DATABASE_REF"),
            'port': os.getenv("DATABASE_PORT")
        }
        encoded_password = quote_plus(mydb_dict['password'])
        connection_string = f"mariadb+pymysql://{mydb_dict['user']}:{encoded_password}@{mydb_dict['host']}:{mydb_dict['port']}/{mydb_dict['database']}"
        engine = sqlalchemy.create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"Error establishing database connection: {e}")
        raise e  


def registration_data():
    try:
        engine = get_connection()
        if engine is None:
            raise RuntimeError("Failed to establish database connection for registration data.")
        
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
            df = pd.read_sql(sql=query, con=conn.connection)
        
        return df

    except Exception as e:
        print(f"Error fetching registration data: {e}")
        raise e  
    finally:
        if engine:
            try:
                engine.dispose()
            except Exception as e:
                print(f"Error disposing the engine: {e}")
                raise e  


def faculty_pref():
    try:
        engine = get_connection()
        if engine is None:
            raise RuntimeError("Failed to establish database connection for faculty preferences.")

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
            df = pd.read_sql(sql=query, con=conn.connection)
        
        return df

    except Exception as e:
        print(f"Error fetching faculty preferences: {e}")
        raise e 
    finally:
        if engine:
            try:
                engine.dispose()
            except Exception as e:
                print(f"Error disposing the engine: {e}")
                raise e  
