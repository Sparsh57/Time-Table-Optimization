import pandas as pd

from .databse_connection import DatabaseConnection


def insert_user_data(list_files, db_config):
    db = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        port=db_config["port"],
        password=db_config["password"],
        database=db_config["database"]
    )
    course_data, stud_course_data = list_files
    db.connect()
    
    try:
        filtered_prof_column = course_data['Faculty Name'].dropna()  # Remove null values
        filtered_prof_column = filtered_prof_column.drop_duplicates()  # Remove duplicates
        filtered_prof_column = pd.DataFrame(filtered_prof_column, columns=['Faculty Name'])  # Convert to DataFrame
        filtered_prof_column["Role"] = "Professor"  # Add role
        filtered_prof_column.rename(columns={'Faculty Name': 'Email'}, inplace=True)  # Rename to 'email'

        filtered_stud_column = stud_course_data['Roll No.'].dropna()  # Remove null values
        filtered_stud_column = filtered_stud_column.drop_duplicates()  # Remove duplicates
        filtered_stud_column = pd.DataFrame(filtered_stud_column, columns=['Roll No.'])  # Convert to DataFrame
        filtered_stud_column["Role"] = "Student"  # Add role
        filtered_stud_column.rename(columns={'Roll No.': 'Email'}, inplace=True)  # Rename to 'email'

        final_data = pd.concat([filtered_prof_column, filtered_stud_column])

        final_data.reset_index(drop=True, inplace=True)  # Reset index to make it sequential
        final_data['UserID'] = final_data.index + 1

        for index, row in final_data.iterrows():
            insert_query = "INSERT INTO Users (UserID, Email, Role) VALUES (?, ?, ?)"
            try:
                db.execute_query(insert_query, (row['UserID'], row['Email'], row['Role']))
            except Exception as e:
                print(f"Error inserting row {index}: {e}")
                raise e  # Re-raise the exception if insertion fails
    except Exception as e:
        print(f"An error occurred while processing user data: {e}")
        raise e  
    finally:
        db.close()


def fetch_user_data():
    db = DatabaseConnection.get_connection()
    try:
        query = """
        SELECT * from Users
        WHERE Role = 'Professor'
        """
        result = db.fetch_query(query)
        return result
    except Exception as e:
        print(f"Error fetching user data: {e}")
        raise e  
    finally:
        db.close()

print(fetch_user_data())
