# Algorithm Notes

Person: Siya Jethliya, Vatsalya Betala

# Components of a Constraint Programming Model

Authored - Vatsalya Betala

## 1. Variables

For instance, if you have a course named "Math101" and time slots like "Monday9AM", "Tuesday10AM", etc., then each possible pairing of course and time slot is a variable:

In CP, the first step is to define the variables. These are typically the elements of the problem that we need to assign values to. For instance, in our scheduling problem, each course with it’s possible timeslots is a variables. 

- `Math101_Monday9AM`
- `Math101_Tuesday10AM`
- `Eng202_Monday9AM`
- `Eng202_Wednesday11AM`

## 2. Domain

Referencing to the variables, each variable had domain set, which is basically the set of all the possible values that the variables can take. In this case, we have a binary problem, where 1 represents that a course is being schedules at that time and 0 that it is not being scheduled.

## 3. Constraints

Constraints are rules that limit the values that variables can simultaneously take. In our scheduling model, we have constraints that ensure: 

- Each course is scheduled exactly twice per week.
- Optional constraints, such as not scheduling a course more than once per day.
- No overlapping courses for any student.

### a. Course Frequency Constraint

**Objective**: It ensures that each course is being schedules only twice per week. 

**Implementation**: 

- For each course, you sum the variables associated with all the possible time slots for that course and set the sum equal to two.
- Example: If "Math101" can be scheduled at "Monday 9AM", "Tuesday 10AM", and "Wednesday 11AM", you would have the following constraint:
`Math101_Monday9AM + Math101_Tuesday10AM + Math101_Wednesday11AM = 2`

### b. No Multiple Sessions Per Day for a Single Course

**Objective**: Ensure that a course is not scheduled more than once on any single day**.**

**Code:** 

```python
for course_id, day_vars in course_day_vars.items():  
# {CourseID: {Monday:[], Tuesday:[], ..}, .. ,}
        for day, vars in day_vars.items(): # day_vars is a dictionary 
            model.Add(sum(vars) <= 1) 
            
            
```

**Implementation:** 

- The outer loop iterated over each course, and accesses a dictionary that groups scheduling variables by the days of the week.
- The inner loop iterates and accesses a list of Boolean variables, which has all the potential time slots for that day of the week.
- We apply the constraint, by making sure that the sum of this list of Boolean variables (representing the potential time slots on a specific day) is less than or equal to one. This will imply that the course is at most scheduled once per day.

### c. No Overlapping Courses for Students

**Objective:**

Prevent any student from having to attend two courses at the same time

**Code:** 

```python
for roll_number, course_list in student_course_map.items(): 
        for i in range(len(course_list) - 1): 
            for j in range(i + 1, len(course_list)):
                course1 = course_list[i]
                course2 = course_list[j]
                # These nested loops iterate through each pair of courses for each student.
                # They ensure that every pair of courses that the student is taking is considered exactly once. 
                # This essentially helps in checking every possible combination of course conflicts. 
                for k, time_slot1 in enumerate(courses[course1]['time_slots']):
                    for l, time_slot2 in enumerate(courses[course2]['time_slots']):
                        if time_slot1 == time_slot2:
                            penalty_var = model.NewBoolVar(f'penalty_{course1}_{course2}_{time_slot1}')
                            model.AddBoolOr([
                                course_time_vars[course1][k].Not(),
                                course_time_vars[course2][l].Not(),
                                penalty_var
                            ])
                            # The AddBoolOr constraint allows for two courses to not be scheduled at the 
                            # same conflicting time (by negating the variables with .Not()) or for the penalty
                            # variable to be activated (indicating that this conflict was unavoidable and hence accepted).
                            all_penalty_vars.append(penalty_var)

```

**Implementation:** 

- **Iterate Over Each Student's Courses**:
    - The code iterates over each student and the list of courses they are enrolled in. It uses nested loops to compare every possible pair of courses for each student to check for scheduling conflicts.
