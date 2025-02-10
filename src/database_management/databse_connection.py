import sqlite3
import os
from pathlib import Path



class DatabaseConnection:
    def __init__(self, db_path="data/timetable.db"):
        """
        Initializes the SQLite database connection class.

        Args:
        db_path (str): The file path to the SQLite database.
        """
        self.db_path = Path(os.getcwd()) / db_path
        print(self.db_path)
        self.connection = None

    def connect(self):
        try:
            print(self.db_path)
            self.connection = sqlite3.connect(self.db_path)
            print(f"Connected to SQLite database at: {self.db_path}")
            return self.connection
        except sqlite3.Error as e:
            print(f"Error connecting to SQLite database: {e}")
            return None
    def is_connected(self):
        """
        Checks if the SQLite database connection is active.

        Returns:
        bool: True if the connection is active, False otherwise.
        """
        try:
            if self.connection:
                self.connection.execute("SELECT 1;")
                return True
        except sqlite3.Error as e:
            print(f"Connection check failed: {e}")
        return False

    def execute_query(self, query, params=None):
        """
        Executes a SQL query on the connected SQLite database.

        Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the SQL query.
        """
        if not self.is_connected():
            print("No active database connection.")
            return

        try:
            cursor = self.connection.cursor()
            print(f"Executing query: {query}")  # Log the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            print("Query executed successfully")
        except sqlite3.Error as e:
            print(f"Failed to execute query: {e}")

    def fetch_query(self, query, params=None):
        """
        Fetches and returns results from a SQL query.

        Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the SQL query.

        Returns:
        list: A list of tuples representing the fetched rows or None if an error occurs.
        """
        if not self.is_connected():
            print("No active database connection.")
            return None

        try:
            cursor = self.connection.cursor()
            print(f"Fetching data with query: {query}")  # Log the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            print(results)
            return results
        except sqlite3.Error as e:
            print(f"Failed to fetch data: {e}")
            return None

    def close(self):
        """
        Closes the SQLite database connection if it is open.
        """
        if self.connection:
            try:
                self.connection.close()
                print("SQLite database connection closed.")
            except sqlite3.Error as e:
                print(f"Failed to close connection: {e}")

    @staticmethod
    def get_connection():
        """
        Retrieves the SQLite database connection using an environment variable.

        Returns:
        db: An instance of DatabaseConnection.
        """
        db_path = Path(os.getcwd()) / "data/timetable.db"
        db = DatabaseConnection(db_path)
        db.connect()
        return db
