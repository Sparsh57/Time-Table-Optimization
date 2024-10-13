def faculty_busy_slots(df_faculty_pref):
    return df_faculty_pref.groupby("Name")["Busy Slot"].agg(list).to_dict()

def create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots):
    unique_courses = set().union(*student_course_map.values())
    course_availability = {}
    for course in unique_courses:
        professor = course_professor_map.get(course, None)
        busy_slots = professor_busy_slots.get(professor, [])
        all_slots = [f'{day} {time}' for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                     for time in ['08:30', '10:30', '12:30', '14:30', '16:30', '18:30']]

        # Add specific exclusions for Wednesday at 2:30 PM and Tuesday at 2:30 PM
        excluded_slots = {'Wednesday 14:30', 'Tuesday 14:30'}

        # Filter slots by checking both professor busy slots and the excluded slots
        course_availability[course] = {
            'time_slots': [slot for slot in all_slots if slot not in busy_slots and slot not in excluded_slots]
        }
    return course_availability