- **Check Course Time Slots for Overlaps**:
    - For each pair of courses, it examines all possible time slots. If the same time slot appears in both courses, a potential conflict is identified.

**Conflict Resolution Using Boolean Logic**:

- **Penalty Variable**: A Boolean variable (`penalty_var`) is created for each conflict. This variable will be true if the conflict is accepted (i.e., both courses end up scheduled at the same time)
- **`AddBoolOr`Constraint**: This constraint ensures that either one of the courses is not scheduled at the conflicting time (by setting the corresponding variable to false), or the penalty variable is activated.

### d. No Overlapping Courses for Professors

**Objective:**

Ensure that no professor is scheduled to teach two different courses at the same time.

**Code:**

```python
for course_id1, course_id2 in combinations(courses.keys(), 2):
    if course_professor_map[course_id1] == course_professor_map[course_id2]:
        # Check if the same professor is assigned to both courses
        for time_slot1 in courses[course_id1]['time_slots']:
            for time_slot2 in courses[course_id2]['time_slots']:
                if time_slot1 == time_slot2:
                    # If the same time slot is found in both courses, add a constraint to avoid this clash
                    model.AddBoolOr([
                        course_time_vars[course_id1][courses[course_id1]['time_slots'].index(time_slot1)].Not(),
                        course_time_vars[course_id2][courses[course_id2]['time_slots'].index(time_slot2)].Not()
                    ])
                    # This constraint ensures that not both courses are scheduled at the same time, preventing the professor
                    # from being double-booked.

```

**Implementation:**

- **Iterate Over Course Combinations**:
    - The code first checks all possible pairs of courses using the combination of course keys. It ensures each pair is checked only once for potential scheduling conflicts involving the same professor.
- **Check Professor Assignments for Overlaps**:
    - For each pair, if the same professor is assigned to both courses, it examines the time slots of these courses for overlaps.

**Conflict Resolution Using Boolean Logic**:

- **`AddBoolOr` Constraint**: This function ensures that if a time slot conflict is detected between two courses taught by the same professor, then one of the courses must not be scheduled at that time (i.e., the corresponding course variable is set to false).

### d. Limit Classes per Time Slot

**Objective:**

Limit the number of classes scheduled in any single time slot across all courses to a specified maximum.

**Code:**

```python
for time_slot, vars in time_slot_count_vars.items():
    model.Add(sum(vars) <= 15)
    # This constraint limits the number of courses that can be scheduled at the same time across the entire institution to 15
    # to prevent resource overallocation and ensure manageable class sizes and space utilization.

```

**Implementation:**

- **Aggregate Courses by Time Slot**:
    - The code aggregates all course variables associated with each specific time slot across all courses.
- **Apply Maximum Limit**:
    - A hard limit of 15 classes per time slot is enforced, ensuring that no more than 15 courses are scheduled simultaneously, which helps in managing classroom and resource allocation effectively.

**Using a Hard Constraint**:

- **Hard Limit**: Unlike soft constraints that allow flexibility, this constraint strictly enforces the limit to prevent resource conflicts and ensure effective learning environments.

These explanations outline the necessity of each constraint and how they function within the scheduling model, providing a clear framework for managing complex scheduling requirements.

## Starting the Solve Process:

### 1. **Variable Selection - Smallest Domain First**:

- **Rationale**: Typically, the "smallest domain first" heuristic selects the variable with the fewest possible values to simplify the decision-making process and reduce complexity early. However, since all variables in our model (course-time slot pairs) inherently have the same domain size (binary: scheduled or not scheduled), this heuristic doesn't directly apply in its traditional form.

### 2. **Value Selection**

Once a variable is selected, the solver needs to decide what value to try first. In most cases, the *least constraining value* is picked (a value that leaves the largest number of choices for the remaining variables)

To address this, we employ a Value Selection strategy that prioritizes assigning values to courses based on the number of available time slots they have.

