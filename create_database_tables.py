import mysql.connector

mydb = mysql.connector.connect(
    host="byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
    user="urao5yk0erbiklfr",
    password="tpgCmLhZdwPk8iAxzVMd",
    database="byfapocx02at8jbunymk"
)

cursor = mydb.cursor()

cursor.execute("""CREATE TABLE Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
)""")

cursor.execute("""CREATE TABLE Instructors (
    instructor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
)""")

cursor.execute("""CREATE TABLE Courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(10) NOT NULL,
    instructor_id INT,
    FOREIGN KEY (instructor_id) REFERENCES Instructors(instructor_id)
)""")

cursor.execute("""CREATE TABLE TimeSlots (
    time_slot_id INT AUTO_INCREMENT PRIMARY KEY,
    day VARCHAR(10) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
)""")

cursor.execute("""
    CREATE TABLE Enrollments (
        student_id INT,
        course_id INT,
        FOREIGN KEY (student_id) REFERENCES Students(student_id),
        FOREIGN KEY (course_id) REFERENCES Courses(course_id),
        PRIMARY KEY (student_id, course_id))
    """)

cursor.execute("""
    CREATE TABLE InstructorPreferences (
        instructor_id INT,
        preferred_time_slot_id INT,
        FOREIGN KEY (instructor_id) REFERENCES Instructors(instructor_id),
        FOREIGN KEY (preferred_time_slot_id) REFERENCES TimeSlots(time_slot_id),
        PRIMARY KEY (instructor_id, preferred_time_slot_id))
    """)

cursor.execute("""CREATE TABLE ScheduledCourses (
    course_id INT,
    time_slot_id INT,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id),
    FOREIGN KEY (time_slot_id) REFERENCES TimeSlots(time_slot_id),
    PRIMARY KEY (course_id, time_slot_id)
)""")

cursor.close()
