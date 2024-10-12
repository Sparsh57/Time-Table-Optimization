from collections import Counter

def check_conflicts(schedule_df, student_course_map):
    # Convert the schedule DataFrame to a dictionary for faster lookup
    # Mapping from course code to list of scheduled times
    schedule = schedule_df.groupby('Course ID')['Scheduled Time'].apply(list).to_dict()

    conflicts = {}
    for student, courses in student_course_map.items():
        times = []
        unscheduled_courses = []
        for course in courses:
            scheduled_times = schedule.get(course)
            if scheduled_times:
                times.extend(scheduled_times)
            else:
                unscheduled_courses.append(course)
        # Check for conflicts
        time_counts = Counter(times)
        conflict_times = [time for time, count in time_counts.items() if count > 1]
        if conflict_times or unscheduled_courses:
            conflicts[student] = {
                'conflict_times': conflict_times,
                'unscheduled_courses': unscheduled_courses
            }
    return conflicts
