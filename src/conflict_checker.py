def check_conflicts(schedule, student_course_map):
    conflicts = {}
    for student, courses in student_course_map.items():
        times = []
        for course in courses:
            times.extend(schedule.get(course, []))
        # Check if any times appear more than once
        if len(times) != len(set(times)):
            # Detect and store the conflict times
            conflict_times = [time for time in times if times.count(time) > 1]
            conflicts[student] = conflict_times
    return conflicts
