from data_preprocessing import load_data, merge_data, prepare_student_course_map, create_course_professor_map
from utilities import faculty_busy_slots, create_course_dictionary
from schedule_model import schedule_courses
from conflict_checker import check_conflicts

# Load data
df_registration, df_courses, df_faculty_pref = load_data()
df_merged = merge_data(df_registration, df_courses)
student_course_map = prepare_student_course_map(df_merged)
course_professor_map = create_course_professor_map(df_merged)
professor_busy_slots = faculty_busy_slots(df_faculty_pref)

# Prepare courses and scheduleS
courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)
schedule_data = schedule_courses(courses, student_course_map)

# Check and print scheduling results
if isinstance(schedule_data, dict):
    print("Scheduling completed successfully.")
    for course, times in schedule_data.items():
        print(f'{course}: {", ".join(times)}')
else:
    print(schedule_data)