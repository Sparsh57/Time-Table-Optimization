import pandas as pd
from .databse_connection import DatabaseConnection


def insert_user_data(list_files):
    print("Inserting user data")
    """
    Inserts user data (professors and students) into the SQLite database.

    :param list_files: A tuple containing two DataFrames:
                       - course_data: DataFrame with faculty information.
                       - stud_course_data: DataFrame with student registration data.
    """
    db = DatabaseConnection.get_connection()
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
        insert_query = "INSERT INTO Users (UserID, Email, Role) VALUES (?, ?, ?)"
        db.execute_query(insert_query, (row['UserID'], row['Email'], row['Role']))

    db.close()


def fetch_user_data():
    """
    Fetches user data of professors from the SQLite database.

    :return: List of tuples containing user data.
    """
    db = DatabaseConnection.get_connection()
    try:
        query = """
        SELECT * FROM Users
        WHERE Role = 'Professor';
        """
        result = db.fetch_query(query)
        return result
    finally:
        db.close()