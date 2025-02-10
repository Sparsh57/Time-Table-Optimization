import unittest
import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))

from src.data_preprocessing import merge_data, prepare_student_course_map, create_course_professor_map

class TestCourseManagement(unittest.TestCase):

    def test_merge_data(self):
        # Sample data for registration and courses
        data_registration = {
            'Roll No.': [1, 2, 3],
            'G CODE': ['CS101', 'CS102', 'CS103']
        }
        data_courses = {
            'Course code': ['CS101', 'CS102', 'CS103'],
            'Faculty Name': ['Prof. A', 'Prof. B', 'Prof. C']
        }

        df_registration = pd.DataFrame(data_registration)
        df_courses = pd.DataFrame(data_courses)

        # Expected merged DataFrame
        expected_data = {
            'Roll No.': [1, 2, 3],
            'G CODE': ['CS101', 'CS102', 'CS103'],
            'Professor': ['Prof. A', 'Prof. B', 'Prof. C']
        }
        expected_df = pd.DataFrame(expected_data)

        # Call the merge_data function
        result_df = merge_data(df_registration, df_courses)

        # Assert that the merged DataFrame matches the expected result
        pd.testing.assert_frame_equal(result_df, expected_df)

    def test_prepare_student_course_map(self):
        # Sample merged DataFrame
        data_merged = {
            'Roll No.': [1, 1, 2, 2, 3],
            'G CODE': ['CS101', 'CS102', 'CS101', 'CS103', 'CS102'],
            'Professor': ['Prof. A', 'Prof. B', 'Prof. A', 'Prof. C', 'Prof. B']
        }
        df_merged = pd.DataFrame(data_merged)

        # Expected student course map
        expected_output = {
            1: ['CS101', 'CS102'],
            2: ['CS101', 'CS103'],
            3: ['CS102']
        }

        # Call the prepare_student_course_map function
        result = prepare_student_course_map(df_merged)

        # Assert that the result matches the expected student course map
        self.assertEqual(result, expected_output)

    def test_create_course_professor_map(self):
        # Sample merged DataFrame
        data_merged = {
            'Roll No.': [1, 1, 2, 2, 3],
            'G CODE': ['CS101', 'CS102', 'CS101', 'CS103', 'CS102'],
            'Professor': ['Prof. A', 'Prof. B', 'Prof. A', 'Prof. C', 'Prof. B']
        }
        df_merged = pd.DataFrame(data_merged)

        # Expected course professor map
        expected_output = {
            'CS101': 'Prof. A',
            'CS102': 'Prof. B',
            'CS103': 'Prof. C'
        }

        # Call the create_course_professor_map function
        result = create_course_professor_map(df_merged)

        # Assert that the result matches the expected course professor map
        self.assertEqual(result, expected_output)


if __name__ == '__main__':
    unittest.main()