import mariadb
from dotenv import load_dotenv
import os

load_dotenv()
mydb_dict = {'host': os.getenv("DATABASE_HOST"),
             'user': os.getenv("DATABASE_USER"),
             'password': os.getenv("DATABASE_PASSWORD"),
             'database': os.getenv("DATABASE_REF"),
             'port': os.getenv("DATABASE_PORT")}

mydb = mariadb.connect(
    host=mydb_dict["host"],
    port=int(mydb_dict["port"]),
    user=mydb_dict["user"],
    password=mydb_dict["password"],
    database=mydb_dict["database"]  # Added database parameter
)

cursor = mydb.cursor()


# Create the Users table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INT AUTO_INCREMENT PRIMARY KEY,
        Email VARCHAR(255) UNIQUE NOT NULL,
        Role VARCHAR(50)
    );
""")

# Create the Courses table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Courses (
        CourseID INT AUTO_INCREMENT PRIMARY KEY,
        CourseName VARCHAR(255) UNIQUE NOT NULL,
        ProfessorID INT,
        CourseType VARCHAR(20),
        FOREIGN KEY (ProfessorID) REFERENCES Users(UserID)
    );
""")

# Create the Course_Stud table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Course_Stud (
        CourseID INT,
        StudentID INT,
        FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
        FOREIGN KEY (StudentID) REFERENCES Users(UserID),
        PRIMARY KEY (CourseID, StudentID)
    );
""")

# Create the Slots table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Slots (
        SlotID INT AUTO_INCREMENT PRIMARY KEY,
        StartTime VARCHAR(10) NOT NULL,
        EndTime VARCHAR(10) NOT NULL,
        Day VARCHAR(50) NOT NULL,
        UNIQUE (StartTime, EndTime, Day)
    );
""")

# Create the Professor_BusySlots table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Professor_BusySlots (
        ProfessorID INT,
        SlotID INT,
        FOREIGN KEY (ProfessorID) REFERENCES Users(UserID),
        FOREIGN KEY (SlotID) REFERENCES Slots(SlotID),
        PRIMARY KEY (ProfessorID, SlotID)
    );
""")

# Create the Schedule table
cursor.execute("""CREATE TABLE IF NOT EXISTS Schedule (
    CourseID INT,
    SlotID INT,
    FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
    FOREIGN KEY (SlotID) REFERENCES Slots(SlotID),
    PRIMARY KEY (CourseID, SlotID)
    );
""")

cursor.close()
mydb.close()
