from .databse_connection import DatabaseConnection
import pandas as pd
import os

def schedule(schedule_df):
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
    db.connect() 
    
    try:
        course_ids = db.fetch_query("SELECT CourseName, CourseID FROM Courses")
        course_id_map = {name: id for name, id in course_ids} 
        time_slots = db.fetch_query("SELECT CONCAT(Day, ' ', StartTime), SlotID FROM Slots")
        slot_id_map = {time: id for time, id in time_slots}

        for index, row in schedule_df.iterrows():
            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(row['Scheduled Time'])
            if course_id and slot_id:
                insert_query = "INSERT INTO Schedule (CourseID, SlotID) VALUES (%s, %s)"
                db.execute_query(insert_query, (course_id, slot_id))

    except Exception as e:
        print("An error occurred while inserting data:", e)
    
    finally:
        db.close()