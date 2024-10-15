from data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from utilities import faculty_busy_slots, create_course_dictionary, create_course_credit_map
from schedule_model import schedule_courses
from conflict_checker import check_conflicts, find_courses_with_multiple_slots_on_same_day
import pandas as pd
import random 

def gen_student_csv(student_list, course_list):
    data = []
    for student in student_list:
        courses = random.sample(course_list, 5)
        for i in courses:
            data.append({"Roll No.":student,"G CODE":i,"Sections": "A"})
    df = pd.DataFrame(data)
    df.to_csv("Student Registration Data.csv",index=False)

def gen_timetable(df_registration, df_courses, df_faculty_pref):
    
    df_merged = merge_data(df_registration, df_courses)
    student_course_map = prepare_student_course_map(df_merged)
    course_professor_map = create_course_professor_map(df_merged)
    professor_busy_slots = faculty_busy_slots(df_faculty_pref)
    course_credit_map = create_course_credit_map(df_courses)
    # Prepare courses and scheduleS
    courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)
    schedule_data = schedule_courses(courses, student_course_map, course_professor_map, course_credit_map)
    print("Schedule Data")
    print()
    print(schedule_data)
    print()
    print("Courses on the same day")
    print(find_courses_with_multiple_slots_on_same_day(schedule_data))
    return schedule_data, check_conflicts(schedule_data, student_course_map)

courses = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\present\Courses.csv")
registration = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\present\Student Registration TOP5.csv")
faculty_pref = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\present\Faculty Pref.csv")

schedule_data, conflict_data = gen_timetable(registration, courses, faculty_pref)
schedule_data.to_csv("Timetable.csv", index = None)
conflict_data.to_csv('Conflicts.csv', index = None)
