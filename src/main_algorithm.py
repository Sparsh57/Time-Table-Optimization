from .data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map
from .utilities import faculty_busy_slots, create_course_dictionary
from .schedule_model import schedule_courses
from .conflict_checker import check_conflicts
from .database_management.database_retrieval import registration_data, faculty_pref
from .database_management.schedule import schedule
import os

def gen_timetable():
    # Load data
    df_merged = registration_data()
    student_course_map = prepare_student_course_map(df_merged)
    #print(f'student_course_map: {student_course_map}')
    course_professor_map = create_course_professor_map(df_merged)
    professor_busy_slots = faculty_busy_slots(faculty_pref())

    # Prepare courses and scheduleS
    courses = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)
    schedule_data = schedule_courses(courses, student_course_map, course_professor_map)
    #print("schedule_data")
    #print(schedule_data)

    print("Conflicts")
    print(check_conflicts(schedule_data, student_course_map))
    # Check and print scheduling results
    
    
    if isinstance(schedule_data, dict):
        print("Scheduling completed successfully.")
        for course, times in schedule_data.items():
            print(f'{course}: {", ".join(times)}')
    else:
        pass
        #print("showing DATAAA")
        #print(schedule_data)
        print("populating database!!!!!!!!!!!!!!!!")
        # Populates the Schedule Table in the Database.
        schedule(schedule_data)
