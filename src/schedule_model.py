import re
from ortools.sat.python import cp_model

def schedule_courses(courses, student_course_map):
    """
    Schedules courses based on the provided course time slots and student course registrations,
    ensuring no student is scheduled for overlapping courses and each course meets twice a week without conflicts.

    Parameters:
        courses (dict): A dictionary where each key is a course ID and each value is another dictionary
                        containing a list of possible 'time_slots' for that course.
        student_course_map (dict): A dictionary mapping student roll numbers to lists of courses they are enrolled in.

    Returns:
        str: A string representing the scheduled courses and their time slots if a solution is found, 
             otherwise a message indicating that no solution exists.
    """
    model = cp_model.CpModel()

    # Variables for each course and time slot
    course_time_vars = {}
    course_day_vars = {}  # Tracks days for courses
    days = ['Monday ', 'Tuesday ', 'Wednesday ', 'Thursday ', 'Friday ']

    # Define model variables
    for course_id, course_info in courses.items():
        course_time_vars[course_id] = []
        course_day_vars[course_id] = {day: [] for day in days}

        for time_slot in course_info['time_slots']:
            var_id = f'{course_id}_{time_slot}'
            var = model.NewBoolVar(var_id)
            course_time_vars[course_id].append(var)
            match = re.match(r"(\D+)", time_slot)
            if match:
                day = match.group(1)
                if day in days:
                    course_day_vars[course_id][day].append(var)
                else:
                    print(f"Day extracted '{day}' is not recognized as a valid day.")

    # Constraints to ensure each course is scheduled exactly twice
    for course_id, vars in course_time_vars.items():
        model.Add(sum(vars) == 2)

    # Constraint to prevent scheduling a course more than once per day
    for course_id, day_vars in course_day_vars.items():
        for day, vars in day_vars.items():
            model.Add(sum(vars) <= 1)

    # Constraint to prevent students from having overlapping courses
    for roll_number, course_list in student_course_map.items():
        for i in range(len(course_list) - 1):
            for j in range(i + 1, len(course_list)):
                course1 = course_list[i]
                course2 = course_list[j]
                for k, time_slot1 in enumerate(courses[course1]['time_slots']):
                    for l, time_slot2 in enumerate(courses[course2]['time_slots']):
                        if time_slot1 == time_slot2:
                            model.AddBoolOr([
                                course_time_vars[course1][k].Not(),
                                course_time_vars[course2][l].Not()
                            ])

    # Solve the model and extract the schedule
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL:
        print("Solution found!")
        schedule_output = []
        for course_id, vars in course_time_vars.items():
            scheduled_times = [var.Name().split('_')[1] for var in vars if solver.Value(var)]
            schedule_output.append(f"{course_id} is scheduled at: {', '.join(scheduled_times)}")
        return "\n".join(schedule_output)
    else:
        print("No solution exists.")
        return "No solution exists."
