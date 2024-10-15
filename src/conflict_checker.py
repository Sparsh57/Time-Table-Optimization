import pandas as pd
from collections import defaultdict

def check_conflicts(schedule_df, student_course_map):
    """
    Checks for scheduling conflicts for each student and returns a DataFrame
    containing all conflicts with details.

    Parameters:
    - schedule_df (pd.DataFrame): DataFrame containing the scheduled courses with their time slots.
    - student_course_map (dict): A mapping of student roll numbers to their enrolled courses.

    Returns:
    - pd.DataFrame: A DataFrame with columns ['Roll No.', 'Conflict Time Slot', 'Conflicting Courses']
                    listing all the conflicts for each student.
    """

    schedule = schedule_df.groupby('Course ID')['Scheduled Time'].apply(list).to_dict()

    conflict_rows = []
    for student, courses in student_course_map.items():
        time_slot_courses = defaultdict(list)
        unscheduled_courses = []
        for course in courses:
            scheduled_times = schedule.get(course)
            if scheduled_times:
                for time_slot in scheduled_times:
                    time_slot_courses[time_slot].append(course)
            else:
                unscheduled_courses.append(course)
        for time_slot, course_list in time_slot_courses.items():
            if len(course_list) > 1:
                # conflict
                conflict_rows.append({
                    'Roll No.': student,
                    'Conflict Time Slot': time_slot,
                    'Conflicting Courses': ', '.join(course_list)
                })
    conflict_df = pd.DataFrame(conflict_rows, columns=['Roll No.', 'Conflict Time Slot', 'Conflicting Courses'])
    return conflict_df
