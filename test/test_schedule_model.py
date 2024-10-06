import unittest
import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))

from src.schedule_model import schedule_courses


class TestCourseScheduling(unittest.TestCase):
    def setUp(self):
        """
        Set up sample input data for testing.
        """
        self.courses = {
            'C1': {'time_slots': ['Monday 9:00', 'Tuesday 10:00', 'Wednesday 11:00']},
            'C2': {'time_slots': ['Monday 9:00', 'Tuesday 10:00', 'Wednesday 11:00']},
            'C3': {'time_slots': ['Tuesday 10:00', 'Thursday 2:00', 'Friday 4:00']}
        }
        self.student_course_map = {
            'S1': ['C1', 'C2'],
            'S2': ['C1', 'C3']
        }
        self.course_professor_map = {
            'C1': 'Prof1',
            'C2': 'Prof1',  # Same professor as C1
            'C3': 'Prof2'
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

if __name__ == '__main__':
    unittest.main()