from ortools.sat.python import cp_model
import pandas as pd
from typing import Dict, List
from collections import defaultdict
import re
from itertools import combinations


def schedule_courses(courses: Dict[str, Dict[str, List[str]]],
                     student_course_map: Dict[str, List[str]],
                     course_professor_map: Dict[str, str],
                     course_credits: Dict[str, int]) -> pd.DataFrame:
    """
    Schedules courses for a given set of courses, students, and professors,
    ensuring each course is scheduled exactly twice without student conflicts,
    while considering time slot preferences and limiting classes per time slot.

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

    # Initialize the constraint programming model
    model = cp_model.CpModel()

    # List of all time slots
    all_time_slots = set()
    for course_info in courses.values():
        all_time_slots.update(course_info['time_slots'])
    all_time_slots = sorted(all_time_slots)

    # Create variables for course schedules
    # course_time_vars[course_id][time_slot] = BoolVar
    course_time_vars = {}
    # Initialize time slot count vars
    time_slot_count_vars = defaultdict(list)

    for course_id, course_info in courses.items():
        time_vars = {}
        for time_slot in course_info['time_slots']:
            var = model.NewBoolVar(f'{course_id}_{time_slot}')
            time_vars[time_slot] = var
            # Collect variables per time slot for counting
            time_slot_count_vars[time_slot].append(var)
        course_time_vars[course_id] = time_vars

    # Constraint: Schedule each course as per its credits
    for course_id, time_vars in course_time_vars.items():
        if course_id in course_credits:
            model.Add(sum(time_vars.values()) == course_credits[course_id])
        else:
            print(f"Warning: No credit information for course {course_id}. Defaulting to 2 sessions.")
            model.Add(sum(time_vars.values()) == 2)  # defaulting to 2 if no credit info is provided

    # Professor conflict constraints (if a professor teaches multiple courses)
    professor_courses = defaultdict(list)
    for course_id, professor in course_professor_map.items():
        professor_courses[professor].append(course_id)
    for professor, courses_taught in professor_courses.items():
        # For each time slot, ensure the professor is not scheduled for more than one course
        time_slot_vars = defaultdict(list)
        for course_id in courses_taught:
            if course_id in course_time_vars:
                for time_slot, var in course_time_vars[course_id].items():
                    time_slot_vars[time_slot].append(var)
        for time_slot, vars_in_slot in time_slot_vars.items():
            if len(vars_in_slot) > 1:
                model.AddAtMostOne(vars_in_slot)

    # Student conflict constraints
    # For each student, introduce penalty variables for potential conflicts
    conflict_penalty_vars = []

    for student_id, enrolled_courses in student_course_map.items():
        # For each time slot, collect variables for the courses the student is enrolled in
        time_slot_vars = defaultdict(list)
        for course_id in enrolled_courses:
            if course_id in course_time_vars:
                for time_slot, var in course_time_vars[course_id].items():
                    time_slot_vars[time_slot].append(var)
        # For each time slot, create a conflict penalty variable
        for time_slot, vars_in_slot in time_slot_vars.items():
            if len(vars_in_slot) > 1:
                # Create a conflict variable that is 1 if there's a conflict at this time slot
                conflict_var = model.NewBoolVar(f'conflict_{student_id}_{time_slot}')
                # The conflict variable is true if the sum of scheduled courses at this time is >= 2
                # Add implication constraints
                model.Add(sum(vars_in_slot) >= 2).OnlyEnforceIf(conflict_var)
                model.Add(sum(vars_in_slot) <= 1).OnlyEnforceIf(conflict_var.Not())
                # Collect conflict variables to minimize in the objective function
                conflict_penalty_vars.append(conflict_var)

    # Add constraint to limit classes per time slot to a maximum of 15
    for time_slot, vars_in_slot in time_slot_count_vars.items():
        model.Add(sum(vars_in_slot) <= 15)

    # Add the Objective Function to Minimize Conflicts
    # Objective: Minimize the total number of conflicts
    model.Minimize(sum(conflict_penalty_vars))

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300  # Set a time limit of 5 minutes
    solver.parameters.num_search_workers = 8  # Adjust based on your CPU cores
    status = solver.Solve(model)

    # Creating a DataFrame to hold the schedule
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        data = []
        for course_id, time_vars in course_time_vars.items():
            scheduled_times = [time_slot for time_slot, var in time_vars.items() if solver.Value(var)]
            for time_slot in scheduled_times:
                data.append({'Course ID': course_id, 'Scheduled Time': time_slot})
        schedule_df = pd.DataFrame(data)
        return schedule_df
    else:
        if status == cp_model.INFEASIBLE:
            print("No feasible solution found.")
        elif status == cp_model.MODEL_INVALID:
            print("The model is invalid. Please check the constraints and variables.")
        elif status == cp_model.UNKNOWN:
            print("The solver could not find a solution within the given time limit.")
        return pd.DataFrame(columns=['Course ID', 'Scheduled Time'])
