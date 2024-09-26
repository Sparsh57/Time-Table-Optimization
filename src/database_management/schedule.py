from .databse_connection import DatabaseConnection
import pandas as pd

def schedule(schedule_df):
    db = DatabaseConnection(
        host="byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
        user="urao5yk0erbiklfr",
        password="tpgCmLhZdwPk8iAxzVMd",
        database="byfapocx02at8jbunymk"
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