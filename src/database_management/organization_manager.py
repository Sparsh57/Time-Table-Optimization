from .dbconnection import (
    get_meta_db_session, 
    get_db_session, 
    create_tables,
    is_postgresql,
    get_organization_database_url,
    get_schema_for_organization
)
from .models import Organization, User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
import logging
import os

logger = logging.getLogger(__name__)


def validate_organization_creation(org_name, org_domains, user_email):
    """
    Validate that an organization can be created with the given parameters.
    
    :param org_name: Name of the organization
    :param org_domains: Comma-separated list of allowed domains
    :param user_email: Email of the user trying to create the organization
    :return: (is_valid, error_message)
    """
    try:
        with get_meta_db_session() as session:
            # Check if organization name already exists
            existing_org_by_name = session.query(Organization).filter_by(OrgName=org_name).first()
            if existing_org_by_name:
                return False, f"Organization name '{org_name}' already exists. Please choose a different name."
            
            # Parse domains and check for conflicts
            domain_list = [d.strip() for d in org_domains.split(",")]
            
            # Check if any of the domains are already registered
            existing_orgs = session.query(Organization).all()
            for existing_org in existing_orgs:
                existing_domains = [d.strip() for d in existing_org.OrgDomains.split(",")]
                
                # Check for domain overlap
                overlapping_domains = set(domain_list) & set(existing_domains)
                if overlapping_domains:
                    return False, f"Domain(s) {', '.join(overlapping_domains)} already registered with organization '{existing_org.OrgName}'"
            
            # Check if user's email domain matches one of the provided domains
            user_domain = user_email.split('@')[1] if '@' in user_email else ''
            if user_domain not in domain_list:
                return False, f"Your email domain '{user_domain}' must be included in the organization domains."
            
            return True, "Validation successful"
            
    except Exception as e:
        logger.error(f"Error validating organization creation: {e}")
        return False, f"Validation error: {str(e)}"


def get_user_organization(user_email):
    """
    Get the organization that a user belongs to based on their email domain.
    
    :param user_email: Email address of the user
    :return: Organization object or None
    """
    try:
        user_domain = user_email.split('@')[1] if '@' in user_email else ''
        
        with get_meta_db_session() as session:
            organizations = session.query(Organization).all()
            
            for org in organizations:
                allowed_domains = [d.strip() for d in org.OrgDomains.split(",")]
                if user_domain in allowed_domains:
                    return org
            
            return None
            
    except Exception as e:
        logger.error(f"Error finding user organization: {e}")
        return None


def should_redirect_to_registration(user_email):
    """
    Determine if a user should be redirected to organization registration.
    
    :param user_email: Email address of the user
    :return: True if user should register organization, False otherwise
    """
    return get_user_organization(user_email) is None


def create_organization_with_validation(org_name, org_domains, user_email, user_name, db_path, max_classes_per_slot=24):
    """
    Create a new organization with comprehensive validation.
    
    :param org_name: Name of the organization
    :param org_domains: Comma-separated list of allowed domains
    :param user_email: Email of the first admin user
    :param user_name: Name of the first admin user
    :param db_path: Path to the organization database (SQLite) or URL (PostgreSQL)
    :param max_classes_per_slot: Maximum classes per time slot setting
    :return: (success, message, organization, database_path)
    """
    # Validate before creating
    is_valid, validation_message = validate_organization_creation(org_name, org_domains, user_email)
    if not is_valid:
        return False, validation_message, None, None
    
    try:
        # For PostgreSQL, use schema-based approach; for SQLite, use file paths
        if is_postgresql():
            database_path = f"schema:{get_schema_for_organization(org_name)}"
        else:
            database_path = db_path
        
        with get_meta_db_session() as session:
            # Create organization record
            new_org = Organization(
                OrgName=org_name,
                OrgDomains=org_domains,
                DatabasePath=database_path
            )
            session.add(new_org)
            session.commit()
            
            logger.info(f"Created organization: {org_name}")
            
            # Extract database path while organization is still attached to session
            org_database_path = new_org.DatabasePath
            
        # Create organization database and tables (outside the session context)
        if is_postgresql():
            create_tables(get_organization_database_url(), org_name)
        else:
            create_tables(db_path)
        
        # Add first admin user to organization database as founder
        from .admin_manager import ensure_first_admin
        if is_postgresql():
            ensure_first_admin(database_path, user_name, user_email, org_name)
        else:
            ensure_first_admin(db_path, user_name, user_email)
        
        # Set the max classes per slot setting
        from .settings_manager import set_max_classes_per_slot
        if is_postgresql():
            set_max_classes_per_slot(database_path, max_classes_per_slot, org_name)
        else:
            set_max_classes_per_slot(db_path, max_classes_per_slot)
        
        return True, f"Organization '{org_name}' created successfully", new_org, org_database_path
        
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        return False, f"Failed to create organization: {str(e)}", None, None


