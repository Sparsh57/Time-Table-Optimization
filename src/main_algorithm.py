from .data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map_all, prepare_student_course_section_map, expand_courses_with_sections
from .utilities import faculty_busy_slots, create_course_dictionary, create_course_credit_map, create_course_elective_map
from .schedule_model import schedule_courses
from .database_management.schedule import schedule
from .database_management.Courses import fetch_course_data
from .conflict_checker import check_conflicts, find_courses_with_multiple_slots_on_same_day
from .database_management.database_retrieval import registration_data, faculty_pref, get_all_time_slots, registration_data_with_sections, get_course_section_professor_mapping
from .database_management.migration import migrate_database_for_sections, check_migration_needed
import pandas as pd
import random


def gen_student_csv(student_list, course_list):
    data = []
    for student in student_list:
        courses = random.sample(course_list, 5)
        for i in courses:
            data.append({"Roll No.": student, "G CODE": i, "Sections": "A"})
    df = pd.DataFrame(data)
    df.to_csv("Student Registration Data.csv", index=False)

def diagnose_same_day_constraints(courses, course_credits):
    """
    Prints a diagnostic for each course that has fewer unique days than
    required credits. If a course needs 'X' sessions (credits = X) but
    only has Y < X distinct days, you'll never be able to schedule them
    all on different days.
    """
    for course_id, info in courses.items():
        # Extract days from each time slot
        slot_days = set()
        for slot in info["time_slots"]:
            day = slot.split()[0]  # or your get_day_from_time_slot(slot)
            slot_days.add(day)

        needed = course_credits.get(course_id, 2)  # default if missing
        day_count = len(slot_days)

        if day_count < needed:
            print(f"[DIAGNOSTIC] Course '{course_id}' needs {needed} sessions, "
                  f"but only has {day_count} unique day(s): {sorted(slot_days)}")
    print("[DIAGNOSTIC] Done checking same-day constraints.")

def gen_timetable(db_path):
    """
    Generate timetable using the original algorithm (backward compatibility).
    """
    df_merged = registration_data(db_path)
    student_course_map = prepare_student_course_map(df_merged)
    course_professor_map = create_course_professor_map_all(df_merged)
    professor_busy_slots = faculty_pref(db_path)
    course_credit_map = create_course_credit_map(df_merged)
    course_type_map = create_course_elective_map(df_merged)
    time_slots = get_all_time_slots(db_path)
    # Preprocess courses and schedule
    courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots, time_slots)
    diagnose_same_day_constraints(courses, course_credit_map)
    schedule_data = schedule_courses(courses, student_course_map, course_professor_map, course_credit_map, course_type_map, [])

    print("Schedule Data")
    print(schedule_data)
    print()
    print("Courses on the same day")
    print(find_courses_with_multiple_slots_on_same_day(schedule_data))
    print("Conflicts")
    print(check_conflicts(schedule_data, student_course_map))
    schedule(schedule_data, db_path)
    return schedule_data, check_conflicts(schedule_data, student_course_map)


def gen_timetable_with_sections(db_path):
    """
    Generate timetable with section support using the new section-aware algorithm.
    """
    print("Generating timetable with section support...")
    
    # Get section-aware registration data
    df_merged = registration_data_with_sections(db_path)
    
    if df_merged.empty:
        print("No registration data found, falling back to original algorithm")
        return gen_timetable(db_path)
    
    print(f"Found {len(df_merged)} student-course-section enrollments")
    
    # Use section-specific course identifiers for mapping
    student_course_map = prepare_student_course_section_map(df_merged)
    
    # Get section-specific professor mapping
    course_professor_map = get_course_section_professor_mapping(db_path)
    
    # Convert to the format expected by the algorithm
    course_professor_map_all = {}
    for course_section_id, prof_email in course_professor_map.items():
        course_professor_map_all[course_section_id] = [prof_email]
    
    # Get other required data
    professor_busy_slots = faculty_pref(db_path)
    
    # Create credit and type maps based on base courses
    course_credit_map = {}
    course_type_map = {}
    for _, row in df_merged.iterrows():
        course_section_id = row['G CODE']
        course_credit_map[course_section_id] = row['Credit']
        course_type_map[course_section_id] = row['Type']
    
    time_slots = get_all_time_slots(db_path)
    
    # Preprocess courses and schedule (treating each section as a separate course)
    courses = create_course_dictionary(student_course_map, course_professor_map_all, professor_busy_slots, time_slots)
    
    print(f"Processing {len(courses)} course sections")
    
    # Diagnose constraints
    diagnose_same_day_constraints(courses, course_credit_map)
    
    # Generate schedule
    schedule_data = schedule_courses(courses, student_course_map, course_professor_map_all, course_credit_map, course_type_map, [])

    print("Schedule Data (Section-aware)")
    print(schedule_data)
    print()
    print("Courses on the same day")
    print(find_courses_with_multiple_slots_on_same_day(schedule_data))
    print("Conflicts")
    conflicts = check_conflicts(schedule_data, student_course_map)
    print(conflicts)
    
    # Save schedule to database
    schedule(schedule_data, db_path)
    
    return schedule_data, conflicts


def has_multi_section_courses(db_path):
    """
    Check if the database has any courses with multiple sections.
    
    :param db_path: Path to the database
    :return: True if multi-section courses exist, False otherwise
    """
    try:
        # Ensure migration is done before checking
        if check_migration_needed(db_path):
            migrate_database_for_sections(db_path)
        
        df_merged = registration_data_with_sections(db_path)
        return not df_merged.empty and df_merged['NumberOfSections'].max() > 1
    except Exception as e:
        print(f"Error checking for multi-section courses: {e}")
        return False


def gen_timetable_auto(db_path):
    """
    Automatically choose between section-aware and original timetable generation
    based on whether multi-section courses exist.
    
    :param db_path: Path to the database
    :return: Schedule data and conflicts
    """
    # Ensure database is migrated for sections support
    if check_migration_needed(db_path):
        print("Database migration needed for sections support...")
        migrate_database_for_sections(db_path)
        print("Database migration completed.")
    
    if has_multi_section_courses(db_path):
        print("Multi-section courses detected, using section-aware algorithm")
        return gen_timetable_with_sections(db_path)
    else:
        print("No multi-section courses detected, using original algorithm")
        return gen_timetable(db_path)