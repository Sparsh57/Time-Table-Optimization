import pandas as pd
from database_management.databse_connection import DatabaseConnection

def registration_data():
    db = DatabaseConnection(
        host="byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
        user="urao5yk0erbiklfr",
        password="tpgCmLhZdwPk8iAxzVMd",
        database="byfapocx02at8jbunymk"
    )
    connection = db.connect()

    query = """
    SELECT 
        u.Email AS 'Roll No.', 
        c.CourseName AS 'G CODE', 
        p.Email AS 'Professor'
    FROM Course_Stud cs
    JOIN Users u ON cs.StudentID = u.UserID
    JOIN Courses c ON cs.CourseID = c.CourseID
    JOIN Users p ON c.ProfessorID = p.UserID
    LEFT JOIN Professor_BusySlots ps ON p.UserID = ps.ProfessorID
    GROUP BY u.Email, c.CourseName, p.Email;
    """
    df = pd.read_sql_query(query, connection)
    db.close()

    return df

def faculty_pref():
    db = DatabaseConnection(
        host="byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
        user="urao5yk0erbiklfr",
        password="tpgCmLhZdwPk8iAxzVMd",
        database="byfapocx02at8jbunymk"
    )
    connection = db.connect()

    query = """
    SELECT 
        u.Email AS 'Name', 
        CONCAT(s.Day, ' ', TIME_FORMAT(s.StartTime, '%H:%i')) AS 'Busy Slot'
    FROM Users u
    JOIN Professor_BusySlots ps ON u.UserID = ps.ProfessorID
    JOIN Slots s ON ps.SlotID = s.SlotID
    WHERE u.Role = 'Professor'
    ORDER BY u.Email, s.Day, s.StartTime;
    """
    df = pd.read_sql_query(query, connection)
    db.close()

    return df

df_registration = registration_data()
df_professor_pref = faculty_pref()

directory_path = 'data/' 

# Save dataframes to CSV
df_registration.to_csv(directory_path + 'Student_Registration.csv', index=False)
df_professor_pref.to_csv(directory_path + 'Faculty_Pref.csv', index=False)
