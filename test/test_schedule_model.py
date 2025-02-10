import unittest
import sys
from pathlib import Path
import pandas as pd

# Get the current file's directory path
current_file_path = Path(__file__).resolve()

# Get the grandparent directory path, which is two levels up
grandparent_path = current_file_path.parent.parent

# Append the grandparent directory to the system path
sys.path.append(str(grandparent_path))

# Import the schedule_courses function
from src.schedule_model import schedule_courses

class TestCourseScheduling(unittest.TestCase):
    def setUp(self):
        """
        Set up sample input data
        """
        self.courses = {
        'Math101': {'time_slots': ['Monday 9:00', 'Wednesday 11:00', 'Friday 10:00']},
        'CS101': {'time_slots': ['Monday 10:00', 'Tuesday 9:00', 'Thursday 10:00']},
        'History201': {'time_slots': ['Tuesday 11:00', 'Thursday 9:00', 'Friday 11:00']}
    }

        self.student_course_map = {
        'Alice': ['Math101', 'CS101'],
        'Bob': ['CS101', 'History201'],
        'Charlie': ['Math101', 'History201']
    }

        self.course_professor_map = {
        'Math101': 'Prof. Einstein',
        'CS101': 'Prof. Turing',
        'History201': 'Prof. Schliemann'
    }

    def test_schedule_courses(self):
        """
        Test that the scheduling function returns a valid DataFrame with correct columns.
        """
        result = schedule_courses(self.courses, self.student_course_map, self.course_professor_map)

        # Assert that the result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)

        # Check that the columns are correct
        self.assertListEqual(list(result.columns), ['Course ID', 'Scheduled Time'])

        # Check that no courses have been scheduled in conflicting time slots
        conflicting_times = set(result[result.duplicated(subset=['Scheduled Time'], keep=False)]['Scheduled Time'])
        self.assertEqual(len(conflicting_times), 0, "Courses have been scheduled in conflicting time slots")

    def test_no_feasible_solution(self):
        """
        Test case where no feasible solution should exist due to conflicts.
        """
        # Create conflicting data that cannot be scheduled
        conflicting_courses = {
            'C1': {'time_slots': ['Monday 9:00']},  # Only one available slot
            'C2': {'time_slots': ['Monday 9:00']}  # Same slot as C1, and same professor
        }

        # Ensure the student course map only refers to the existing courses
        student_course_map = {'S1': ['C1', 'C2'], 'S2': ['C1', 'C2']}

        # Keep the course_professor_map aligned with the courses
        course_professor_map = {'C1': 'Prof1', 'C2': 'Prof1'}

        result = schedule_courses(conflicting_courses, student_course_map, course_professor_map)

        # Since this is an infeasible scheduling case, we expect an empty DataFrame
        self.assertTrue(result.empty)

    def test_no_conflicts_for_students(self):
        """Students should not have overlapping courses."""
        result = schedule_courses(self.courses, self.student_course_map, self.course_professor_map)
        student_schedule = {}
        for _, row in result.iterrows():
            course, time = row['Course ID'], row['Scheduled Time']
            for student, courses in self.student_course_map.items():
                if course in courses:
                    if student not in student_schedule:
                        student_schedule[student] = []
                    student_schedule[student].append(time)

        for student, times in student_schedule.items():
            self.assertEqual(len(times), len(set(times)), f"Student {student} has overlapping classes.")

    def test_no_conflicts_for_students(self):
        """Students should not have overlapping courses."""
        result = schedule_courses(self.courses, self.student_course_map, self.course_professor_map)
        student_schedule = {}
        for _, row in result.iterrows():
            course, time = row['Course ID'], row['Scheduled Time']
            for student, courses in self.student_course_map.items():
                if course in courses:
                    if student not in student_schedule:
                        student_schedule[student] = []
                    student_schedule[student].append(time)

        for student, times in student_schedule.items():
            self.assertEqual(len(times), len(set(times)), f"Student {student} has overlapping classes.")
    
    def test_professor_conflicts(self):
        """
        Ensure that no professor is scheduled to teach more than one course at the same time.
        """
        result = schedule_courses(self.courses, self.student_course_map, self.course_professor_map)
        professor_schedule = {}

        # Track each professor's courses and times
        for _, row in result.iterrows():
            course = row['Course ID']
            time_slot = row['Scheduled Time']
            professor = self.course_professor_map[course]
            if professor not in professor_schedule:
                professor_schedule[professor] = []
            professor_schedule[professor].append(time_slot)

        # Check for conflicts in professors' schedules
        for professor, slots in professor_schedule.items():
            self.assertEqual(len(slots), len(set(slots)), f"Professor {professor} has overlapping classes.")


if __name__ == '__main__':
    unittest.main()
