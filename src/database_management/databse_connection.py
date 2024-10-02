import mariadb
import mysql.connector
from mariadb import Error as MariadbError
from mysql.connector import Error as MySQLError
import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseConnection:
    def __init__(self, host, user, password, database, port):
        """
        Initializes the database connection class with necessary database parameters.

        Args:
        host (str): The server address of the database (MariaDB or MySQL).
        user (str): Username used to authenticate with the database.
        password (str): Password used to authenticate with the database.
        database (str): The name of the database to connect to.
        port (int): The port number for the database connection.
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = int(port)
        self.connection = None

    def connect(self):
        """
        Establishes a connection to the MariaDB database. If it fails, it falls back to a MySQL database connection.

        Returns:
        connection: The established database connection.
        """
        try:
            self.connection = mariadb.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.is_connected():
                cursor = self.connection.cursor()
                cursor.execute("SELECT VERSION();")
                db_info = cursor.fetchone()
                print(f"Successfully connected to MariaDB Server version: {db_info[0]}")
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                print("You're connected to MariaDB database: ", record)
                return self.connection
        except MariadbError as e:
            print("Error while connecting to MariaDB:", e)
            print("Attempting to connect to MySQL database as a backup...")
            return self.connect_to_mysql()

    def connect_to_mysql(self):
        """
        Attempts to connect to a MySQL database as a backup.

        Returns:
        connection: The established MySQL database connection or None if it fails.
        """
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DATABASE")
            )
            if self.is_connected():
                cursor = self.connection.cursor()
                cursor.execute("SELECT VERSION();")
                db_info = cursor.fetchone()
                print(f"Successfully connected to MySQL Server version: {db_info[0]}")
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                print("You're connected to MySQL database: ", record)
                return self.connection
        except MySQLError as e:
            print("Error while connecting to MySQL:", e)
            raise e

    def is_connected(self):
        try:
            self.connection.ping(reconnect=True)
        except Exception as e:
            raise e
        return True

    def execute_query(self, query, params=None):
        """
        Executes a SQL query on the connected database.

        Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the SQL query.
        """
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            print("Query executed successfully")
        except (MariadbError, MySQLError) as e:
            print(f"Failed to execute query: {e}")
            self.connection.rollback()
            raise e

    def fetch_query(self, query, params=None):
        """
        Fetches and returns results from a SQL query.

        Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters for the SQL query.

        Returns:
        list: A list of tuples representing the fetched rows.
        """
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            return results
        except (MariadbError, MySQLError) as e:
            print(f"Failed to fetch data: {e}")
            raise e

    def close(self):
        """
        Closes the database connection if it is open.
        """
        if self.connection and self.is_connected():
            self.connection.close()
            print("Database connection is closed")

    @staticmethod
    def get_connection():
        """
        Retrieves the database connection using environment variables.

        Returns:
        db: An instance of DatabaseConnection.
        """
        mydb_dict = {
            'host': os.getenv("DATABASE_HOST"),
            'user': os.getenv("DATABASE_USER"),
            'password': os.getenv("DATABASE_PASSWORD"),
            'database': os.getenv("DATABASE_REF"),
            'port': os.getenv("DATABASE_PORT")
        }

        db = DatabaseConnection(
            host=mydb_dict["host"],
            port=int(mydb_dict["port"]),
            user=mydb_dict["user"],
            password=mydb_dict["password"],
            database=mydb_dict["database"]
        )
        db.connect()
        return db
