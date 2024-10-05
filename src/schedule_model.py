from ortools.sat.python import cp_model
import pandas as pd
import re
from itertools import combinations


def schedule_courses(courses, student_course_map, course_professor_map):
    model = cp_model.CpModel()

    course_time_vars = {}
    course_day_vars = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    all_penalty_vars = []
    time_slot_count_vars = {}

    # Model variables
    for course_id, course_info in courses.items():
        course_time_vars[course_id] = []
        course_day_vars[course_id] = {day: [] for day in days}

        for time_slot in course_info['time_slots']:
            var_id = f'{course_id}_{time_slot}'
            var = model.NewBoolVar(var_id)
            course_time_vars[course_id].append(var)

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

    # Define penalties for conflicts and adjust constraints for overlapping courses
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

    # Add constraint to limit classes per time slot to a maximum of 14
    for time_slot, vars in time_slot_count_vars.items():
        model.Add(sum(vars) <= 15)

    num_courses = len(courses.keys())*2
    num_days= 5
    # Define a maximum number of courses scheduled per day (for distribution)
    max_courses_per_day = int((num_courses/num_days)*(1.3))
    for day in days:
        day_vars = []
        for course_id, vars in course_day_vars.items():
            day_vars.extend(vars[day])  # Collect all course variables for the day
        model.Add(sum(day_vars) <= max_courses_per_day)

    # Distribute the total classes evenly
    total_classes = sum(len(course_info['time_slots']) for course_info in courses.values())
    num_time_slots = len(time_slot_count_vars)
    max_classes_per_time_slot = total_classes // num_time_slots + 1  # Allow for slight overage

    for time_slot, vars in time_slot_count_vars.items():
        model.Add(sum(vars) <= max_classes_per_time_slot)

    if all_penalty_vars:
        model.Minimize(sum(all_penalty_vars))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Creating a DataFrame to hold the schedule
    if status == cp_model.OPTIMAL:
        data = []
        for course_id, vars in course_time_vars.items():
            times = [var.Name().split('_')[1] for var in vars if solver.Value(var)]
            # print("TIMESS")
            # print(times)
            for time in times:
                data.append({'Course ID': course_id, 'Scheduled Time': time})
        schedule_df = pd.DataFrame(data)
        # print(schedule_df)
        return schedule_df
    else:
        print("No feasible solution found.")
        return pd.DataFrame(columns=['Course ID', 'Scheduled Time'])