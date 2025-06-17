from .dbconnection import get_db_session, create_tables
from .models import User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def add_admin_user(db_path, name, email, created_by_admin_email=None):
    """
    Add a new admin user to the system with hierarchy tracking.
    
    :param db_path: Path to the database file
    :param name: Name of the admin user
    :param email: Email of the admin user
    :param created_by_admin_email: Email of the admin who is creating this user
    :return: True if successful, False otherwise
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Users LIMIT 1"))
    except Exception:
        logger.info("Users table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")
    
    with get_db_session(db_path) as session:
        try:
            # Get the creating admin's ID if provided
            created_by_admin_id = None
            if created_by_admin_email:
                creating_admin = session.query(User).filter_by(Email=created_by_admin_email, Role='Admin').first()
                if creating_admin:
                    created_by_admin_id = creating_admin.UserID
            
            # Check if user already exists
            existing_user = session.query(User).filter_by(Email=email).first()
            
            if existing_user:
                if existing_user.Role == 'Admin':
                    logger.info(f"User {email} is already an admin")
                    return False, "User is already an admin"
                else:
                    # Update existing user to admin
                    existing_user.Role = 'Admin'
                    existing_user.Name = name  # Update name too
                    existing_user.CreatedByAdminID = created_by_admin_id
                    session.commit()
                    logger.info(f"Updated user {email} to admin role")
                    return True, f"User {email} has been promoted to admin"
            else:
                # Create new admin user
                new_admin = User(
                    Name=name,
                    Email=email,
                    Role='Admin',
                    CreatedByAdminID=created_by_admin_id
                )
                session.add(new_admin)
                session.commit()
                logger.info(f"Created new admin user: {email}")
                return True, f"Admin user {email} created successfully"
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding admin user {email}: {e}")
            return False, f"Database error: {str(e)}"


def can_remove_admin(db_path, remover_email, target_email):
    """
    Check if an admin can remove another admin based on hierarchy.
    
    :param db_path: Path to the database file
    :param remover_email: Email of the admin trying to remove
    :param target_email: Email of the admin to be removed
    :return: (can_remove, reason)
    """
    with get_db_session(db_path) as session:
        try:
            remover = session.query(User).filter_by(Email=remover_email, Role='Admin').first()
            target = session.query(User).filter_by(Email=target_email, Role='Admin').first()
            
            if not remover or not target:
                return False, "Admin not found"
            
            # Cannot remove yourself
            if remover_email == target_email:
                return False, "Cannot remove yourself"
            
            # Check if this is the last admin
            admin_count = session.query(User).filter_by(Role='Admin').count()
            if admin_count <= 1:
                return False, "Cannot remove the last admin"
            
            # Founder admin cannot be removed by anyone
            if target.IsFounderAdmin == 1:
                return False, "Cannot remove the organization founder"
            
            # If target was created by remover, remover can remove them
            if target.CreatedByAdminID == remover.UserID:
                return True, "Can remove - you created this admin"
            
            # If remover is the founder, they can remove anyone (except themselves)
            if remover.IsFounderAdmin == 1:
                return True, "Can remove - you are the organization founder"
            
            # Otherwise, cannot remove
            return False, "Cannot remove this admin - insufficient privileges"
            
        except Exception as e:
            logger.error(f"Error checking admin removal permissions: {e}")
            return False, f"Error: {str(e)}"


def remove_admin_user(db_path, email, remover_email=None):
    """
    Remove admin privileges from a user with hierarchy checks.
    
    :param db_path: Path to the database file
    :param email: Email of the admin user to demote
    :param remover_email: Email of the admin performing the removal
    :return: True if successful, False otherwise
    """
    # Check permissions first if remover is specified
    if remover_email:
        can_remove, reason = can_remove_admin(db_path, remover_email, email)
        if not can_remove:
            return False, reason
    
    with get_db_session(db_path) as session:
        try:
            user = session.query(User).filter_by(Email=email, Role='Admin').first()
            
            if not user:
                return False, "Admin user not found"
            
            # Change role to regular user (or could be deleted entirely)
            # For safety, we'll just demote rather than delete
            user.Role = 'Student'  # or could ask what role to assign
            user.CreatedByAdminID = None  # Clear the hierarchy
            session.commit()
            
            logger.info(f"Removed admin privileges from user: {email}")
            return True, f"Admin privileges removed from {email}"
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error removing admin user {email}: {e}")
            return False, f"Database error: {str(e)}"


def get_all_admins(db_path):
    """
    Get list of all admin users with hierarchy information.
    
    :param db_path: Path to the database file
    :return: List of admin user dictionaries
    """
    with get_db_session(db_path) as session:
        try:
            admins = session.query(User).filter_by(Role='Admin').all()
            result = []
            for admin in admins:
                result.append({
                    'user_id': admin.UserID,
                    'name': admin.Name,
                    'email': admin.Email,
                    'created_by_admin_id': admin.CreatedByAdminID,
                    'is_founder_admin': admin.IsFounderAdmin
                })
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error fetching admin users: {e}")
            return []


def is_user_admin(db_path, email):
    """
    Check if a user is an admin.
    
    :param db_path: Path to the database file
    :param email: Email to check
    :return: True if user is admin, False otherwise
    """
    with get_db_session(db_path) as session:
        try:
            admin = session.query(User).filter_by(Email=email, Role='Admin').first()
            return admin is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking admin status for {email}: {e}")
            return False


def ensure_first_admin(db_path, name, email):
    """
    Ensure there is at least one admin in the system and mark them as founder.
    This is typically called during initial setup.
    
    :param db_path: Path to the database file
    :param name: Name of the first admin
    :param email: Email of the first admin
    :return: True if successful, False otherwise
    """
    with get_db_session(db_path) as session:
        try:
            # Check if any admin exists
            admin_count = session.query(User).filter_by(Role='Admin').count()
            
            if admin_count == 0:
                # No admins exist, create the first one as founder
                new_admin = User(
                    Name=name,
                    Email=email,
                    Role='Admin',
                    IsFounderAdmin=1,  # Mark as founder
                    CreatedByAdminID=None
                )
                session.add(new_admin)
                session.commit()
                logger.info(f"Created founder admin user: {email}")
                return True, f"Founder admin {email} created successfully"
            else:
                # Admins already exist
                return True, "Admin users already exist"
                
        except SQLAlchemyError as e:
            logger.error(f"Error ensuring first admin: {e}")
            return False, f"Database error: {str(e)}"


def get_admin_count(db_path):
    """
    Get the total number of admin users.
    
    :param db_path: Path to the database file
    :return: Number of admin users
    """
    with get_db_session(db_path) as session:
        try:
            return session.query(User).filter_by(Role='Admin').count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting admin users: {e}")
            return 0


# User repair functions removed - user creation now handled automatically in OAuth callback  