def get_organization_summary(org_name):
    """
    Get summary information about an organization.
    
    :param org_name: Name of the organization
    :return: Dictionary with organization summary
    """
    try:
        with get_meta_db_session() as session:
            org = session.query(Organization).filter_by(OrgName=org_name).first()
            if not org:
                return None
            
            # Get user counts from organization database
            try:
                if is_postgresql() and org.DatabasePath.startswith("schema:"):
                    # Extract org name for schema access
                    with get_db_session(get_organization_database_url(), org_name) as org_session:
                        admin_count = org_session.query(User).filter_by(Role='Admin').count()
                        professor_count = org_session.query(User).filter_by(Role='Professor').count()
                        student_count = org_session.query(User).filter_by(Role='Student').count()
                else:
                    # SQLite path
                    with get_db_session(org.DatabasePath) as org_session:
                        admin_count = org_session.query(User).filter_by(Role='Admin').count()
                        professor_count = org_session.query(User).filter_by(Role='Professor').count()
                        student_count = org_session.query(User).filter_by(Role='Student').count()
            except Exception:
                admin_count = professor_count = student_count = 0
            
            return {
                'org_id': org.OrgID,
                'org_name': org.OrgName,
                'org_domains': org.OrgDomains.split(','),
                'database_path': org.DatabasePath,
                'admin_count': admin_count,
                'professor_count': professor_count,
                'student_count': student_count,
                'total_users': admin_count + professor_count + student_count
            }
            
    except Exception as e:
        logger.error(f"Error getting organization summary: {e}")
        return None


def list_all_organizations():
    """
    Get a list of all organizations in the system.
    
    :return: List of organization summaries
    """
    try:
        with get_meta_db_session() as session:
            organizations = session.query(Organization).all()
            
            org_list = []
            for org in organizations:
                summary = get_organization_summary(org.OrgName)
                if summary:
                    org_list.append(summary)
            
            return org_list
            
    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        return []


def check_domain_availability(domains_string):
    """
    Check if the provided domains are available for registration.
    
    :param domains_string: Comma-separated list of domains
    :return: (available, conflicting_domains, conflicting_orgs)
    """
    try:
        domain_list = [d.strip() for d in domains_string.split(",")]
        conflicting_domains = []
        conflicting_orgs = []
        
        with get_meta_db_session() as session:
            existing_orgs = session.query(Organization).all()
            
            for org in existing_orgs:
                existing_domains = [d.strip() for d in org.OrgDomains.split(",")]
                
                # Check for domain overlap
                overlapping = set(domain_list) & set(existing_domains)
                if overlapping:
                    conflicting_domains.extend(list(overlapping))
                    conflicting_orgs.append(org.OrgName)
        
        is_available = len(conflicting_domains) == 0
        return is_available, conflicting_domains, conflicting_orgs
        
    except Exception as e:
        logger.error(f"Error checking domain availability: {e}")
        return False, [], []


