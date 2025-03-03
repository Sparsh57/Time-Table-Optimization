from .databse_connection import DatabaseConnection
from dotenv import load_dotenv

load_dotenv()


def truncate_detail(db_path):
    """
    Deletes all data from the tables in the SQLite database while handling foreign key constraints.
    """
    db = DatabaseConnection.get_connection(db_path)

    # Queries to disable foreign key checks, delete data, and re-enable foreign key checks
    queries = [
        "PRAGMA foreign_keys = OFF;",  # Disable foreign key checks
        "DELETE FROM Courses;",
        "DELETE FROM Course_Stud;",
        "DELETE FROM Professor_BusySlots;",
        "DELETE FROM Schedule;",
        "DELETE FROM Users WHERE Role != 'Admin';",
        "PRAGMA foreign_keys = ON;"  # Re-enable foreign key checks
    ]

    try:
        for query in queries:
            db.execute_query(query)  # Execute each query
        print("Tables truncated successfully.")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        db.close()

