from ortools.sat.python import cp_model
import pandas as pd
import re
from itertools import combinations
from typing import Dict, List


def schedule_courses(courses: Dict[str, Dict[str, List[str]]],
                     student_course_map: Dict[str, List[str]],
                     course_professor_map: Dict[str, str]) -> pd.DataFrame:
    """
    Schedules courses for a given set of courses, students, and professors,
    ensuring no conflicts and adherence to constraints.

    Parameters:
    - courses (dict): A dictionary where each key is a course ID and its value
                      is a dictionary containing course details, including
                      available time slots.
    - student_course_map (dict): A mapping of student roll numbers to their
                                  enrolled courses.
    - course_professor_map (dict): A mapping of course IDs to their respective
                                    professors.

    Returns:
    - pd.DataFrame: A DataFrame containing scheduled courses with their
                    corresponding time slots, or an empty DataFrame if no
                    feasible solution is found.
    """

    assert isinstance(courses, dict), "Expected 'courses' to be a dictionary"
    assert isinstance(student_course_map, dict), "Expected 'student_course_map' to be a dictionary"
    assert isinstance(course_professor_map, dict), "Expected 'course_professor_map' to be a dictionary"
    
    # Initialize the constraint programming model
    model = cp_model.CpModel()

    # Dictionaries to hold course variables
    course_time_vars = {}
    course_day_vars = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    all_penalty_vars = []  # Holds penalty variables for conflicts
    time_slot_count_vars = {}  # Holds count variables for time slots

    # Create model variables for each course's time slots
    for course_id, course_info in courses.items():
        course_time_vars[course_id] = []
        course_day_vars[course_id] = {day: [] for day in days}

        for time_slot in course_info['time_slots']:
            var_id = f'{course_id}_{time_slot}'  # Unique variable ID for each course time slot
            var = model.NewBoolVar(var_id)  # Create a boolean variable
            course_time_vars[course_id].append(var)  # Add variable to course time vars

            # Extract the day from the time slot and add the variable to the corresponding day
            match = re.match(r"(\D+)", time_slot)
            if match:
                day = match.group(1).strip()  # Remove any extra spaces
                course_day_vars[course_id][day].append(var)

            # Initialize time slot count variable if not already done
            if time_slot not in time_slot_count_vars:
                time_slot_count_vars[time_slot] = []
            time_slot_count_vars[time_slot].append(var)

    # Constraints for each course to be scheduled exactly twice
    for course_id, vars in course_time_vars.items():
        model.Add(sum(vars) == 2)

    # Add constraints for no more than one time slot per day per course
    for course_id, day_vars in course_day_vars.items():
        for day, vars in day_vars.items():
            model.Add(sum(vars) <= 1)

    # Define penalties for scheduling conflicts for students enrolled in multiple courses
    for roll_number, course_list in student_course_map.items():
        for i in range(len(course_list) - 1):
            for j in range(i + 1, len(course_list)):
                course1 = course_list[i]
                course2 = course_list[j]
                for k, time_slot1 in enumerate(courses[course1]['time_slots']):
                    for l, time_slot2 in enumerate(courses[course2]['time_slots']):
                        if time_slot1 == time_slot2:
                            penalty_var = model.NewBoolVar(f'penalty_{course1}_{course2}_{time_slot1}')
                            model.AddBoolOr([
                                course_time_vars[course1][k].Not(),
                                course_time_vars[course2][l].Not(),
                                penalty_var
                            ])
                            all_penalty_vars.append(penalty_var)

    # Constraints to avoid scheduling two courses taught by the same professor at the same time
    for course_id1, course_id2 in combinations(courses.keys(), 2):
        if course_professor_map[course_id1] == course_professor_map[course_id2]:
            for time_slot1 in courses[course_id1]['time_slots']:
                for time_slot2 in courses[course_id2]['time_slots']:
                    if time_slot1 == time_slot2:
                        # Create a constraint to ensure that not both courses can be scheduled at the same time
                        model.AddBoolOr([
                            course_time_vars[course_id1][courses[course_id1]['time_slots'].index(time_slot1)].Not(),
                            course_time_vars[course_id2][courses[course_id2]['time_slots'].index(time_slot2)].Not()
                        ])

    # Add constraint to limit classes per time slot to a maximum of 15
    for time_slot, vars in time_slot_count_vars.items():
        model.Add(sum(vars) <= 15)

    num_courses = len(courses.keys()) * 2  # Total number of courses, assuming each course is scheduled twice
    num_days = 5  # Number of days in the schedule
    # Define a maximum number of courses scheduled per day (for distribution)
    max_courses_per_day = int((num_courses / num_days) * (1.3))
    for day in days:
        day_vars = []
        for course_id, vars in course_day_vars.items():
            day_vars.extend(vars[day])  # Collect all course variables for the day
        excess_courses = model.NewIntVar(0, num_courses, f'excess_courses_{day}')
        model.Add(sum(day_vars) <= max_courses_per_day + excess_courses)        # Limit courses scheduled per day
        all_penalty_vars.append(excess_courses)

    # Distribute the total classes evenly across time slots
    total_classes = sum(len(course_info['time_slots']) for course_info in courses.values())
    num_time_slots = len(time_slot_count_vars)
    max_classes_per_time_slot = total_classes // num_time_slots + 1  # Allow for slight overage

    for time_slot, vars in time_slot_count_vars.items():
        # Define an integer variable to track excess classes in this time slot
        excess_classes = model.NewIntVar(0, total_classes, f'excess_classes_{time_slot}')

        # Add a soft constraint: number of classes in this time slot can exceed the limit by 'excess_classes'
        model.Add(sum(vars) <= max_classes_per_time_slot + excess_classes)

        # Penalize excess classes in the minimization objective
        all_penalty_vars.append(excess_classes) # Limit classes per time slot

    # Minimize penalties for conflicts
    if all_penalty_vars:
        model.Minimize(sum(all_penalty_vars))

    # Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Creating a DataFrame to hold the schedule
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        data = []
        for course_id, vars in course_time_vars.items():
            times = [var.Name().split('_')[1] for var in vars if solver.Value(var)]
            for time in times:
                data.append({'Course ID': course_id, 'Scheduled Time': time})
        schedule_df = pd.DataFrame(data)  # Create DataFrame from the scheduling data
        return schedule_df
    else:
        print("No feasible solution found.")
        return pd.DataFrame(columns=['Course ID', 'Scheduled Time'])  # Return empty DataFrame if no solution