def get_organization_by_user_role(user_email, required_role=None):
    """
    Get organization and check if user has required role.
    
    :param user_email: Email of the user
    :param required_role: Required role (Admin, Professor, Student) or None
    :return: (organization, user_role, has_required_role)
    """
    try:
        org = get_user_organization(user_email)
        if not org:
            return None, None, False
        
        # Check user role in organization database
        if is_postgresql() and org.DatabasePath.startswith("schema:"):
            with get_db_session(get_organization_database_url(), org.OrgName) as session:
                user = session.query(User).filter_by(Email=user_email).first()
                user_role = user.Role if user else 'Student'  # Default to Student
        else:
            with get_db_session(org.DatabasePath) as session:
                user = session.query(User).filter_by(Email=user_email).first()
                user_role = user.Role if user else 'Student'  # Default to Student
            
            has_required_role = True
            if required_role:
                has_required_role = (user_role == required_role)
            
            return org, user_role, has_required_role
            
    except Exception as e:
        logger.error(f"Error checking user organization role: {e}")
        return None, None, False


def delete_organization(org_name, admin_email, confirmation_token=None):
    """
    Delete an organization and all its associated data.
    Requires confirmation from a founder admin.
    
    :param org_name: Name of the organization to delete
    :param admin_email: Email of the admin requesting deletion
    :param confirmation_token: Security token for confirmation
    :return: (success, message)
    """
    try:
        # Verify organization exists
        org = get_organization_by_name(org_name)
        if not org:
            return False, f"Organization '{org_name}' not found"
        
        # Verify admin has permission to delete (must be founder)
        from .admin_manager import is_user_admin
        if not is_user_admin(org.DatabasePath, admin_email, org_name):
            return False, "Only founder admins can delete organizations"
        
        # Check if user is founder admin
        if is_postgresql() and org.DatabasePath.startswith("schema:"):
            with get_db_session(get_organization_database_url(), org_name) as session:
                admin_user = session.query(User).filter_by(Email=admin_email, IsFounderAdmin=1).first()
        else:
            with get_db_session(org.DatabasePath) as session:
                admin_user = session.query(User).filter_by(Email=admin_email, IsFounderAdmin=1).first()
        
        if not admin_user:
            return False, "Only the organization founder can delete the organization"
        
        # Delete organization database/schema
        if is_postgresql() and org.DatabasePath.startswith("schema:"):
            # For PostgreSQL, drop the schema
            schema_name = org.DatabasePath.replace("schema:", "")
            from sqlalchemy import text
            with get_db_session(get_organization_database_url()) as session:
                session.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
                session.commit()
        else:
            # For SQLite, delete the database file
            if os.path.exists(org.DatabasePath):
                os.remove(org.DatabasePath)
        
        # Remove organization from meta-database
        with get_meta_db_session() as session:
            org_to_delete = session.query(Organization).filter_by(OrgName=org_name).first()
            if org_to_delete:
                session.delete(org_to_delete)
                session.commit()
        
        logger.info(f"Successfully deleted organization: {org_name}")
        return True, f"Organization '{org_name}' has been permanently deleted"
        
    except Exception as e:
        logger.error(f"Error deleting organization {org_name}: {e}")
        return False, f"Failed to delete organization: {str(e)}"


def get_organization_deletion_confirmation_data(org_name, admin_email):
    """
    Get data needed for organization deletion confirmation.
    
    :param org_name: Name of the organization
    :param admin_email: Email of the admin requesting deletion
    :return: Dictionary with confirmation data
    """
    try:
        org_summary = get_organization_summary(org_name)
        if not org_summary:
            return None
            
        return {
            'org_name': org_name,
            'total_users': org_summary['total_users'],
            'admin_count': org_summary['admin_count'],
            'professor_count': org_summary['professor_count'],
            'student_count': org_summary['student_count'],
            'domains': org_summary['org_domains'],
            'requester_email': admin_email
        }
        
    except Exception as e:
        logger.error(f"Error getting deletion confirmation data: {e}")
        return None 