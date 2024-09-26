import mariadb
from mariadb import Error


class DatabaseConnection:
    def __init__(self, host, user, password, database, port):
        """
        Initializes the database connection class with necessary database parameters.

        Args:
        host (str): The server address of the Mariadb database.
        user (str): Username used to authenticate with Mariadb.
        password (str): Password used to authenticate with Mariadb.
        database (str): The name of the database to connect to.
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = int(port)
        self.connection = None  # Initially there is no connection

    def connect(self):
        """
        Establishes a connection to the MySQL database using the initialization parameters.
        If connected, it prints the MySQL server version and the current connected database.
        Returns:
        connection: The established database connection.
        """
        try:
            self.connection =mariadb.connect(
                                host=self.host,
                                port=self.port,
                                user=self.user,
                                password=self.password,
                                database=self.database  # Added database parameter
                            )
            if self.is_connected():
                cursor = self.connection.cursor()
                cursor.execute("SELECT VERSION();")
                db_info = cursor.fetchone()
                print(f"Successfully connected to MariaDB Server version: {db_info[0]}")
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                print("You're connected to database: ", record)
                return self.connection  # Return the connection object
        except Error as e:
            print("Error while connecting to Mariadb", e)
            return None

    def is_connected(self):
        try:
            self.connection.ping()
        except:
            return False
        return True

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
        if self.connection and self.is_connected():
            self.connection.close()
            print("Mariadb connection is closed")
