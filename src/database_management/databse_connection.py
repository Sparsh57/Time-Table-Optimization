import mysql.connector
from mysql.connector import Error

class DatabaseConnection:
    def __init__(self, host, user, password, database):
        """Initialize database connection parameters."""
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def connect(self):
        """ Connect to MySQL database """
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if connection.is_connected():
                db_Info = connection.get_server_info()
                print(f"Successfully connected to MySQL Server version {db_Info}")
                cursor = connection.cursor()
                cursor.execute("select database();")
                record = cursor.fetchone()
                print("You're connected to database: ", record)
                return connection
        except Error as e:
            print("Error while connecting to MySQL", e)
            return None

    def execute_query(self, query, params=None):
        """Execute a given SQL query with optional parameters."""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            print("Query executed successfully")
        except Error as e:
            print(f"Failed to execute query: {e}")
            self.connection.rollback()

    def fetch_data(self, query, params=None):
        """Fetch data from the database based on a query."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params) if params else cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"Failed to fetch data: {e}")
            return None

    def close(self):
        """Close the database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")
