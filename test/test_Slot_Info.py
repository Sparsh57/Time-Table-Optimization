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
from src.database_management.Slot_info import insert_time_slots

class SlotConnect(unittest.TestCase):
    @patch('mariadb.connect')
    def test_insert_time_slots(self, mock_connect):
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
        insert_time = {
                  "days": ["Monday", "Tuesday"],
                  "times": [
                    ["08:30", "10:30"],
                    ["10:30", "12:30"],
                    ["12:30", "14:30"]]
        }
        insert_time_slots(db_config, insert_time)
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)", ('08:30', '10:30', 'Monday'))
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)", ("10:30", "12:30","Monday"))
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)", ("12:30", "14:30", "Monday"))
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)", ("08:30", "10:30", "Tuesday"))
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)", ("10:30", "12:30", "Tuesday"))
        mock_cursor.execute.assert_any_call("INSERT INTO Slots (StartTime, EndTime, Day) VALUES (%s, %s, %s)",("12:30", "14:30", "Tuesday"))