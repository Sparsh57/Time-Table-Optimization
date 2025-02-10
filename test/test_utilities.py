import unittest
import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))
from src.utilities import faculty_busy_slots, create_course_dictionary

class TestCourseManagement(unittest.TestCase):

    def test_faculty_busy_slots(self):
        # Create a sample DataFrame for faculty preferences
        data = {
            'Name': ['Prof. A', 'Prof. A', 'Prof. B', 'Prof. B', 'Prof. C'],
            'Busy Slot': ['Monday 08:30', 'Tuesday 10:30', 'Monday 12:30', 'Wednesday 14:30', 'Friday 16:30']
        }
        df_faculty_pref = pd.DataFrame(data)

        # Expected output
        expected_output = {
            'Prof. A': ['Monday 08:30', 'Tuesday 10:30'],
            'Prof. B': ['Monday 12:30', 'Wednesday 14:30'],
            'Prof. C': ['Friday 16:30']
        }

        # Call the function
        result = faculty_busy_slots(df_faculty_pref)

        # Assert that the result matches the expected output
        self.assertEqual(result, expected_output)

    def test_create_course_dictionary(self):
        # Define mock data
        student_course_map = {
            'Student1': ['CS101', 'CS102'],
            'Student2': ['CS101', 'CS103'],
            'Student3': ['CS102', 'CS103']
        }

        course_professor_map = {
            'CS101': 'Prof. A',
            'CS102': 'Prof. B',
            'CS103': 'Prof. C'
        }

        professor_busy_slots = {
            'Prof. A': ['Monday 08:30', 'Tuesday 10:30'],
            'Prof. B': ['Monday 12:30', 'Wednesday 14:30'],
            'Prof. C': ['Friday 16:30']
        }

        # Expected output (only time slots where the professor is not busy)
        expected_output = {
            'CS101': {'time_slots': ['Monday 10:30', 'Monday 12:30', 'Monday 14:30', 'Monday 16:30', 'Monday 18:30',
                                     'Tuesday 08:30', 'Tuesday 12:30', 'Tuesday 14:30', 'Tuesday 16:30', 'Tuesday 18:30',
                                     'Wednesday 08:30', 'Wednesday 10:30', 'Wednesday 12:30', 'Wednesday 14:30', 'Wednesday 16:30', 'Wednesday 18:30',
                                     'Thursday 08:30', 'Thursday 10:30', 'Thursday 12:30', 'Thursday 14:30', 'Thursday 16:30', 'Thursday 18:30',
                                     'Friday 08:30', 'Friday 10:30', 'Friday 12:30', 'Friday 14:30', 'Friday 16:30', 'Friday 18:30']},
            'CS102': {'time_slots': ['Monday 08:30', 'Monday 10:30', 'Monday 14:30', 'Monday 16:30', 'Monday 18:30',
                                     'Tuesday 08:30', 'Tuesday 10:30', 'Tuesday 12:30', 'Tuesday 14:30', 'Tuesday 16:30', 'Tuesday 18:30',
                                     'Wednesday 08:30', 'Wednesday 10:30', 'Wednesday 12:30', 'Wednesday 16:30', 'Wednesday 18:30',
                                     'Thursday 08:30', 'Thursday 10:30', 'Thursday 12:30', 'Thursday 14:30', 'Thursday 16:30', 'Thursday 18:30',
                                     'Friday 08:30', 'Friday 10:30', 'Friday 12:30', 'Friday 14:30', 'Friday 16:30', 'Friday 18:30']},
            'CS103': {'time_slots': ['Monday 08:30', 'Monday 10:30', 'Monday 12:30', 'Monday 14:30', 'Monday 16:30', 'Monday 18:30',
                                     'Tuesday 08:30', 'Tuesday 10:30', 'Tuesday 12:30', 'Tuesday 14:30', 'Tuesday 16:30', 'Tuesday 18:30',
                                     'Wednesday 08:30', 'Wednesday 10:30', 'Wednesday 12:30', 'Wednesday 14:30', 'Wednesday 16:30', 'Wednesday 18:30',
                                     'Thursday 08:30', 'Thursday 10:30', 'Thursday 12:30', 'Thursday 14:30', 'Thursday 16:30', 'Thursday 18:30',
                                     'Friday 08:30', 'Friday 10:30', 'Friday 12:30', 'Friday 14:30', 'Friday 18:30']}
        }

        # Call the function
        result = create_course_dictionary(student_course_map, course_professor_map, professor_busy_slots)

        # Assert that the result matches the expected output
        self.assertEqual(result, expected_output)


if __name__ == '__main__':
    unittest.main()
