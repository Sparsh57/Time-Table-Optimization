import pandas as pd
from .databse_connection import DatabaseConnection


def insert_user_data(list_files, db_path):
    print("Inserting user data")
    """
    Inserts user data (professors and students) into the SQLite database.

    :param list_files: A tuple containing two DataFrames:
                       - course_data: DataFrame with faculty information.
                       - stud_course_data: DataFrame with student registration data.
    """
    db = DatabaseConnection.get_connection(db_path)
    course_data, stud_course_data = list_files

    # Process professor data
    filtered_prof_column = course_data['Faculty Name'].dropna().drop_duplicates()  # Remove nulls and duplicates
    filtered_prof_column = pd.DataFrame(filtered_prof_column, columns=['Faculty Name'])
    filtered_prof_column["Role"] = "Professor"  # Add role
    filtered_prof_column.rename(columns={'Faculty Name': 'Email'}, inplace=True)  # Rename to 'Email'

    # Process student data
    filtered_stud_column = stud_course_data['Roll No.'].dropna().drop_duplicates()  # Remove nulls and duplicates
    filtered_stud_column = pd.DataFrame(filtered_stud_column, columns=['Roll No.'])
    filtered_stud_column["Role"] = "Student"  # Add role
    filtered_stud_column.rename(columns={'Roll No.': 'Email'}, inplace=True)  # Rename to 'Email'

    # Combine professor and student data
    final_data = pd.concat([filtered_prof_column, filtered_stud_column])
    final_data.reset_index(drop=True, inplace=True)  # Reset index to make it sequential
    final_data['UserID'] = final_data.index + 1  # Assign UserID

    # Insert data into the Users table
    for index, row in final_data.iterrows():
        insert_query = "INSERT INTO Users (Name, Email, Role) VALUES (?, ?, ?)"
        db.execute_query(insert_query, (row['UserID'], row['Email'], row['Role']))

    db.close()


def fetch_user_data(db_path):
    """
    Fetches user data of professors from the SQLite database.

    :return: List of tuples containing user data.
    """
    db = DatabaseConnection.get_connection(db_path)
    try:
        query = """
        SELECT * FROM Users
        WHERE Role = 'Professor';
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()


def add_admin(user_name: str, email:str, db_path: str, role: str):
    """
    Adds an admin to the organization's database using the DatabaseConnection.
    Expects the user name, the database path, and the role (e.g., "Admin").

    Note: Since the Users table requires an Email field, we generate a dummy email
    from the user name.
    """

    # Connect to the given database using DatabaseConnection
    db_conn = DatabaseConnection(db_path)
    connection = db_conn.connect()
    if not connection:
        print("Failed to connect to the organization's database.")
        return

    # Create the Users table if it doesn't exist
    create_users_table_query = """
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Email TEXT UNIQUE NOT NULL,
            Name TEXT NOT NULL,
            Role TEXT CHECK (Role IN ('Admin', 'Professor', 'Student')) NOT NULL
        );
    """
    db_conn.execute_query(create_users_table_query)

    # Insert the admin record into the Users table
    insert_query = "INSERT OR IGNORE INTO Users (Name, Email, Role) VALUES (?, ?, ?)"
    db_conn.execute_query(insert_query, (user_name, email, role))
    db_conn.close()
    print(f"{role} '{user_name}' added successfully to the database at {db_path}.")