import csv
import random 
import pandas as pd
import os

# Get the current working directory
path = os.getcwd()

num_students = 100
num_profs = 100
num_courses = 100
courses_per_student = 4

# Gen_prof_names
prof_names = []
for i in range(num_profs):
    prof_names.append(f"prof{i}")

# Gen_courses
course_names = []
for i in range(num_courses):
    course_names.append(f"course{i}")

# Gen_students
student_names = []
for i in range(num_students):
    student_names.append(f"student{i}")

def select_with_prob(choice_list, check_list, repeat_percent,middle_num,max_num):
    choice = random.choice(choice_list)
    count = sum(1 for i in check_list if i == choice)
    num = random.randint(0,101)
    if count<middle_num and num<=repeat_percent:
        select_with_prob(choice_list, check_list, repeat_percent,middle_num,max_num)
    if count>=max_num:
        select_with_prob(choice_list, check_list, repeat_percent,middle_num,max_num)
    else:
        return choice

def gen_course_list(prof_names,course_names):
    # Course_list generation
    courses_offered = []
    check_list = []
    for course in course_names:
        prof = select_with_prob(prof_names,check_list,75,2,3)
        courses_offered.append({"Course code":course,"Faculty Name":prof,"Course Type":"Required"})
        check_list.append(prof)
    df = pd.DataFrame(courses_offered)
    df.to_csv("test_data/Students - Courses Offere List - AY 2024-25 - Term 1 - Sheet1.csv",index=False)

# Faculty Pref
def generate_faculty_schedule(faculty_names):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    times = ['08:30', '10:30', '12:30', '14:30', '16:30', '18:30']
    
    data = []
    
    for name in faculty_names:
        busy_count = random.randint(1, 15) 
        busy_slots = set()
        
        while len(busy_slots) < busy_count:
            day = random.choice(days)
            time = random.choice(times)
            busy_slots.add((day, time))
        
        for slots in busy_slots: 
            data.append({'Name':name, 'Busy Slot':f'{slots[0]} {slots[1]}'})
            
    df = pd.DataFrame(data)
    df.to_csv('test_data/faculty_pref.csv', index=False)

def gen_student_csv(student_list, course_list):
    data = []
    for student in student_list:
        courses = random.sample(course_list, 4)
        for i in courses:
            data.append({"Roll No.":student,"G CODE":i,"Sections": "A"})
    df = pd.DataFrame(data)
    df.to_csv("test_data/Student Registration Data.csv",index=False)

gen_course_list(prof_names,course_names)
generate_faculty_schedule(prof_names)
gen_student_csv(student_names,course_names)
