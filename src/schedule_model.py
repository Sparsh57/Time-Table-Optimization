import re
from ortools.sat.python import cp_model

def schedule_courses(courses, student_course_map):
    model = cp_model.CpModel()
    
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
    course_time_vars = {}
    course_day_vars = {}
    days = ['Monday ', 'Tuesday ', 'Wednesday ', 'Thursday ', 'Friday ']
    all_penalty_vars = []  # List to hold all penalty variables

    # model variables
    for course_id, course_info in courses.items():
        course_time_vars[course_id] = []  # {'COURSE_ID': [], .. , }
        course_day_vars[course_id] = {day: [] for day in days} # {'Monday ': [], 'Tuesday ': [], 
                                                               # 'Wednesday ': [], 'Thursday ': [],'Friday ': []}

        for time_slot in course_info['time_slots']: 
            var_id = f'{course_id}_{time_slot}'  # COURSE_ID_TIME_SLOT
            var = model.NewBoolVar(var_id) # A new boolean variable is created.
            course_time_vars[course_id].append(var)

            # course_time_vars = {
            #'COURSE_ID1': [var_Mon9AM, var_Tue10AM, var_Wed11AM, ...],
            # 'COURSE_ID2': [var_Mon10AM, var_Tue11AM, var_Wed9AM, ...], } 
            # Here, each list contains boolean variables where each variable 
            # represents whether a specific course is scheduled at a specific time slot.
        
            match = re.match(r"(\D+)", time_slot)
            if match:
                day = match.group(1) # Day
                course_day_vars[course_id][day].append(var) # {CourseID: {Monday:[], Tuesday:[], ..}, .. ,}

    ## Constraints for each course to be scheduled exactly twice 
    # Exactly Two True: Out of all the boolean variables listed for each course, exactly two must evaluate 
    # to True in any valid solution.
    
    for course_id, vars in course_time_vars.items(): 
        model.Add(sum(vars) == 2) 

    ## Add constraints for no more than one time slot per day per course
    for course_id, day_vars in course_day_vars.items():  
        for day, vars in day_vars.items(): # day_vars is a dictionary 
            model.Add(sum(vars) <= 1) 

    ## Define penalties for conflicts and adjust constraints for overlapping courses
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

    if all_penalty_vars:
        model.Minimize(sum(all_penalty_vars))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL:
        print("Optimized solution found with minimized conflicts!")
        schedule_output = []
        for course_id, vars in course_time_vars.items():
            scheduled_times = [var.Name().split('_')[1] for var in vars if solver.Value(var)]
            schedule_output.append(f"{course_id} is scheduled at: {', '.join(scheduled_times)}")
        return "\n".join(schedule_output)
    else:
        return "No feasible solution found."
