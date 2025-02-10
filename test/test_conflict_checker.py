import unittest
import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))

from src.conflict_checker import check_conflicts
class TestCheckConflicts(unittest.TestCase):

    def test_no_conflicts(self):
        # Sample schedule with no conflicts
        schedule = {
            'CS101': ['Monday 08:30', 'Wednesday 10:30'],
            'CS102': ['Tuesday 10:30', 'Thursday 14:30'],
            'CS103': ['Friday 12:30', 'Wednesday 16:30']
        }
        student_course_map = {
            'Student A': ['CS101', 'CS102'],
            'Student B': ['CS103']
        }

        # Expecting no conflicts
        expected_output = {}
        result = check_conflicts(schedule, student_course_map)
        self.assertEqual(result, expected_output)

    def test_conflicts(self):
        # Sample schedule with conflicts
        schedule = {
            'CS101': ['Monday 08:30', 'Wednesday 10:30'],
            'CS102': ['Monday 08:30', 'Thursday 14:30'],  # Conflict with CS101
            'CS103': ['Tuesday 12:30', 'Wednesday 10:30']
        }
        student_course_map = {
            'Student A': ['CS101', 'CS102'],  # Conflict here
            'Student B': ['CS103']  # No conflict
        }

        # Expecting conflicts for Student A
        expected_output = {
            'Student A': ['Monday 08:30', 'Monday 08:30']  # Two courses share this time slot
        }
        result = check_conflicts(schedule, student_course_map)
        self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()