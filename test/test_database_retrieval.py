import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

import pandas as pd

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))

from src.database_management.database_retrieval import registration_data, faculty_pref

class TestDatabaseFunctions(unittest.TestCase):

    @patch(
        'src.database_management.databse_connection.DatabaseConnection.connect')  # Mock the connect method of DatabaseConnection
    @patch(
        'src.database_management.databse_connection.DatabaseConnection.fetch_query')  # Mock the fetch_query method of DatabaseConnection
    def test_registration_data(self, mock_fetch_query, mock_connect):
        # Mock the return value of the connect method to return the same connection object
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        # Sample test data to mock the SQL query result
        sample_data = [
            ('student1@example.com', 'CS101', 'prof1@example.com'),
            ('student2@example.com', 'MA102', 'prof2@example.com')
        ]

        # Mock the return value of the fetch_query method
        mock_fetch_query.return_value = sample_data

        # Ensure fetch_query is being called on the correct connection object
        mock_connection.fetch_query = mock_fetch_query

        # Database config
        db_config = {
            "host": "localhost",
            "user": "test_user",
            "port": 3306,
            "password": "test_password",
            "database": "test_database"
        }

        # Call the registration_data function
        df = registration_data(db_config)

        # Create the expected DataFrame
        expected_df = pd.DataFrame(sample_data, columns=['Roll No.', 'G CODE', 'Professor'])

        # Assert the result matches the expected DataFrame
        pd.testing.assert_frame_equal(df, expected_df)

        # Ensure fetch_query is called once
        mock_fetch_query.assert_called_once()

    @patch(
        'src.database_management.databse_connection.DatabaseConnection.connect')  # Mock the connect method of DatabaseConnection
    @patch(
        'src.database_management.databse_connection.DatabaseConnection.fetch_query')  # Mock the fetch_query method of DatabaseConnection
    def test_faculty_pref(self, mock_fetch_query, mock_connect):
        # Sample test data to mock the SQL query result
        sample_data = [
            ('prof1@example.com', 'Monday 10:00'),
            ('prof1@example.com', 'Tuesday 11:00'),
            ('prof2@example.com', 'Wednesday 14:00')
        ]

        # Mock the return value of the fetch_query method
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.fetch_query.return_value = sample_data

        # Database config
        db_config = {
            "host": "localhost",
            "user": "test_user",
            "port": 3306,
            "password": "test_password",
            "database": "test_database"
        }

        # Call the faculty_pref function
        df = faculty_pref(db_config)
        # Create the expected DataFrame
        expected_df = pd.DataFrame(sample_data, columns=['Name', 'Busy Slot'])

        # Assert the result matches the expected DataFrame
        pd.testing.assert_frame_equal(df, expected_df)


if __name__ == '__main__':
    unittest.main()
