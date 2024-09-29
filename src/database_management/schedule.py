from .databse_connection import DatabaseConnection
import pandas as pd
import os

def schedule(schedule_df):
    db = DatabaseConnection.get_connection()
    try:
        
        course_ids = db.fetch_query("SELECT CourseName, CourseID FROM Courses")
        print("course_ids",course_ids)
        course_id_map = {name: id for name, id in course_ids} 
        print("course_id_map",course_id_map)
        time_slots = db.fetch_query("SELECT CONCAT(Day, ' ', StartTime), SlotID FROM Slots")
        slot_id_map = {time: id for time, id in time_slots}
        print("slot_id_map",slot_id_map)
        for index, row in schedule_df.iterrows():
            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(row['Scheduled Time'])
            if course_id and slot_id:
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
    try:
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
        return result
    finally:
        db.close()

def generate_csv(filename='schedule.csv'):
    data = fetch_schedule_data()
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return filename 

def generate_csv_for_student(roll_number): 
    filename = f'Student_{roll_number}.csv'
    data = get_student_schedule(roll_number)
    df = pd.DataFrame(data)
    df.to_csv(filename, index = False)
    return filename

def get_course_ids_for_student(roll_number):
    db = DatabaseConnection.get_connection()
    try:
        course_query = """
        SELECT CourseID
        FROM Course_Stud
        JOIN Users ON Course_Stud.StudentID = Users.UserID
        WHERE Users.Email = %s
        """
        course_ids = db.fetch_query(course_query, (roll_number,))
        return [str(course[0]) for course in course_ids]
    finally:
        db.close()

def get_schedule_for_courses(course_id_list):
    if not course_id_list:
        return []
    db = DatabaseConnection.get_connection()
    try:
        in_clause = ', '.join(course_id_list)
        schedule_query = """
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
        WHERE 
            Schedule.CourseID IN (%s)
        GROUP BY 
            Slots.Day, Slots.StartTime, Slots.EndTime
        ORDER BY 
            FIELD(Slots.Day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'), 
            Slots.StartTime, 
            Slots.EndTime
        """
        schedule_query = schedule_query % in_clause 
        schedule = db.fetch_query(schedule_query)
        return schedule
    finally:
        db.close()

def get_student_schedule(roll_number):
    course_ids = get_course_ids_for_student(roll_number)
    schedule = get_schedule_for_courses(course_ids)
    return schedule