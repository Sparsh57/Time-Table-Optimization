from .databse_connection import DatabaseConnection
import pandas as pd


def schedule(schedule_df):
    print(schedule_df)
    db = DatabaseConnection.get_connection()
    try:
        # Fetch course IDs
        course_ids = db.fetch_query("SELECT CourseName, CourseID FROM Courses")
        course_id_map = {name: id for name, id in course_ids}

        # Fetch time slots
        time_slots = db.fetch_query("SELECT Day || ' ' || StartTime AS TimeSlot, SlotID FROM Slots")
        slot_id_map = {time: id for time, id in time_slots}

        for index, row in schedule_df.iterrows():
            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(row['Scheduled Time'])
            if course_id and slot_id:
                insert_query = "INSERT INTO Schedule (CourseID, SlotID) VALUES (?, ?)"
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
            GROUP_CONCAT(DISTINCT Courses.CourseName) AS Courses
        FROM 
            Schedule
        JOIN 
            Courses ON Schedule.CourseID = Courses.CourseID
        JOIN 
            Slots ON Schedule.SlotID = Slots.SlotID
        GROUP BY 
            Slots.Day, Slots.StartTime, Slots.EndTime
        ORDER BY 
            CASE Slots.Day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END, 
            Slots.StartTime, 
            Slots.EndTime;
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()


def generate_csv(filename='schedule.csv'):
    data = fetch_schedule_data()
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def generate_csv_for_student(roll_number):
    filename = f'Student_{roll_number}.csv'
    data = get_student_schedule(roll_number)
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def get_course_ids_for_student(roll_number):
    db = DatabaseConnection.get_connection()
    try:
        course_query = """
        SELECT CourseID
        FROM Course_Stud
        JOIN Users ON Course_Stud.StudentID = Users.UserID
        WHERE Users.Email = ?
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
        in_clause = ', '.join('?' * len(course_id_list))
        schedule_query = f"""
        SELECT 
            Slots.Day,
            Slots.StartTime,
            Slots.EndTime,
            GROUP_CONCAT(DISTINCT Courses.CourseName) AS Courses
        FROM 
            Schedule
        JOIN 
            Courses ON Schedule.CourseID = Courses.CourseID
        JOIN 
            Slots ON Schedule.SlotID = Slots.SlotID
        WHERE 
            Schedule.CourseID IN ({in_clause})
        GROUP BY 
            Slots.Day, Slots.StartTime, Slots.EndTime
        ORDER BY 
            CASE Slots.Day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END, 
            Slots.StartTime, 
            Slots.EndTime;
        """
        schedule = db.fetch_query(schedule_query, course_id_list)
        return schedule
    finally:
        db.close()


def get_student_schedule(roll_number):
    course_ids = get_course_ids_for_student(roll_number)
    schedule = get_schedule_for_courses(course_ids)
    return schedule