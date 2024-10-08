import pandas as pd
from data_preprocessing import merge_data,prepare_student_course_map,create_course_professor_map
from main_algorithm import gen_timetable

student_reg = pd.read_excel("data/Test_Stud_reg.xlsx")
prof_course = pd.read_excel("data/Test_Student Course.xlsx")
faculty_pref = pd.read_csv("data/faculty_pref2.csv")

gen_timetable(student_reg,prof_course,faculty_pref)
