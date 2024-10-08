from data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from utilities import faculty_busy_slots, create_course_dictionary
from schedule_model import schedule_courses
from conflict_checker import check_conflicts
import pandas as pd

def gen_timetable(df_registration, df_courses, df_faculty_pref):
    
    df_merged = merge_data(df_registration, df_courses)
    student_course_map = prepare_student_course_map(df_merged)
    course_professor_map = create_course_professor_map(df_merged)
    professor_busy_slots = faculty_busy_slots(df_faculty_pref)

    # Prepare courses and scheduleS
    courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)
    schedule_data = schedule_courses(courses, student_course_map, course_professor_map)
    print("schedule_data")
    print(schedule_data)
    print('--------------------')
    print("Conflicts")
    print(check_conflicts(schedule_data, student_course_map))
    return schedule_data

registration = pd.read_csv(r'C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization\data\Student Registration Data.csv')
faculty_pref = pd.read_csv(r'C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization\data\faculty_pref.csv')
courses = pd.read_csv(r'C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization\data\Students - Courses Offere List - AY 2024-25 - Term 1 - Sheet1.csv')

schedule_data = gen_timetable(registration, courses, faculty_pref)
schedule_data.to_csv("Timetable.csv", index = None) 
