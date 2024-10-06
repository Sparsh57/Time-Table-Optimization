import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))
from src.database_management.databse_connection import DatabaseConnection
# Assuming your file is named database_connection.py
import unittest
from unittest.mock import patch, MagicMock
from src.database_management.schedule import schedule, timetable_made, fetch_schedule_data, generate_csv, generate_csv_for_student, get_student_schedule

class TestScheduleFunctions(unittest.TestCase):

    @patch('src.database_management.databse_connection.DatabaseConnection.get_connection')
    def test_schedule(self, mock_get_connection):
        # Setup the mock database connection and query return values
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        # Mock the fetch_query for course and time slots
        mock_connection.fetch_query.side_effect = [
            [('CS101', 1), ('DS102', 2)],  # Return for course ids
            [('Monday 09:00', 1), ('Tuesday 10:00', 2)]  # Return for slot ids
        ]

        # Create a sample DataFrame for the schedule input
        schedule_df = pd.DataFrame({
            'Course ID': ['CS101', 'DS102'],
            'Scheduled Time': ['Monday 09:00', 'Tuesday 10:00']
        })

        # Call the function
        schedule(schedule_df)

        # Assert that the correct queries were executed
        mock_connection.execute_query.assert_any_call(
            "INSERT INTO Schedule (CourseID, SlotID) VALUES (%s, %s)", (1, 1)
        )
        mock_connection.execute_query.assert_any_call(
            "INSERT INTO Schedule (CourseID, SlotID) VALUES (%s, %s)", (2, 2)
        )

        # Ensure the connection was closed
        mock_connection.close.assert_called_once()

    @patch('src.database_management.databse_connection.DatabaseConnection.get_connection')
    def test_timetable_made(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        # Mock the fetch_query return value
        mock_connection.fetch_query.return_value = [(1,)]

        # Call the function
        result = timetable_made()

        # Assert that the query was executed and the result was True
        mock_connection.fetch_query.assert_called_once_with("SELECT COUNT(*) FROM Schedule")
        self.assertTrue(result)

        # Ensure the connection was closed
        mock_connection.close.assert_called_once()

    @patch('src.database_management.databse_connection.DatabaseConnection.get_connection')
    def test_fetch_schedule_data(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_get_connection.return_value = mock_connection

        # Mock the fetch_query return value
        mock_connection.fetch_query.return_value = [
            ('Monday', '09:00', '10:00', 'CS101, DS102')
        ]

        # Call the function
        result = fetch_schedule_data()

        # Assert that the query was executed and the result matches the mock
        mock_connection.fetch_query.assert_called_once()
        self.assertEqual(result, [('Monday', '09:00', '10:00', 'CS101, DS102')])

        # Ensure the connection was closed
        mock_connection.close.assert_called_once()




if __name__ == '__main__':
    unittest.main()