1. **Assessment** - At each step of the scheduling process, we assess how many viable time slots are left for each unscheduled course.
2. **Prioritization** - We then prioritize scheduling those courses with the fewest available slots. This approach reduces the risk of a course running out of feasible slots as the scheduling process progresses.
3. **Implementation** - For example, if 'History 301' has only one possible slot remaining and 'Math 101' has three, we schedule 'History 301' first to ensure it has a place in the schedule without conflict."

### 3. Constraint Propagation

- After a variable is assigned a value (from the domain), the solver immediately uses constraint propagation to reduce the domain size of the other variables.
- For examples, if a value to one variables is assigned a value then it essentially means it’s scheduled or not. Let’s assume it’s scheduled. If it’s schedules the the model propagates through the domains of all the other variable and reduces the domain size. Like in our case, it would be all  the variables of the course for the same time for all the students in  the course which is assigned a value.

When a value is assigned to a variable in a course scheduling model, indicating that a course is scheduled at a specific time, the model automatically propagates this decision through the domains of all related variables to enforce the scheduling constraints. This propagation leads to a reduction in the domain sizes of other variables. 

For instance, if Course1 is scheduled at a given time, the system will automatically adjust the domains for all other courses that are scheduled at the same time and are taken by students enrolled in Course1 to False, hence reducing the search space. 

### **Example: Course Scheduling**

Imagine you are scheduling two courses, Math 101 and English 102, which need to be placed into two time slots, 9 AM and 10 AM. Assume that due to student enrollment overlaps, these two courses cannot be scheduled at the same time.

### Example Setup with Student Enrollments

**Courses**:

- Math 101
- English 201
- History 301
- Science 401

**Time Slots**:

- Monday 9 AM
- Wednesday 10 AM
- Friday 11 AM

**Students**:

- Student A: Enrolled in Math 101 and English 201
- Student B: Enrolled in English 201 and History 301
- Student C: Enrolled in History 301 and Science 401

### Step 1: Define Variables

Each course and time slot pairing remains a variable:

- `Math101_Monday9AM`, `Math101_Wednesday10AM`, `Math101_Friday11AM`
- `English201_Monday9AM`, `English201_Wednesday10AM`, `English201_Friday11AM`
- `History301_Monday9AM`, `History301_Wednesday10AM`, `History301_Friday11AM`
- `Science401_Monday9AM`, `Science401_Wednesday10AM`, `Science401_Friday11AM`

### Step 2: Define Domain

Each variable can be either 0 (not scheduled at that time) or 1 (scheduled at that time).

**`D(X) = {0,1}`**

### Step 3: Define Constraints

1. **Single Scheduling per Course**:
    - Each course must be scheduled exactly once.
    - E.g., `Math101_Monday9AM + Math101_Wednesday10AM + Math101_Friday11AM = 1`
2. **Non-Overlapping Courses for Students**:
    - Courses in which a student is enrolled cannot overlap in time.
    - For Student A (`Math 101` and `English 201`):
        - `Math101_*` and `English201_*` cannot both be 1 for the same `` time slot.

### Step 4: Constraint Propagation Example

To visualize how constraint propagation works in this setup, let’s assume some initial decisions and follow through with the implications.

### Initial Decisions and Propagation

- Suppose `Math101_Monday9AM = 1` is chosen.
- This decision automatically sets:
    - `Math101_Wednesday10AM = 0` and `Math101_Friday11AM = 0`
    - For Student A (also in English 201), set `English201_Monday9AM = 0`

### Impact on Remaining Variables

- Next, consider `English201_Wednesday10AM = 1` (since Monday is no longer available for Student A).
- This forces:
    - `English201_Monday9AM = 0` and `English201_Friday11AM = 0`
    - For Student B (also in History 301), we set `History301_Wednesday10AM = 0`

### Continued Scheduling

- With `English201` and `Math101` scheduled, look at available slots for `History301` and `Science401`, keeping student enrollments in mind.
- Suppose `History301_Friday11AM = 1` is chosen:
    - This sets `History301_Monday9AM = 0` and `History301_Wednesday10AM = 0`
    - For Student C, this decision impacts `Science401` scheduling, preventing a Friday 11 AM slot.