from databse_connection import DatabaseConnection
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

def truncate_detail(db_config):
    """
    Truncates various tables in the Timetable_Optimization database.

    :param db_config: A dictionary containing the database configuration (host, user, password, database, port).
    """
    mydb = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        port=db_config["port"],
        password=db_config["password"],
        database=db_config["database"]
    )

    mydb.connect()

    # Disable foreign key checks and truncate tables one by one
    queries = [
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE Courses;",
        "TRUNCATE Course_Stud;",
        "TRUNCATE Professor_BusySlots;",
        "TRUNCATE Schedule;",
        "TRUNCATE Slots;",
        "TRUNCATE Users;",
        "SET FOREIGN_KEY_CHECKS = 1;"  # Re-enable foreign key checks
    ]

    try:
        for query in queries:
            mydb.execute_query(query)  # Execute each query
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        mydb.close()

db_config = {'host': os.getenv("DATABASE_HOST"),
             'user': os.getenv("DATABASE_USER"),
             'port': os.getenv("DATABASE_PORT"),
             'password': os.getenv("DATABASE_PASSWORD"),
             'database': os.getenv("DATABASE_REF"),}
