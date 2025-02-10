from data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from utilities import faculty_busy_slots, create_course_dictionary, create_course_credit_map
from schedule_model import schedule_courses
from conflict_checker import check_conflicts, find_courses_with_multiple_slots_on_same_day
import pandas as pd
import random 

def get_student_schedule(roll_no, schedule_df, df_registration, df_courses) : 
    
    df_merged = merge_data(df_registration, df_courses)
    student_course_map = prepare_student_course_map(df_merged)
    
    if roll_no in student_course_map:
        courses = student_course_map[roll_no]
        student_schedule = schedule_df[schedule_df['Course ID'].isin(courses)]
        return student_schedule, check_conflicts(student_schedule, student_course_map)
    else:
        return pd.DataFrame()
    
courses = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\present\Courses.csv")
registration = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\present\Student Registration TOP5.csv")
timetable = pd.read_csv(r"C:\Users\Vatsalya Betala\OneDrive\Documents\Repositories\Time-Table-Optimization-1\Timetable.csv")

roll_no = 'SIASUG2022-0166'
student_schedule, conflicts = get_student_schedule(roll_no, timetable, registration, courses)
print(student_schedule)
print()
print(conflicts)



