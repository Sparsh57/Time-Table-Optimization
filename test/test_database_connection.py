import sys
from pathlib import Path

current_file_path = Path(__file__)
# Get the parent's parent's path
grandparent_path = current_file_path.parent.parent

# Convert to a string and add to system path
sys.path.append(str(grandparent_path))
from src.database_management.databse_connection import DatabaseConnection  # Assuming your file is named database_connection.py
import unittest
from unittest.mock import patch, MagicMock

class TestDatabaseConnection(unittest.TestCase):

    @patch('mariadb.connect')
    def test_mariadb_connection_success(self, mock_connect):
        # Mock the connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['10.5.12-MariaDB']

        db = DatabaseConnection(host="localhost", user="user", password="pass", database="test_db", port=3306)
        db.connect()

        # Assert the connection and query execution
        mock_connect.assert_called_once_with(
            host="localhost", port=3306, user="user", password="pass", database="test_db"
        )
        mock_cursor.execute.assert_any_call("SELECT VERSION();")


    @patch('mariadb.connect')
    def test_execute_query_success(self, mock_connect):
        # Mock the connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        db = DatabaseConnection(host="localhost", user="user", password="pass", database="test_db", port=3306)
        db.connect()

        query = "CREATE TABLE test (id INT PRIMARY KEY)"
        db.execute_query(query)

        # Assert the correct query execution
        mock_cursor.execute.assert_any_call(query)

    @patch('mariadb.connect')
    def test_fetch_query_success(self, mock_connect):
        # Mock the connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('result1',), ('result2',)]

        db = DatabaseConnection(host="localhost", user="user", password="pass", database="test_db", port=3306)
        db.connect()

        query = "SELECT * FROM test"
        results = db.fetch_query(query)

        # Assert the correct query execution and fetched results
        mock_cursor.execute.assert_any_call(query)
        self.assertEqual(results, [('result1',), ('result2',)])

    @patch('mariadb.connect')
    def test_close_connection(self, mock_connect):
        # Mock connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Instantiate DatabaseConnection and connect
        db = DatabaseConnection(host="localhost", user="user", password="pass", database="test_db", port=3306)
        db.connect()

        # Close the connection
        db.close()

        # Assert that cursor and connection were closed
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()
