from src.database_management.schedule import timetable_made, fetch_schedule_data

def check_conflicts(schedule, student_course_map):
    try:
        conflicts = {}
        for student, courses in student_course_map.items():
            times = []
            for course in courses:
                times.extend(schedule.get(course, []))
            if len(times) != len(set(times)):
                conflicts[student] = times
        return conflicts
    except Exception as e:
        print(f"Error occurred while checking conflicts: {e}")
        raise e 

try:
    print(fetch_schedule_data())
except Exception as e:
    print(f"Error occurred while fetching schedule data: {e}")
    raise e  