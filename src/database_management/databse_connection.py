import mysql.connector
from mysql.connector import Error

class DatabaseConnection:
    def __init__(self, host, user, password, database):
        """
        Initializes the database connection class with necessary database parameters.
        
        Args:
        host (str): The server address of the MySQL database.
        user (str): Username used to authenticate with MySQL.
        password (str): Password used to authenticate with MySQL.
        database (str): The name of the database to connect to.
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None  # Initially there is no connection

    def connect(self):
        """
        Establishes a connection to the MySQL database using the initialization parameters.
        If connected, it prints the MySQL server version and the current connected database.
        Returns:
        connection: The established database connection.
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                print(f"Successfully connected to MySQL Server version {db_info}")
                cursor = self.connection.cursor()
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                print("You're connected to database: ", record)
                return self.connection  # Return the connection object
        except Error as e:
            print("Error while connecting to MySQL", e)
            return None

    def execute_query(self, query, params=None):
        """
        Executes a SQL query on the connected database. It can handle queries with or without parameters.

        Args:
        query (str): The SQL query to execute.
        params (tuple, optional): The parameters to substitute into the SQL query.
        """
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

    def fetch_query(self, query, params=None):
        """
        Fetches and returns results from a SQL query. This method is used for queries that retrieve data.

        Args:
        query (str): The SQL query to execute for fetching data.
        params (tuple, optional): The parameters to substitute into the SQL query.

        Returns:
        list: A list of tuples representing the fetched rows.
        """
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()  # Fetch all results
            return results
        except Error as e:
            print(f"Failed to fetch data: {e}")
            return None

    def close(self):
        """
        Closes the database connection if it is open.
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")
