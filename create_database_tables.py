import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the directory where organization databases will be stored
DATA_DIR = os.path.join(os.getcwd(), "data")

# Ensure the `data/` directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# Initialize the meta-database (stores organizations and their database paths)
def init_meta_database():
    conn = sqlite3.connect('organizations_meta.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Organizations (
                        OrgID INTEGER PRIMARY KEY AUTOINCREMENT,
                        OrgName TEXT UNIQUE NOT NULL,
                        OrgDomains TEXT NOT NULL,
                        DatabasePath TEXT NOT NULL
                      );''')
    conn.commit()
    conn.close()


# Function to get or create an organization's database in the `data/` directory
def get_or_create_org_database(org_name, org_domains):
    conn = sqlite3.connect('organizations_meta.db')
    cursor = conn.cursor()

    # Convert list of domains to a comma-separated string
    domain_str = ",".join(org_domains)

    # Check if the organization already exists
    cursor.execute("SELECT DatabasePath FROM Organizations WHERE OrgName = ?", (org_name,))
    result = cursor.fetchone()

    if result:
        db_path = result[0]
    else:
        # Generate a new database file for the organization in the `data/` subdirectory
        db_path = os.path.join(DATA_DIR, f"{org_name.replace(' ', '_')}.db")
        cursor.execute("INSERT INTO Organizations (OrgName, OrgDomains, DatabasePath) VALUES (?, ?, ?)",
                       (org_name, domain_str, db_path))
        conn.commit()

        init_org_database(db_path)

    conn.close()

    init_org_database(db_path)

    return db_path


# Function to initialize a new organization's database with required tables
def init_org_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Users table (stores professors, students, and admins)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Email TEXT UNIQUE NOT NULL,
            Name TEXT NOT NULL,
            Role TEXT CHECK (Role IN ('Admin', 'Professor', 'Student')) NOT NULL
        );
    """)

    # Create Courses table
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

    # Create Course_Stud table (mapping students to courses)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Course_Stud (
            CourseID INTEGER,
            StudentID INTEGER,
            PRIMARY KEY (CourseID, StudentID),
            FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
            FOREIGN KEY (StudentID) REFERENCES Users(UserID)
        );
    """)

    # Create Slots table (time slots for scheduling)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Slots (
            SlotID INTEGER PRIMARY KEY AUTOINCREMENT,
            StartTime TEXT NOT NULL,
            EndTime TEXT NOT NULL,
            Day TEXT NOT NULL,
            UNIQUE (StartTime, EndTime, Day)
        );
    """)

    # Create Professor_BusySlots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Professor_BusySlots (
            ProfessorID INTEGER,
            SlotID INTEGER,
            PRIMARY KEY (ProfessorID, SlotID),
            FOREIGN KEY (ProfessorID) REFERENCES Users(UserID),
            FOREIGN KEY (SlotID) REFERENCES Slots(SlotID)
        );
    """)

    # Create Schedule table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Schedule (
            CourseID INTEGER,
            SlotID INTEGER,
            PRIMARY KEY (CourseID, SlotID),
            FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
            FOREIGN KEY (SlotID) REFERENCES Slots(SlotID)
        );
    """)

    conn.commit()
    conn.close()


# Function to validate if an email belongs to an organization
def is_valid_email(org_name, email):
    conn = sqlite3.connect('organizations_meta.db')
    cursor = conn.cursor()

    cursor.execute("SELECT OrgDomains FROM Organizations WHERE OrgName = ?", (org_name,))
    result = cursor.fetchone()

    conn.close()

    if result:
        org_domains = result[0].split(",")
        return any(email.endswith(f"@{domain}") for domain in org_domains)
    return False


# Function to add an admin to an organization's database (stored in the Users table)
def add_admin(org_name, org_domains, admin_name, admin_email):
    # Ensure the admin's email matches the organization's allowed domains
    if not any(admin_email.endswith(f"@{domain}") for domain in org_domains):
        print(f"Error: The email {admin_email} is not allowed for {org_name}. Allowed domains: {org_domains}")
        return

    # Get or create the organization's database
    db_path = get_or_create_org_database(org_name, org_domains)

    # Connect to the organization's database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure the Users table exists before inserting
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Email TEXT UNIQUE NOT NULL,
            Name TEXT NOT NULL,
            Role TEXT CHECK (Role IN ('Admin', 'Professor', 'Student')) NOT NULL
        );
    """)

    # Insert admin into the Users table with "Admin" role
    cursor.execute("INSERT OR IGNORE INTO Users (Name, Email, Role) VALUES (?, ?, 'Admin')", (admin_name, admin_email))

    conn.commit()
    conn.close()
    print(f"Admin {admin_name} ({admin_email}) added to {org_name}'s database at {db_path}.")


# Function to display all registered organizations
def list_organizations():
    conn = sqlite3.connect('organizations_meta.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Organizations;")
    organizations = cursor.fetchall()

    if organizations:
        print("Registered Organizations:")
        for org in organizations:
            print(f"ID: {org[0]}, Name: {org[1]}, Allowed Domains: {org[2]}, DB Path: {org[3]}")
    else:
        print("No organizations registered yet.")

    conn.close()


# Function to list all users (admins, professors, and students) in an organization's database
def list_users(org_name):
    conn = sqlite3.connect('organizations_meta.db')
    cursor = conn.cursor()

    cursor.execute("SELECT DatabasePath FROM Organizations WHERE OrgName = ?", (org_name,))
    result = cursor.fetchone()

    if not result:
        print(f"Error: Organization {org_name} not found.")
        conn.close()
        return

    db_path = result[0]
    conn.close()

    # Connect to the organization's database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Users;")
    users = cursor.fetchall()

    if users:
        print(f"Users in {org_name}:")
        for user in users:
            print(f"ID: {user[0]}, Name: {user[2]}, Email: {user[1]}, Role: {user[3]}")
    else:
        print(f"No users found in {org_name}'s database.")

    conn.close()