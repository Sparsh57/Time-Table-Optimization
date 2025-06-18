from .dbconnection import get_db_session, create_tables
from .models import Course, Slot, Schedule, User, CourseStud, CourseProfessor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy import func, case, text
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
    :param db_path: Path to the database file or schema identifier
    """
    print("Inserting schedule data:")
    print(schedule_df)
    
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # First, ensure tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                # Check if Schedule table exists by querying it
                session.execute(text("SELECT 1 FROM \"Schedule\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                # Check if Schedule table exists by querying it
                session.execute(text("SELECT 1 FROM Schedule LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Schedule table not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        logger.info("Tables created successfully")
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
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

                # Parse course identifier to extract base course and section number
                course_identifier = row['Course ID']
                section_number = 1  # Default section
                
                if '-' in course_identifier and course_identifier.split('-')[-1].isalpha():
                    # This is a section identifier like "DATA201-A"
                    parts = course_identifier.split('-')
                    base_course_name = '-'.join(parts[:-1])
                    section_letter = parts[-1]
                    
                    # Convert section letter to number (A=1, B=2, etc.)
                    if len(section_letter) == 1 and section_letter.isalpha():
                        section_number = ord(section_letter.upper()) - ord('A') + 1
                else:
                    # This is a base course name without section
                    base_course_name = course_identifier
                    section_number = 1
                
                course_id = course_id_map.get(base_course_name)
                slot_id = slot_id_map.get(formatted_time)
                
                if course_id and slot_id:
                    # Check if schedule entry already exists
                    existing_schedule = session.query(Schedule).filter_by(
                        CourseID=course_id, 
                        SlotID=slot_id,
                        SectionNumber=section_number
                    ).first()
                    
                    if not existing_schedule:
                        new_schedule = Schedule(
                            CourseID=course_id,
                            SlotID=slot_id,
                            SectionNumber=section_number
                        )
                        session.add(new_schedule)
                        print(f"Inserted schedule: {base_course_name} section {section_number} at {formatted_time}")
                else:
                    if not course_id:
                        print(f"Course not found in database: '{course_identifier}' -> '{base_course_name}'")
                    if not slot_id:
                        print(f"Slot not found for time: '{formatted_time}'")
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
    
    :param db_path: Path to the database file or schema identifier
    :return: Boolean indicating if timetable exists
    """
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # First, ensure tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                # Check if Schedule table exists by querying it
                session.execute(text("SELECT 1 FROM \"Schedule\" LIMIT 1"))
        else:
            with get_db_session(db_path) as session:
                # Check if Schedule table exists by querying it
                session.execute(text("SELECT 1 FROM Schedule LIMIT 1"))
    except Exception:
        # If table doesn't exist, create all tables
        logger.info("Schedule table not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        logger.info("Tables created successfully")
        return False  # No timetable exists yet
    
    # Check if there are any schedule entries
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            count = session.query(Schedule).count()
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking timetable status: {e}")
            return False


def fetch_schedule_data(db_path):
    """
    Fetch schedule data with course information using SQLAlchemy.
    
    :param db_path: Path to the database file or schema identifier
    :return: List of tuples containing schedule data
    """
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            # Query to get courses for each time slot with section information
            query = session.query(
                Slot.Day,
                Slot.StartTime,
                Slot.EndTime,
                Course.CourseName,
                Course.NumberOfSections,
                Schedule.SectionNumber
            ).select_from(Schedule)\
             .join(Course, Schedule.CourseID == Course.CourseID)\
             .join(Slot, Schedule.SlotID == Slot.SlotID)\
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
                Slot.EndTime,
                Course.CourseName,
                Schedule.SectionNumber
            )
            
            # Group courses by time slot and format section identifiers
            schedule_dict = {}
            for row in query.all():
                time_key = (row.Day, row.StartTime, row.EndTime)
                
                # Format course identifier based on number of sections
                if row.NumberOfSections == 1:
                    course_identifier = row.CourseName
                else:
                    section_letter = chr(ord('A') + row.SectionNumber - 1)
                    course_identifier = f"{row.CourseName}-{section_letter}"
                
                if time_key not in schedule_dict:
                    schedule_dict[time_key] = []
                schedule_dict[time_key].append(course_identifier)
            
            # Convert to the expected format
            result = []
            for (day, start_time, end_time), courses in schedule_dict.items():
                courses_str = ', '.join(sorted(courses))
                result.append((day, start_time, end_time, courses_str))
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Error fetching schedule data: {e}")
            return []


def generate_csv(db_path, filename='schedule.csv'):
    """
    Generate CSV file from schedule data.
    
    :param db_path: Path to the database file or schema identifier
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
    :param db_path: Path to the database file or schema identifier
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
    :param db_path: Path to the database file or schema identifier
    :return: List of course IDs
    """
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
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
    :param db_path: Path to the database file or schema identifier
    :return: List of schedule data
    """
    if not course_id_list:
        return []
    
    from .dbconnection import is_postgresql, get_organization_database_url
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
        
    with session_context as session:
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