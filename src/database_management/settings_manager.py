from .dbconnection import get_db_session, create_tables
from .models import Settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def get_setting(db_path, setting_key, default_value=None):
    """
    Get a setting value from the database.
    
    :param db_path: Path to the database file
    :param setting_key: The setting key to retrieve
    :param default_value: Default value if setting doesn't exist
    :return: Setting value or default_value
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Settings LIMIT 1"))
    except Exception:
        logger.info("Settings table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")
    
    with get_db_session(db_path) as session:
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


def set_setting(db_path, setting_key, setting_value, description=None):
    """
    Set a setting value in the database.
    
    :param db_path: Path to the database file
    :param setting_key: The setting key
    :param setting_value: The setting value
    :param description: Optional description of the setting
    """
    # First, ensure tables exist
    try:
        with get_db_session(db_path) as session:
            session.execute(text("SELECT 1 FROM Settings LIMIT 1"))
    except Exception:
        logger.info("Settings table not found, creating tables...")
        create_tables(db_path)
        logger.info("Tables created successfully")
    
    with get_db_session(db_path) as session:
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


def get_max_classes_per_slot(db_path):
    """
    Get the configured maximum classes per time slot.
    
    :param db_path: Path to the database file
    :return: Maximum classes per slot (default: 24)
    """
    return get_setting(db_path, "max_classes_per_slot", 24)


def set_max_classes_per_slot(db_path, max_classes):
    """
    Set the maximum classes per time slot.
    
    :param db_path: Path to the database file
    :param max_classes: Maximum number of classes per slot
    """
    set_setting(db_path, "max_classes_per_slot", max_classes, 
                "Maximum number of classes allowed per time slot")


def initialize_default_settings(db_path):
    """
    Initialize default settings in the database.
    
    :param db_path: Path to the database file
    """
    # Set default max classes per slot if not already set
    if get_setting(db_path, "max_classes_per_slot") is None:
        set_max_classes_per_slot(db_path, 24)
        logger.info("Initialized default max_classes_per_slot to 24")


def get_all_settings(db_path):
    """
    Get all settings from the database.
    
    :param db_path: Path to the database file
    :return: Dictionary of all settings
    """
    with get_db_session(db_path) as session:
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