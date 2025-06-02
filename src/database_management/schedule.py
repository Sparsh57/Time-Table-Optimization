from .dbconnection import get_db_session
from .models import Course, Slot, Schedule, User, CourseStud
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy import func, case
import pandas as pd
import datetime
import logging

logger = logging.getLogger(__name__)


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
    """
    Insert schedule data into the database using SQLAlchemy.
    
    :param schedule_df: DataFrame containing schedule information
    :param db_path: Path to the database file
    """
    print("Inserting schedule data:")
    print(schedule_df)
    
    with get_db_session(db_path) as session:
        try:
            # Fetch course IDs
            courses = session.query(Course).all()
            course_id_map = {course.CourseName: course.CourseID for course in courses}

            # Fetch time slots - create mapping for "Day HH:MM" format
            slots = session.query(Slot).all()
            slot_id_map = {}
            for slot in slots:
                time_key = f"{slot.Day} {slot.StartTime}"
                slot_id_map[time_key] = slot.SlotID
            
            print("Available time slots in database:", list(slot_id_map.keys()))
            
            for index, row in schedule_df.iterrows():
                # Remove seconds using our helper function
                formatted_time = remove_seconds(row['Scheduled Time'])
                print(f"Row {index}: original='{row['Scheduled Time']}', formatted='{formatted_time}'")

                course_id = course_id_map.get(row['Course ID'])
                slot_id = slot_id_map.get(formatted_time)
                
                if course_id and slot_id:
                    # Check if schedule entry already exists
                    existing_schedule = session.query(Schedule).filter_by(
                        CourseID=course_id, 
                        SlotID=slot_id
                    ).first()
                    
                    if not existing_schedule:
                        new_schedule = Schedule(
                            CourseID=course_id,
                            SlotID=slot_id
                        )
                        session.add(new_schedule)
                else:
                    print(f"Course ID or Slot ID not found for row: {row}")

            session.commit()
            logger.info("Schedule data inserted successfully")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting schedule data: {e}")
            raise


def timetable_made(db_path):
    """
    Check if timetable has been created (i.e., if Schedule table has entries).
    
    :param db_path: Path to the database file
    :return: Boolean indicating if timetable exists
    """
    with get_db_session(db_path) as session:
        try:
            count = session.query(Schedule).count()
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking timetable status: {e}")
            return False


def fetch_schedule_data(db_path):
    """
    Fetch schedule data with course information using SQLAlchemy.
    
    :param db_path: Path to the database file
    :return: List of tuples containing schedule data
    """
    with get_db_session(db_path) as session:
        try:
            # Query with joins and group by day and time slot
            query = session.query(
                Slot.Day,
                Slot.StartTime,
                Slot.EndTime,
                func.group_concat(Course.CourseName.distinct()).label('Courses')
            ).select_from(Schedule)\
             .join(Course, Schedule.CourseID == Course.CourseID)\
             .join(Slot, Schedule.SlotID == Slot.SlotID)\
             .group_by(Slot.Day, Slot.StartTime, Slot.EndTime)\
             .order_by(
                case(
                    (Slot.Day == 'Monday', 1),
                    (Slot.Day == 'Tuesday', 2),
                    (Slot.Day == 'Wednesday', 3),
                    (Slot.Day == 'Thursday', 4),
                    (Slot.Day == 'Friday', 5),
                    (Slot.Day == 'Saturday', 6),
                    (Slot.Day == 'Sunday', 7),
                    else_=8
                ),
                Slot.StartTime,
                Slot.EndTime
            )
            
            result = query.all()
            return [(row.Day, row.StartTime, row.EndTime, row.Courses) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching schedule data: {e}")
            return []


def generate_csv(db_path, filename='schedule.csv'):
    """
    Generate CSV file from schedule data.
    
    :param db_path: Path to the database file
    :param filename: Output CSV filename
    :return: Filename of generated CSV
    """
    data = fetch_schedule_data(db_path)
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def generate_csv_for_student(roll_number, db_path):
    """
    Generate CSV file for a specific student's schedule.
    
    :param roll_number: Student's roll number (email)
    :param db_path: Path to the database file
    :return: Filename of generated CSV
    """
    filename = f'Student_{roll_number}.csv'
    data = get_student_schedule(roll_number, db_path)
    df = pd.DataFrame(data, columns=['Day', 'StartTime', 'EndTime', 'Courses'])
    df.to_csv(filename, index=False)
    return filename


def get_course_ids_for_student(roll_number, db_path):
    """
    Get course IDs for a specific student using SQLAlchemy.
    
    :param roll_number: Student's roll number (email)
    :param db_path: Path to the database file
    :return: List of course IDs
    """
    with get_db_session(db_path) as session:
        try:
            # Query courses enrolled by the student
            query = session.query(CourseStud.CourseID)\
                          .join(User, CourseStud.StudentID == User.UserID)\
                          .filter(User.Email == roll_number)
            
            course_ids = [str(course.CourseID) for course in query.all()]
            return course_ids
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching course IDs for student: {e}")
            return []


def get_schedule_for_courses(course_id_list, db_path):
    """
    Get schedule for a list of courses using SQLAlchemy.
    
    :param course_id_list: List of course IDs
    :param db_path: Path to the database file
    :return: List of schedule data
    """
    if not course_id_list:
        return []
        
    with get_db_session(db_path) as session:
        try:
            # Convert course IDs to integers
            course_ids = [int(cid) for cid in course_id_list]
            
            # Query schedule for specific courses
            query = session.query(
                Slot.Day,
                Slot.StartTime,
                Slot.EndTime,
                func.group_concat(Course.CourseName.distinct()).label('Courses')
            ).select_from(Schedule)\
             .join(Course, Schedule.CourseID == Course.CourseID)\
             .join(Slot, Schedule.SlotID == Slot.SlotID)\
             .filter(Schedule.CourseID.in_(course_ids))\
             .group_by(Slot.Day, Slot.StartTime, Slot.EndTime)\
             .order_by(
                case(
                    (Slot.Day == 'Monday', 1),
                    (Slot.Day == 'Tuesday', 2),
                    (Slot.Day == 'Wednesday', 3),
                    (Slot.Day == 'Thursday', 4),
                    (Slot.Day == 'Friday', 5),
                    (Slot.Day == 'Saturday', 6),
                    (Slot.Day == 'Sunday', 7),
                    else_=8
                ),
                Slot.StartTime,
                Slot.EndTime
            )
            
            result = query.all()
            return [(row.Day, row.StartTime, row.EndTime, row.Courses) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching schedule for courses: {e}")
            return []


def get_student_schedule(roll_number, db_path):
    """
    Get complete schedule for a student.
    
    :param roll_number: Student's roll number (email)
    :param db_path: Path to the database file
    :return: List of schedule data for the student
    """
    course_ids = get_course_ids_for_student(roll_number, db_path)
    schedule_data = get_schedule_for_courses(course_ids, db_path)
    return schedule_data