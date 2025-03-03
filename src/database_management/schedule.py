from .databse_connection import DatabaseConnection
import pandas as pd
import datetime



def remove_seconds(time_str):
    """
    Given a time string in the format "Day HH:MM:SS", return it as "Day HH:MM".
    """
    try:
        day, time_part = time_str.split(" ", 1)
        parts = time_part.split(":")
        if len(parts) == 3:
            return f"{day} {parts[0]}:{parts[1]}"
        else:
            return time_str
    except Exception as e:
        print(f"Error processing time string '{time_str}': {e}")
        return time_str

def schedule(schedule_df, db_path):
    print(schedule_df)
    db = DatabaseConnection.get_connection(db_path)
    try:
        # Fetch course IDs
        course_ids = db.fetch_query("SELECT CourseName, CourseID FROM Courses")
        course_id_map = {name: id for name, id in course_ids}

        # Fetch time slots
        time_slots = db.fetch_query("SELECT Day || ' ' || StartTime AS TimeSlot, SlotID FROM Slots")
        slot_id_map = {time: id for time, id in time_slots}
        print("Available time slots in database:", slot_id_map.keys())
        for index, row in schedule_df.iterrows():
            # Remove seconds using our helper function
            formatted_time = remove_seconds(row['Scheduled Time'])
            print(f"Row {index}: original='{row['Scheduled Time']}', formatted='{formatted_time}'")

            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(formatted_time)
            if course_id and slot_id:
                insert_query = "INSERT OR IGNORE INTO Schedule (CourseID, SlotID) VALUES (?, ?)"
                db.execute_query(insert_query, (course_id, slot_id))
            else:
                print(f"Course ID or Slot ID not found for row: {row}")

            course_id = course_id_map.get(row['Course ID'])
            slot_id = slot_id_map.get(formatted_time)
            if course_id and slot_id:
                insert_query = "INSERT OR IGNORE INTO Schedule (CourseID, SlotID) VALUES (?, ?)"
                db.execute_query(insert_query, (course_id, slot_id))
            else:
                print(f"Course ID or Slot ID not found for row: {row}")

    except Exception as e:
        print("An error occurred while inserting data:", e)

    finally:
        db.close()


def timetable_made(db_path):
    db = DatabaseConnection.get_connection(db_path)
    query = "SELECT COUNT(*) FROM Schedule"
    result = db.fetch_query(query)
    db.close()
    return result[0][0] > 0


def fetch_schedule_data(db_path):
    db = DatabaseConnection.get_connection(db_path)
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
                WHEN 'Saturday' THEN 6 
                WHEN 'Sunday' THEN 7
            END, 
            Slots.StartTime, 
            Slots.EndTime;
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()


def generate_csv(db_path, filename='schedule.csv'):
    data = fetch_schedule_data(db_path)
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def generate_csv_for_student(roll_number, db_path):
    filename = f'Student_{roll_number}.csv'
    data = get_student_schedule(roll_number)
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def get_course_ids_for_student(roll_number, db_path):
    db = DatabaseConnection.get_connection(db_path)
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


def get_schedule_for_courses(course_id_list, db_path):
    if not course_id_list:
        return []
    db = DatabaseConnection.get_connection(db_path)
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
                WHEN 'Saturday' THEN 6 
                WHEN 'Sunday' THEN 7
            END, 
            Slots.StartTime, 
            Slots.EndTime;
        """
        schedule = db.fetch_query(schedule_query, course_id_list)
        return schedule
    finally:
        db.close()


def get_student_schedule(roll_number, db_path):
    course_ids = get_course_ids_for_student(roll_number, db_path)
    schedule = get_schedule_for_courses(course_ids, db_path)
    return schedule