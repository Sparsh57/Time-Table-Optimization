import os
from dotenv import load_dotenv
from src.database_management.dbconnection import (
    create_tables, 
    create_meta_tables, 
    get_db_session, 
    get_meta_db_session,
    get_organization_by_name,
    is_postgresql,
    get_organization_database_url
)
from src.database_management.models import User, Organization

# Load environment variables
load_dotenv()

# Define the directory where organization databases will be stored
DATA_DIR = os.path.join(os.getcwd(), "data")

# Ensure the `data/` directory exists (only for SQLite mode)
def ensure_data_directory():
    """Ensure data directory exists for SQLite mode."""
    if not is_postgresql() and not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


# Initialize the meta-database using SQLAlchemy
def init_meta_database():
    """
    Initialize the meta-database with SQLAlchemy.
    For PostgreSQL, ensures the meta schema exists first.
    """
    try:
        # For PostgreSQL, ensure the meta schema exists before creating tables
        if is_postgresql():
            from src.database_management.dbconnection import get_database_url, create_database_engine, create_schema_if_not_exists
            
            # Create the meta schema if it doesn't exist
            engine = create_database_engine(get_database_url())
            create_schema_if_not_exists(engine, "meta")
            engine.dispose()
            
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
        # For SQLite mode, ensure data directory exists
        if not is_postgresql():
            ensure_data_directory()
        
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
def init_org_database(db_path, org_name=None):
    """
    Initialize organization database using SQLAlchemy models.
    Ensures proper table creation and metadata synchronization.
    
    :param db_path: Path to the organization's database file or schema identifier
    :param org_name: Organization name (required for PostgreSQL)
    """
    try:
        # Create all tables using SQLAlchemy
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        
        # Verify tables were created successfully
        if is_postgresql() and org_name:
            session_context = get_db_session(get_organization_database_url(), org_name)
        else:
            session_context = get_db_session(db_path)
        
        with session_context as session:
            from sqlalchemy import text
            
            # Check if all expected tables exist
            if is_postgresql():
                # PostgreSQL query to check tables in schema
                if org_name:
                    from src.database_management.dbconnection import get_schema_for_organization
                    schema_name = get_schema_for_organization(org_name)
                    result = session.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema_name ORDER BY table_name"
                    ), {"schema_name": schema_name})
                else:
                    result = session.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
                    ))
            else:
                # SQLite query
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"))
                
                tables = [row[0] for row in result.fetchall()]
                
                expected_tables = ['Users', 'Courses', 'Course_Professor', 'Course_Stud', 
                                'Slots', 'Professor_BusySlots', 'Schedule']
                
                missing_tables = [table for table in expected_tables if table not in tables]
                if missing_tables:
                    print(f"Warning: Missing tables: {missing_tables}")
                    # Try to create tables again
                    if is_postgresql() and org_name:
                        create_tables(get_organization_database_url(), org_name)
                    else:
                        create_tables(db_path)
                        print("Attempted to recreate missing tables")
                else:
                    print(f"All expected tables created successfully: {tables}")
            
        if is_postgresql() and org_name:
            print(f"Initialized organization database with schema: {org_name}")
        else:
            print(f"Initialized organization database at: {db_path}")
    except Exception as e:
        print(f"Error initializing database {db_path}: {e}")
        raise


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

    # Ensure data directory exists for SQLite mode
    if not is_postgresql():
        ensure_data_directory()

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