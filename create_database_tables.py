import mysql.connector

mydb = mysql.connector.connect(
    host="byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
    user="urao5yk0erbiklfr",
    password="tpgCmLhZdwPk8iAxzVMd",
    database="byfapocx02at8jbunymk"
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

cursor.close()
mydb.close()
