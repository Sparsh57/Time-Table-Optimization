from .data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from .utilities import faculty_busy_slots, create_course_dictionary, create_course_credit_map, create_course_elective_map
from .schedule_model import schedule_courses
from .database_management.schedule import schedule
from .database_management.Courses import fetch_course_data
from .conflict_checker import check_conflicts, find_courses_with_multiple_slots_on_same_day
from .database_management.database_retrieval import registration_data, faculty_pref, get_all_time_slots
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
    df_merged = registration_data(db_path)
    student_course_map = prepare_student_course_map(df_merged)
    course_professor_map = create_course_professor_map(df_merged)
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