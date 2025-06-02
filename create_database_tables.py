import os
from dotenv import load_dotenv
from src.database_management.dbconnection import (
    create_tables, 
    create_meta_tables, 
    get_db_session, 
    get_meta_db_session,
    get_organization_by_name
)
from src.database_management.models import User, Organization

# Load environment variables
load_dotenv()

# Define the directory where organization databases will be stored
DATA_DIR = os.path.join(os.getcwd(), "data")

# Ensure the `data/` directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# Initialize the meta-database using SQLAlchemy
def init_meta_database():
    """
    Initialize the meta-database with SQLAlchemy.
    """
    try:
        create_meta_tables()
        print("Meta-database initialized successfully")
    except Exception as e:
        print(f"Error initializing meta-database: {e}")


# Function to get or create an organization's database in the `data/` directory
def get_or_create_org_database(org_name, org_domains):
    """
    Get or create an organization's database using SQLAlchemy.
    
    :param org_name: Name of the organization
    :param org_domains: List of allowed email domains
    :return: Path to the organization's database
    """
    # Convert list of domains to a comma-separated string
    domain_str = ",".join(org_domains)
    
    # Check if the organization already exists using SQLAlchemy
    existing_org = get_organization_by_name(org_name)
    
    if existing_org:
        db_path = existing_org.DatabasePath
    else:
        # Generate a new database file for the organization in the `data/` subdirectory
        db_path = os.path.join(DATA_DIR, f"{org_name.replace(' ', '_')}.db")
        
        # Create organization record in meta-database using SQLAlchemy
        with get_meta_db_session() as session:
            try:
                new_org = Organization(
                    OrgName=org_name,
                    OrgDomains=domain_str,
                    DatabasePath=db_path
                )
                session.add(new_org)
                session.commit()
                print(f"Created organization record for {org_name}")
            except Exception as e:
                session.rollback()
                print(f"Error creating organization record: {e}")
                raise
        
        # Initialize the organization's database
        init_org_database(db_path)

    # Ensure the organization database is properly initialized
    init_org_database(db_path)
    return db_path


# Function to initialize a new organization's database with required tables using SQLAlchemy
def init_org_database(db_path):
    """
    Initialize organization database using SQLAlchemy models.
    
    :param db_path: Path to the organization's database file
    """
    try:
        # Create all tables using SQLAlchemy
        create_tables(db_path)
        print(f"Initialized organization database at: {db_path}")
    except Exception as e:
        print(f"Error initializing database {db_path}: {e}")


# Function to validate if an email belongs to an organization using SQLAlchemy
def is_valid_email(org_name, email):
    """
    Validate if an email belongs to an organization using SQLAlchemy.
    
    :param org_name: Name of the organization
    :param email: Email to validate
    :return: Boolean indicating if email is valid for the organization
    """
    org = get_organization_by_name(org_name)
    if org:
        org_domains = org.OrgDomains.split(",")
        return any(email.endswith(f"@{domain}") for domain in org_domains)
    return False


# Function to add an admin to an organization's database using SQLAlchemy
def add_admin(org_name, org_domains, admin_name, admin_email):
    """
    Add an admin to organization's database using SQLAlchemy.
    
    :param org_name: Name of the organization
    :param org_domains: List of allowed email domains
    :param admin_name: Name of the admin
    :param admin_email: Email of the admin
    """
    # Ensure the admin's email matches the organization's allowed domains
    if not any(admin_email.endswith(f"@{domain}") for domain in org_domains):
        print(f"Error: The email {admin_email} is not allowed for {org_name}. Allowed domains: {org_domains}")
        return

    # Get or create the organization's database
    db_path = get_or_create_org_database(org_name, org_domains)

    # Add admin using SQLAlchemy
    try:
        with get_db_session(db_path) as session:
            # Check if admin already exists
            existing_admin = session.query(User).filter_by(Email=admin_email).first()
            if not existing_admin:
                new_admin = User(
                    Name=admin_name,
                    Email=admin_email,
                    Role='Admin'
                )
                session.add(new_admin)
                session.commit()
                print(f"Admin {admin_name} ({admin_email}) added to {org_name}'s database at {db_path}.")
            else:
                print(f"Admin {admin_email} already exists in {org_name}'s database.")
    except Exception as e:
        print(f"Error adding admin: {e}")


# Function to display all registered organizations using SQLAlchemy
def list_organizations():
    """
    List all registered organizations using SQLAlchemy.
    """
    from src.database_management.dbconnection import get_all_organizations
    
    organizations = get_all_organizations()
    
    if organizations:
        print("Registered Organizations:")
        for org in organizations:
            print(f"ID: {org.OrgID}, Name: {org.OrgName}, Allowed Domains: {org.OrgDomains}, DB Path: {org.DatabasePath}")
    else:
        print("No organizations registered yet.")


# Function to list all users in an organization's database using SQLAlchemy
def list_users(org_name):
    """
    List all users in an organization's database using SQLAlchemy.
    
    :param org_name: Name of the organization
    """
    org = get_organization_by_name(org_name)
    
    if not org:
        print(f"Error: Organization {org_name} not found.")
        return

    db_path = org.DatabasePath

    # List users using SQLAlchemy
    try:
        with get_db_session(db_path) as session:
            users = session.query(User).all()
            if users:
                print(f"Users in {org_name}:")
                for user in users:
                    print(f"ID: {user.UserID}, Name: {user.Name}, Email: {user.Email}, Role: {user.Role}")
            else:
                print(f"No users found in {org_name}'s database.")
    except Exception as e:
        print(f"Error listing users: {e}")