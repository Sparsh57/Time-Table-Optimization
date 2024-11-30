import os
import sqlite3
from dotenv import load_dotenv
load_dotenv()
# Connect to the SQLite database (creates the file if it doesn't exist)
db_path = os.path.join(os.getcwd(),os.getenv("SQLITE_DB_PATH"))
mydb = sqlite3.connect(db_path)
cursor = mydb.cursor()

# Create the Users table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
        Email TEXT UNIQUE NOT NULL,
        Role TEXT
    );
""")

# Create the Courses table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Courses (
        CourseID INTEGER PRIMARY KEY AUTOINCREMENT,
        CourseName TEXT UNIQUE NOT NULL,
        ProfessorID INTEGER,
        CourseType TEXT,
        Credits INTEGER,
        FOREIGN KEY (ProfessorID) REFERENCES Users(UserID)
    );
""")

# Create the Course_Stud table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Course_Stud (
        CourseID INTEGER,
        StudentID INTEGER,
        PRIMARY KEY (CourseID, StudentID),
        FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
        FOREIGN KEY (StudentID) REFERENCES Users(UserID)
    );
""")

# Create the Slots table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Slots (
        SlotID INTEGER PRIMARY KEY AUTOINCREMENT,
        StartTime TEXT NOT NULL,
        EndTime TEXT NOT NULL,
        Day TEXT NOT NULL,
        UNIQUE (StartTime, EndTime, Day)
    );
""")

# Create the Professor_BusySlots table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Professor_BusySlots (
        ProfessorID INTEGER,
        SlotID INTEGER,
        PRIMARY KEY (ProfessorID, SlotID),
        FOREIGN KEY (ProfessorID) REFERENCES Users(UserID),
        FOREIGN KEY (SlotID) REFERENCES Slots(SlotID)
    );
""")

# Create the Schedule table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Schedule (
        CourseID INTEGER,
        SlotID INTEGER,
        PRIMARY KEY (CourseID, SlotID),
        FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
        FOREIGN KEY (SlotID) REFERENCES Slots(SlotID)
    );
""")

# Close the connection
cursor.close()
mydb.commit()
mydb.close()

print(f"Database and tables created successfully in {db_path}.")