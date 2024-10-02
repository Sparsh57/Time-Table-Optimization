import csv
import random

num_students = 1000
num_profs = 100
num_courses = 100
courses_per_student = 4

#gen_prof_names
prof_names = []
for i in range(num_profs):
    prof_names.append(f"prof_{i}")

#gen_courses
course_names = []
for i in range(num_courses):
    course_names.append(f"course_{i}")

#gen_students
student_names = []
for i in range(num_students):
    student_names.append(f"student_{i}")


#course_list generateion
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
courses_offered = []
check_list = []
for course in course_names:
    prof = select_with_prob(prof_names,check_list,75,2,3)
    courses_offered.append({"Course code":course,"Faculty Name":prof})
    check_list.append(prof)

print(courses_offered)

with open('Students - Courses Offere List - AY 2024-25 - Term 1 - Sheet1.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Course code","Faculty Name"])
    for i in courses_offered:
        writer.writerow([i["Course code"],i["Faculty Name"]])


