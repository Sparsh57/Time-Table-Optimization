def check_conflicts(schedule, student_course_map):
    conflicts = {}
    for student, courses in student_course_map.items():
        times = []
        for course in courses:
            times.extend(schedule.get(course, []))
        if len(times) != len(set(times)):
            conflicts[student] = times
    return conflicts