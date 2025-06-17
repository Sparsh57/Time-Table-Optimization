from ortools.sat.python import cp_model
import pandas as pd
from typing import Dict, List, Union
from collections import defaultdict


def get_day_from_time_slot(time_slot: str) -> str:
    """
    Example: "Monday 9am-10am" -> "Monday"
    Adjust if your actual string format is different.
    """
    return time_slot.split()[0]


def schedule_courses(courses: Dict[str, Dict[str, List[str]]],
                     student_course_map: Dict[str, List[str]],
                     course_professor_map: Dict[str, Union[str, List[str]]],
                     course_credits: Dict[str, int],
                     course_type: Dict[str, str], 
                     non_preferred_slots: List[str]) -> pd.DataFrame:
    """
    Debug-friendly scheduling function with incremental constraint phases:

      PHASE 1) Each course must appear 'credits' times.
      PHASE 2) Professor cannot teach two courses in the same slot (AddAtMostOne).
      PHASE 3) Limit each slot to at most 30 classes.
      PHASE 4) Student conflicts (soft) -> penalize scheduling multiple courses for one student in the same slot.
               Additionally, a very soft extra penalty is added if a student’s two required courses clash.
      PHASE 5) No same course twice on the same day (hard constraint).

    If a phase is infeasible, we print a debug message and return an empty DataFrame.
    If all phases succeed, we return the final schedule from PHASE 5.

    NOTE: The function signature is unchanged. The incremental approach is done internally.
    """

    # ---------------------------------------------------------
    # Parameters you can tweak
    # ---------------------------------------------------------
    MAX_CLASSES_PER_SLOT = 24
    STUDENT_CONFLICT_WEIGHT = 1000  # penalty weight for each student conflict
    REQUIRED_CONFLICT_WEIGHT = 10    # very soft penalty for a clash between two Required courses
    NON_PREFERRED_SLOTS = 50
    # ---------------------------------------------------------
    # Quick Pre-Check for "credits > available slots" problems
    # ---------------------------------------------------------
    for c_id, info in courses.items():
        needed = course_credits.get(c_id, 2)  # default if missing
        possible = len(info["time_slots"])
        if needed > possible:
            print(f"[PRE-CHECK] Course '{c_id}' needs {needed} sessions but only has {possible} slot(s). Infeasible.")
            return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    def solve_phase(phase_name: str,
                    add_prof_constraints=False,
                    add_timeslot_capacity=False,
                    add_student_conflicts=False,
                    add_no_same_day=False):
        """
        Builds and solves a new model with specified constraints included.
        Returns (status, schedule_df).
        """
        model = cp_model.CpModel()

        # Collect all distinct time slots globally
        all_time_slots = set()
        for c_info in courses.values():
            all_time_slots.update(c_info['time_slots'])
        all_time_slots = sorted(all_time_slots)

        # Create bool vars: course_time_vars[c][slot] = 1 if c is in slot
        course_time_vars = {}
        time_slot_count_vars = defaultdict(list)  # for capacity constraints

        for c_id, c_info in courses.items():
            slot_dict = {}
            for slot in c_info['time_slots']:
                var = model.NewBoolVar(f'{c_id}_{slot}')
                slot_dict[slot] = var
                time_slot_count_vars[slot].append(var)
            course_time_vars[c_id] = slot_dict

        # PHASE 1) Each course must appear exactly 'course_credits[c_id]' times
        for c_id, slot_dict in course_time_vars.items():
            needed = course_credits.get(c_id, 2)  # fallback if missing
            model.Add(sum(slot_dict.values()) == needed)

        # PHASE 2) Professor constraints
        if add_prof_constraints:
            prof_dict = defaultdict(list)
            for c_id, profs in course_professor_map.items():
                # Handle both single professor (string) and multiple professors (list)
                if isinstance(profs, str):
                    profs = [profs]
                elif profs is None:
                    profs = []
                
                # Add course to each professor's list
                for prof in profs:
                    prof_dict[prof].append(c_id)

            for prof, c_list in prof_dict.items():
                # For each time slot, a professor cannot teach more than one course
                slot_map = defaultdict(list)
                for pc_id in c_list:
                    if pc_id in course_time_vars:
                        for s, v in course_time_vars[pc_id].items():
                            slot_map[s].append(v)
                for s, var_list in slot_map.items():
                    if len(var_list) > 1:
                        model.AddAtMostOne(var_list)

        # PHASE 3) Time slot capacity
        if add_timeslot_capacity:
            for slot, var_list in time_slot_count_vars.items():
                model.Add(sum(var_list) <= MAX_CLASSES_PER_SLOT)

        # PHASE 4) Student conflicts (soft)
        conflict_vars = []
        if add_student_conflicts:
            for student_id, enrolled in student_course_map.items():
                # Build mapping: time slot -> list of booleans for this student's courses
                slot_map = defaultdict(list)
                for c_id in enrolled:
                    if c_id in course_time_vars:
                        for s, v in course_time_vars[c_id].items():
                            slot_map[s].append(v)
                for s, var_list in slot_map.items():
                    if len(var_list) > 1:
                        # conflict_var = 1 if sum(var_list) >= 2
                        conflict_var = model.NewBoolVar(f'conflict_{student_id}_{s}')
                        model.Add(sum(var_list) >= 2).OnlyEnforceIf(conflict_var)
                        model.Add(sum(var_list) <= 1).OnlyEnforceIf(conflict_var.Not())
                        conflict_vars.append(conflict_var)

        # Additional very soft constraint: Avoid conflict between two Required courses
        conflict_required_vars = []
        if add_student_conflicts:
            for student_id, enrolled in student_course_map.items():
                # Filter only the courses that are marked as 'Required'
                required_courses = [c_id for c_id in enrolled if course_type.get(c_id, "Elective") == "Required"]
                slot_map_req = defaultdict(list)
                for c_id in required_courses:
                    if c_id in course_time_vars:
                        for s, v in course_time_vars[c_id].items():
                            slot_map_req[s].append(v)
                for s, var_list in slot_map_req.items():
                    if len(var_list) > 1:
                        conflict_req_var = model.NewBoolVar(f'req_conflict_{student_id}_{s}')
                        model.Add(sum(var_list) >= 2).OnlyEnforceIf(conflict_req_var)
                        model.Add(sum(var_list) <= 1).OnlyEnforceIf(conflict_req_var.Not())
                        conflict_required_vars.append(conflict_req_var)

        # PHASE 5) No same course twice on the same day (hard constraint)
        if add_no_same_day:
            for c_id, slot_dict in course_time_vars.items():
                # Group the course's slots by day
                day_map = defaultdict(list)
                for s, var in slot_dict.items():
                    day = get_day_from_time_slot(s)
                    day_map[day].append(var)
                # Each day can have at most 1 session of this course
                for day, var_list in day_map.items():
                    if len(var_list) > 1:
                        model.Add(sum(var_list) <= 1)
        
        # PHASE 6) No classes on consecutive days
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_to_index = {day: idx for idx, day in enumerate(day_order)}
        
        for c_id, slot_dict in course_time_vars.items():
            day_vars = defaultdict(list) # empty-list as keys; can use append
            for s, vars in slot_dict.items(): # Fetches from the slot dictionary of the given course c_id. (s -> slot, vars -> CP-SAT BOOL VAR) 
                day = get_day_from_time_slot(s)
                day_vars[day].append(var)

            for i in range(6): 
                d1, d2 = day_order[i], day_order[i+1] # Fetches consective days 
                if d1 in day_vars and d2 in day_vars:
                    d1_var = model.NewBoolVar(f'{c_id}_on_{d1}')
                    d2_var = model.NewBoolVar(f'{c_id}_on_{d2}')
                    model.AddMaxEquality(d1_var, day_vars[d1]) # Binds each *_var to the list of time slots on that day.
                    model.AddMaxEquality(d2_var, day_vars[d2]) # Same here 
                    model.Add(d1_var + d2_var <= 1) # The constraint itsel - course can be scheduled on d1 or d2, but not both.
                
        slot_penalty_vars = []
        # We retrieve the course_id and the dictionary 
        # with key as the timeslots and the values as the boolean decision variables 
        for c_id, slot_dict in course_time_vars.items(): 
            # We retieve the timeslot and the boolean associated with that
            for s, var in slot_dict.items(): 
                if s in non_preferred_slots: 
                    slot_penalty_vars.append(var)

        # Objective: minimize student conflicts (with additional required course penalty, if any)
        total_penalty = 0
        if conflict_vars:
            total_penalty += STUDENT_CONFLICT_WEIGHT * sum(conflict_vars)
        if conflict_required_vars:
            total_penalty += REQUIRED_CONFLICT_WEIGHT * sum(conflict_required_vars)
        if slot_penalty_vars: 
            total_penalty += NON_PREFERRED_SLOTS * sum(slot_penalty_vars)
        model.Minimize(total_penalty)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # short limit per phase
        status = solver.Solve(model)

        schedule_df = pd.DataFrame(columns=["Course ID", "Scheduled Time"])
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            rows = []
            for c_id, slot_dict in course_time_vars.items():
                for s, var in slot_dict.items():
                    if solver.Value(var) == 1:
                        rows.append({"Course ID": c_id, "Scheduled Time": s})
            schedule_df = pd.DataFrame(rows)

        return status, schedule_df

    # ---------------------------------------------------------
    # Phase-by-phase approach
    # ---------------------------------------------------------

    # PHASE 1
    p1_status, p1_df = solve_phase("PHASE 1",
                                   add_prof_constraints=False,
                                   add_timeslot_capacity=False,
                                   add_student_conflicts=False,
                                   add_no_same_day=False)
    if p1_status == cp_model.INFEASIBLE:
        print("[DEBUG] Infeasible at PHASE 1: Basic 'credits' constraints.")
        return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    # PHASE 2
    p2_status, p2_df = solve_phase("PHASE 2",
                                   add_prof_constraints=True,
                                   add_timeslot_capacity=False,
                                   add_student_conflicts=False,
                                   add_no_same_day=False)
    if p2_status == cp_model.INFEASIBLE:
        print("[DEBUG] Infeasible at PHASE 2: Professor no-overlap constraints.")
        return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    # PHASE 3
    p3_status, p3_df = solve_phase("PHASE 3",
                                   add_prof_constraints=True,
                                   add_timeslot_capacity=True,
                                   add_student_conflicts=False,
                                   add_no_same_day=False)
    if p3_status == cp_model.INFEASIBLE:
        print(f"[DEBUG] Infeasible at PHASE 3: Time slot capacity <= {MAX_CLASSES_PER_SLOT}.")
        return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    # PHASE 4
    p4_status, p4_df = solve_phase("PHASE 4",
                                   add_prof_constraints=True,
                                   add_timeslot_capacity=True,
                                   add_student_conflicts=True,
                                   add_no_same_day=False)
    if p4_status == cp_model.INFEASIBLE:
        # Rare for soft conflicts to cause infeasibility, but we check anyway
        print("[DEBUG] Infeasible at PHASE 4: Student conflict constraints.")
        return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    # PHASE 5: No same course twice on the same day
    p5_status, p5_df = solve_phase("PHASE 5",
                                   add_prof_constraints=True,
                                   add_timeslot_capacity=True,
                                   add_student_conflicts=True,
                                   add_no_same_day=True)
    if p5_status == cp_model.INFEASIBLE:
        print("[DEBUG] Infeasible at PHASE 5: The 'no same course twice on the same day' constraint.")
        print("Check if any course's distribution of slots forces multiple sessions on the same day.")
        return pd.DataFrame(columns=["Course ID", "Scheduled Time"])

    # If we got here, it's feasible through PHASE 5
    print("[DEBUG] Schedule found with all constraints (including no same-day double scheduling).")
    return p5_df