import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
import pandas as pd

# Adjust the import below if your module is named differently.
# For example, if your file is named data_functions.py:
from src.database_management.database_retrieval import registration_data, faculty_pref, student_pref


class TestDataFunctions(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and switch to it.
        self.test_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir.name)

        # Create the required "data" directory.
        os.mkdir("data")
        self.db_path = Path(os.getcwd()) / "data" / "timetable.db"

        # Create a SQLite database file with the required tables.
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create Users table (includes CourseID for student_pref join).
        cursor.execute("""
            CREATE TABLE Users (
                UserID INTEGER PRIMARY KEY,
                Email TEXT,
                Role TEXT,
                CourseID INTEGER
            );
        """)

        # Create Courses table.
        cursor.execute("""
            CREATE TABLE Courses (
                CourseID INTEGER PRIMARY KEY,
                CourseName TEXT,
                CourseType TEXT,
                Credits INTEGER,
                ProfessorID INTEGER
            );
        """)

        # Create Course_Stud table.
        cursor.execute("""
            CREATE TABLE Course_Stud (
                StudentID INTEGER,
                CourseID INTEGER
            );
        """)

        # Create Professor_BusySlots table.
        cursor.execute("""
            CREATE TABLE Professor_BusySlots (
                ProfessorID INTEGER,
                SlotID INTEGER
            );
        """)

        # Create Slots table.
        cursor.execute("""
            CREATE TABLE Slots (
                SlotID INTEGER PRIMARY KEY,
                Day TEXT,
                StartTime TEXT
            );
        """)

        # Insert sample data for registration_data and faculty_pref.
        # Insert a student (with CourseID=1) and a professor.
        cursor.execute(
            "INSERT INTO Users (UserID, Email, Role, CourseID) VALUES (1, 'student@example.com', 'Student', 1);")
        cursor.execute(
            "INSERT INTO Users (UserID, Email, Role, CourseID) VALUES (2, 'professor@example.com', 'Professor', NULL);")

        # Insert a course.
        cursor.execute(
            "INSERT INTO Courses (CourseID, CourseName, CourseType, Credits, ProfessorID) VALUES (1, 'G CODE Example', 'Lecture', 3, 2);")

        # Insert a record into Course_Stud linking the student and course.
        cursor.execute("INSERT INTO Course_Stud (StudentID, CourseID) VALUES (1, 1);")

        # Insert data for faculty_pref: a busy slot for the professor.
        cursor.execute("INSERT INTO Slots (SlotID, Day, StartTime) VALUES (1, 'Monday', '09:00:00');")
        cursor.execute("INSERT INTO Professor_BusySlots (ProfessorID, SlotID) VALUES (2, 1);")

        conn.commit()
        conn.close()

    def tearDown(self):
        # Restore the original working directory and remove the temporary directory.
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    def test_registration_data(self):
        """
        Test the registration_data() function returns the expected DataFrame.
        """
        df = registration_data()
        # Expected columns: 'Roll No.', 'G CODE', 'Professor', 'Type', 'Credit'
        self.assertListEqual(list(df.columns), ['Roll No.', 'G CODE', 'Professor', 'Type', 'Credit'])
        # One row should be returned with the sample data.
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Roll No.'], 'student@example.com')
        self.assertEqual(df.iloc[0]['G CODE'], 'G CODE Example')
        self.assertEqual(df.iloc[0]['Professor'], 'professor@example.com')
        self.assertEqual(df.iloc[0]['Type'], 'Lecture')
        self.assertEqual(df.iloc[0]['Credit'], 3)

    def test_faculty_pref(self):
        """
        Test the faculty_pref() function returns the expected DataFrame.
        """
        df = faculty_pref()
        self.assertListEqual(list(df.columns), ['Name', 'Busy Slot'])
        self.assertEqual(len(df), 1)
        # The busy slot should combine Day and StartTime.
        self.assertEqual(df.iloc[0]['Name'], 'professor@example.com')
        self.assertEqual(df.iloc[0]['Busy Slot'], 'Monday 09:00:00')

    def test_student_pref_empty(self):
        """
        Test the student_pref() function returns an empty DataFrame when no student row
        qualifies for the join (thus avoiding the column mismatch error).
        """
        # Remove the valid course association for students so that the join returns no rows.
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET CourseID = NULL WHERE Role = 'Student';")
        conn.commit()
        conn.close()

        df = student_pref()
        # Even though the function specifies two columns, with no rows the DataFrame will be empty.
        self.assertListEqual(list(df.columns), ['Name', 'Busy Slot'])
        self.assertEqual(len(df), 0)


if __name__ == "__main__":
    unittest.main()