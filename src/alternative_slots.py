import pandas as pd
import random
from typing import Dict, List, Tuple
from collections import defaultdict

from data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from utilities import faculty_busy_slots, create_course_dictionary, create_course_credit_map
from schedule_model import schedule_courses
from conflict_checker import check_conflicts, find_courses_with_multiple_slots_on_same_day

def compute_slot_conflicts_detailed(course_id: str,
                                    schedule_data: pd.DataFrame,
                                    registration_df: pd.DataFrame,
                                    courses: Dict[str, Dict]) -> Dict[str, Tuple[int, dict]]:

    students_in_course = registration_df.loc[registration_df["G CODE"] == course_id, "Roll No."].unique()
    possible_slots = set(courses.get(course_id, {}).get("time_slots", []))
    possible_slots.add("Wednesday 14:30")
    possible_slots.add("Tuesday 14:30")
    
    student_schedule_map = defaultdict(lambda: defaultdict(list))  # student -> slot -> list_of_courses_at_that_slot
    
    for student in students_in_course:
        all_courses_this_student = registration_df.loc[registration_df["Roll No."] == student, "G CODE"].unique()
        
        for c in all_courses_this_student:
            c_slots = schedule_data.loc[schedule_data["Course ID"] == c, "Scheduled Time"].unique()
            for slot in c_slots:
                student_schedule_map[student][slot].append(c)
    
    conflict_data = {}
    
    for slot in sorted(possible_slots):
        conflict_count = 0
        conflict_info = {}
        
        for student in students_in_course:
            clashing_courses = student_schedule_map[student].get(slot, [])            
            if len(clashing_courses) > 0:
                conflict_count += 1
                conflict_info[student] = clashing_courses
        
        conflict_data[slot] = (conflict_count, conflict_info)
    
    return conflict_data

def find_min_conflict_slots(course_id: str,
                            schedule_data: pd.DataFrame,
                            registration_df: pd.DataFrame,
                            courses: Dict[str, Dict]) -> Tuple[List[str], pd.DataFrame]:
    """
    1) Uses compute_slot_conflicts_detailed to get conflict_count and conflict_info for each slot.
    2) Builds a DataFrame with columns: [Slot, Conflict Count, Conflict].
    3) Identifies the minimal conflict value and returns:
       - A list of the best (lowest-conflict) slots
       - The full DataFrame with conflict details
    """
    conflict_dict = compute_slot_conflicts_detailed(course_id, schedule_data, registration_df, courses)
    
    rows = []
    for slot, (count, info) in conflict_dict.items():
        rows.append({"Slot": slot, "Conflict Count": count, "Conflict": info})
    
    conflict_df = pd.DataFrame(rows)
    conflict_df.sort_values(by=["Conflict Count", "Slot"], inplace=True)
    conflict_df.reset_index(drop=True, inplace=True)
    
    min_conflict = conflict_df["Conflict Count"].min()
    best_slots = conflict_df.loc[conflict_df["Conflict Count"] == min_conflict, "Slot"].tolist()
    
    return best_slots, conflict_df

schedule_data = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\Timetable.csv")
registration_df = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\data\Student_Registration_TOP_Formatted.csv")
df_courses = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\data\Courses_NEW.csv")
df_faculty_pref = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\data\Faculty_Pref_Empty.csv")

df_merged = merge_data(registration_df, df_courses)
student_course_map = prepare_student_course_map(df_merged)
course_professor_map = create_course_professor_map(df_merged)
professor_busy_slots = faculty_busy_slots(df_faculty_pref)
course_credit_map = create_course_credit_map(df_courses)
courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)
print(courses)

course_id = "MATH203"

best_slots, conflict_table = find_min_conflict_slots(course_id, schedule_data, registration_df, courses)

print(f"Slots with MINIMUM conflicts for '{course_id}': {best_slots}\n")
print("Full Conflict Table (top 10 rows):")
print(conflict_table.head(10))

import re

def sanitize_filename(filename):
    return re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')

filename = sanitize_filename(course_id) + "Conflict_Details.csv"
conflict_table.to_csv(filename, index=False)
print(f"Conflict details saved to {filename}")
