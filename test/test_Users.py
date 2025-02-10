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
from src.database_management.Users import insert_user_data

class UserConnection(unittest.TestCase):
    @patch('mariadb.connect')
    def test_insert_user_data(self, mock_connect):
        # Create a mock database connection
        mock_connection = MagicMock()

        # Create a mock cursor object
        mock_cursor = MagicMock()

        # Set the return value for the connect function to be the mock connection
        mock_connect.return_value = mock_connection

        # Set the return value for the cursor method to be the mock cursor
        mock_connection.cursor.return_value = mock_cursor

        # Create a test database configuration
        db_config = {
            "host": "localhost",
            "user": "test_user",
            "port": 3306,
            "password": "test_password",
            "database": "test_database"
        }

        # Call the insert_user_data function with your test data and database config
        faculty_data_dict = {
            "Faculty Name": ["A", "B", "C", "A"],
        }
        student_data_dict = {
            'Roll No.': ["1", "2"]
        }
        faculty_data = pd.DataFrame(faculty_data_dict, columns=['Faculty Name'])
        student_data = pd.DataFrame(student_data_dict, columns=['Roll No.'])
        list_files = [faculty_data, student_data]
        insert_user_data(list_files, db_config)
        mock_cursor.execute.assert_any_call("INSERT INTO Users (UserID, Email, Role) VALUES (%s, %s, %s)", (1, "A","Professor"))
        mock_cursor.execute.assert_any_call("INSERT INTO Users (UserID, Email, Role) VALUES (%s, %s, %s)", (2, "B","Professor"))
        mock_cursor.execute.assert_any_call("INSERT INTO Users (UserID, Email, Role) VALUES (%s, %s, %s)", (3, "C","Professor"))
        mock_cursor.execute.assert_any_call("INSERT INTO Users (UserID, Email, Role) VALUES (%s, %s, %s)", (4, "1","Student"))
        mock_cursor.execute.assert_any_call("INSERT INTO Users (UserID, Email, Role) VALUES (%s, %s, %s)", (5, "2","Student"))