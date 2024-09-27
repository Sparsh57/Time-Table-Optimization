from .databse_connection import DatabaseConnection
import pandas as pd
import os

def schedule(schedule_df):
    print("this is the shiiiii")
    print("schedule db = ")
    print(schedule_df)
    db = DatabaseConnection.get_connection()
    try:
        course_ids = db.fetch_query("SELECT CourseName, CourseID FROM Courses")
        course_id_map = {name: id for name, id in course_ids} 
        time_slots = db.fetch_query("SELECT CONCAT(Day, ' ', StartTime), SlotID FROM Slots")
        print(f'time_slots = {time_slots}')
        slot_id_map = {time: id for time, id in time_slots}
        print(f'map = {slot_id_map}')

        for index, row in schedule_df.iterrows():
            #print(row)
            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(row['Scheduled Time'])
            if course_id and slot_id:
                print("here")
                insert_query = f"INSERT INTO Schedule (CourseID, SlotID) VALUES ({course_id}, {slot_id})"
                print(insert_query)
                db.execute_query(insert_query, (course_id, slot_id))

    except Exception as e:
        print("An error occurred while inserting data:", e)
    
    finally:
        db.close()

def timetable_made():
    db = DatabaseConnection.get_connection()
    query = "SELECT COUNT(*) FROM Schedule"
    result = db.fetch_query(query)
    db.close()
    return result[0][0] > 0

def fetch_schedule_data():
    db = DatabaseConnection.get_connection()
    query = """
    SELECT 
        Slots.Day,
        Slots.StartTime,
        Slots.EndTime,
        GROUP_CONCAT(DISTINCT Courses.CourseName ORDER BY Courses.CourseName SEPARATOR ', ') AS Courses
    FROM 
        Schedule
    JOIN 
        Courses ON Schedule.CourseID = Courses.CourseID
    JOIN 
        Slots ON Schedule.SlotID = Slots.SlotID
    GROUP BY 
        Slots.Day, Slots.StartTime, Slots.EndTime
    ORDER BY 
        FIELD(Slots.Day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'), 
        Slots.StartTime, 
        Slots.EndTime;
    """
    result = db.fetch_query(query)
    db.close()
    return result

def generate_csv():
    pass

print(fetch_schedule_data())
