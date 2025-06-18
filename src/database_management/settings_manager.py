from .dbconnection import (
    get_db_session, 
    create_tables, 
    is_postgresql, 
    get_organization_database_url
)
from .models import Settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def get_org_name_from_path(db_path):
    """
    Extract organization name from database path.
    For PostgreSQL schema paths, extract from 'schema:org_name' format.
    For SQLite, this returns None as org_name isn't needed.
    
    :param db_path: Database path or schema identifier
    :return: Organization name or None
    """
    if db_path and db_path.startswith("schema:"):
        # Extract org name from schema path
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            return schema_name[4:]  # Remove 'org_' prefix
    return None


def get_setting(db_path, setting_key, default_value=None, org_name=None):
    """
    Get a setting value from the database.
    
    :param db_path: Path to the database file or schema identifier
    :param setting_key: The setting key to retrieve
    :param default_value: Default value if setting doesn't exist
    :param org_name: Organization name (required for PostgreSQL)
    :return: Setting value or default_value
    """
    # Auto-detect org_name if not provided
    if org_name is None:
        org_name = get_org_name_from_path(db_path)
    
    # First, ensure tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Settings\" LIMIT 1"))
        else:

            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Settings LIMIT 1"))
    except Exception:
        logger.info("Settings table not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:

            create_tables(db_path)
        logger.info("Tables created successfully")
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            setting = session.query(Settings).filter_by(SettingKey=setting_key).first()
            if setting:
                # Try to convert to appropriate type
                value = setting.SettingValue
                
                # Try to convert to int if possible
                try:
                    return int(value)
                except ValueError:
                    pass
                
                # Try to convert to float if possible
                try:
                    return float(value)
                except ValueError:
                    pass
                
                # Return as string
                return value
            else:
                return default_value
        except SQLAlchemyError as e:
            logger.error(f"Error getting setting {setting_key}: {e}")
            return default_value


def set_setting(db_path, setting_key, setting_value, description=None, org_name=None):
    """
    Set a setting value in the database.
    
    :param db_path: Path to the database file or schema identifier
    :param setting_key: The setting key
    :param setting_value: The setting value
    :param description: Optional description of the setting
    :param org_name: Organization name (required for PostgreSQL)
    """
    # Auto-detect org_name if not provided
    if org_name is None:
        org_name = get_org_name_from_path(db_path)
    
    # First, ensure tables exist
    try:
        if is_postgresql() and org_name:
            with get_db_session(get_organization_database_url(), org_name) as session:
                session.execute(text("SELECT 1 FROM \"Settings\" LIMIT 1"))
        else:

            with get_db_session(db_path) as session:
                session.execute(text("SELECT 1 FROM Settings LIMIT 1"))
    except Exception:
        logger.info("Settings table not found, creating tables...")
        if is_postgresql() and org_name:
            create_tables(get_organization_database_url(), org_name)
        else:

            create_tables(db_path)
        logger.info("Tables created successfully")
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            # Check if setting already exists
            existing_setting = session.query(Settings).filter_by(SettingKey=setting_key).first()
            
            if existing_setting:
                # Update existing setting
                existing_setting.SettingValue = str(setting_value)
                if description:
                    existing_setting.Description = description
            else:
                # Create new setting
                new_setting = Settings(
                    SettingKey=setting_key,
                    SettingValue=str(setting_value),
                    Description=description
                )
                session.add(new_setting)
            
            session.commit()
            logger.info(f"Setting {setting_key} set to {setting_value}")
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error setting {setting_key}: {e}")
            raise


def get_max_classes_per_slot(db_path, org_name=None):
    """
    Get the configured maximum classes per time slot.
    
    :param db_path: Path to the database file or schema identifier
    :param org_name: Organization name (required for PostgreSQL)
    :return: Maximum classes per slot (default: 24)
    """
    return get_setting(db_path, "max_classes_per_slot", 24, org_name)


def set_max_classes_per_slot(db_path, max_classes, org_name=None):
    """
    Set the maximum classes per time slot.
    
    :param db_path: Path to the database file or schema identifier
    :param max_classes: Maximum number of classes per slot
    :param org_name: Organization name (required for PostgreSQL)
    """
    set_setting(db_path, "max_classes_per_slot", max_classes, 
                "Maximum number of classes allowed per time slot", org_name)


def initialize_default_settings(db_path, org_name=None):
    """
    Initialize default settings in the database.
    
    :param db_path: Path to the database file or schema identifier
    :param org_name: Organization name (required for PostgreSQL)
    """
    # Set default max classes per slot if not already set
    if get_setting(db_path, "max_classes_per_slot", None, org_name) is None:
        set_max_classes_per_slot(db_path, 24, org_name)
        logger.info("Initialized default max_classes_per_slot to 24")


def get_all_settings(db_path, org_name=None):
    """
    Get all settings from the database.
    
    :param db_path: Path to the database file or schema identifier
    :param org_name: Organization name (required for PostgreSQL)
    :return: Dictionary of all settings
    """
    # Auto-detect org_name if not provided
    if org_name is None:
        org_name = get_org_name_from_path(db_path)
    
    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)
    
    with session_context as session:
        try:
            settings = session.query(Settings).all()
            result = {}
            for setting in settings:
                # Try to convert to appropriate type
                value = setting.SettingValue
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # Keep as string
                
                result[setting.SettingKey] = {
                    'value': value,
                    'description': setting.Description
                }
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting all settings: {e}")
            return {} 