from ortools.sat.python import cp_model
import pandas as pd
from typing import Dict, List
from collections import defaultdict
import re
from itertools import combinations

def get_day_from_time_slot(time_slot):
    """
    Extracts the day from the time slot string.
    Assumes that the day is the first word in the time slot string.
    Modify this function based on the actual format of your time slots.
    """
    # Example time slot format: "Monday 9am-10am"
    day = time_slot.split()[0]
    return day

def schedule_courses(courses: Dict[str, Dict[str, List[str]]],
                     student_course_map: Dict[str, List[str]],
                     course_professor_map: Dict[str, str],
                     course_credits: Dict[str, int]) -> pd.DataFrame:
    """
    Schedules courses for a given set of courses, students, and professors,
    ensuring each course is scheduled exactly twice without student conflicts,
    while considering time slot preferences and limiting classes per time slot.
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

    # Soft Constraint: Avoid scheduling the same course more than once on the same day
    penalty_vars = []

    for course_id, time_vars in course_time_vars.items():
        # Mapping from day to time slot variables
        day_time_vars = defaultdict(list)
        for time_slot, var in time_vars.items():
            day = get_day_from_time_slot(time_slot)
            day_time_vars[day].append(var)
        for day, vars_on_day in day_time_vars.items():
            if len(vars_on_day) > 1:
                num_classes_on_day = model.NewIntVar(0, len(vars_on_day), f'num_classes_{course_id}_{day}')
                model.Add(num_classes_on_day == sum(vars_on_day))
                penalty_var = model.NewBoolVar(f'penalty_{course_id}_{day}')
                # penalty_var = 1 if num_classes_on_day >= 2
                model.Add(num_classes_on_day >= 2).OnlyEnforceIf(penalty_var)
                model.Add(num_classes_on_day <= 1).OnlyEnforceIf(penalty_var.Not())
                # Collect penalty_var to be added to the objective function
                penalty_vars.append(penalty_var)

    # Add the Objective Function to Minimize Conflicts and Penalties
    # You can adjust the weights to prioritize one over the other
    model.Minimize(1000 * sum(conflict_penalty_vars) + 750 * sum(penalty_vars))

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15 * 60  
    solver.parameters.num_search_workers = 10
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
