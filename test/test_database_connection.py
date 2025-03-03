import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Import the DatabaseConnection class.
# Adjust the import if your class is in a different module.
from src.database_management.databse_connection import DatabaseConnection


class TestDatabaseConnection(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and set it as the current working directory.
        self.test_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir.name)

        # Create the "data" directory to match the expected db_path structure.
        os.mkdir("data")

        # Use a test database file in the temporary directory.
        self.db_path = "data/test_timetable.db"
        self.db = DatabaseConnection(db_path=self.db_path)
        self.db.connect()

    def tearDown(self):
        # Close the database connection and revert the working directory.
        self.db.close()
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    def test_connection(self):
        """Test that the database connection is active."""
        self.assertTrue(self.db.is_connected(), "The database connection should be active.")

    def test_execute_query_and_fetch(self):
        """Test executing a query and then fetching data."""
        # Create a simple table.
        create_table_query = """
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL
        );
        """
        self.db.execute_query(create_table_query)

        # Insert a record into the table.
        insert_query = "INSERT INTO timetable (subject) VALUES (?);"
        self.db.execute_query(insert_query, params=("Mathematics",))

        # Fetch the inserted record.
        select_query = "SELECT subject FROM timetable;"
        results = self.db.fetch_query(select_query)

        self.assertIsNotNone(results, "The fetch query should return results.")
        self.assertEqual(len(results), 1, "There should be exactly one record in the table.")
        self.assertEqual(results[0][0], "Mathematics", "The subject should be 'Mathematics'.")

    def test_close_connection(self):
        """Test that the connection is properly closed."""
        self.db.close()
        self.assertFalse(self.db.is_connected(), "The database connection should be closed.")


if __name__ == "__main__":
    unittest.main()