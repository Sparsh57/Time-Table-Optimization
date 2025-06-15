from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from .models import Base, MetaBase, Organization
import logging
import time

logger = logging.getLogger(__name__)


def create_database_engine(db_path: str):
    """
    Creates a SQLAlchemy engine for the given database path.
    
    :param db_path: Path to the SQLite database file
    :return: SQLAlchemy engine
    """
    # Add connection parameters to handle SQLite locking and ensure proper behavior
    engine = create_engine(
        f'sqlite:///{db_path}', 
        echo=False,
        connect_args={
            'check_same_thread': False,
            'timeout': 30  # Add timeout for database locks
        }
    )
    return engine


def create_tables(db_path: str):
    """
    Creates all tables defined in the models for the given database.
    
    :param db_path: Path to the SQLite database file
    """
    engine = create_database_engine(db_path)
    
    # Retry mechanism for table creation to handle potential locking issues
    max_retries = 3
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(engine)
            logger.info(f"Created tables for database: {db_path}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Table creation attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(1)  # Wait before retry
            else:
                logger.error(f"Failed to create tables after {max_retries} attempts: {e}")
                raise
    
    # Always dispose of the engine
    engine.dispose()


def create_meta_tables(meta_db_path: str = "organizations_meta.db"):
    """
    Creates all tables for the meta-database.
    
    :param meta_db_path: Path to the meta-database file
    """
    engine = create_database_engine(meta_db_path)
    try:
        MetaBase.metadata.create_all(engine)
        logger.info(f"Created meta-database tables: {meta_db_path}")
    finally:
        engine.dispose()


@contextmanager
def get_db_session(db_path: str) -> Session:
    """
    Context manager that provides a SQLAlchemy session for the given database.
    Automatically handles session cleanup and rollback on errors.
    
    :param db_path: Path to the SQLite database file
    :yield: SQLAlchemy session
    """
    engine = create_database_engine(db_path)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


@contextmanager
def get_meta_db_session(meta_db_path: str = "organizations_meta.db") -> Session:
    """
    Context manager that provides a SQLAlchemy session for the meta-database.
    
    :param meta_db_path: Path to the meta-database file
    :yield: SQLAlchemy session
    """
    engine = create_database_engine(meta_db_path)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Meta-database session error: {e}")
        raise
    finally:
        session.close()


def get_organization_by_domain(email_domain: str, meta_db_path: str = "organizations_meta.db"):
    """
    Get organization information by email domain using SQLAlchemy.
    
    :param email_domain: Email domain to search for
    :param meta_db_path: Path to the meta-database file
    :return: Organization object or None
    """
    with get_meta_db_session(meta_db_path) as session:
        try:
            organizations = session.query(Organization).all()
            for org in organizations:
                allowed_domains = [d.strip() for d in org.OrgDomains.split(",")]
                if any(email_domain.endswith(f"@{domain}") for domain in allowed_domains):
                    return org
            return None
        except Exception as e:
            logger.error(f"Error finding organization by domain: {e}")
            return None


def get_all_organizations(meta_db_path: str = "organizations_meta.db"):
    """
    Get all organizations from the meta-database using SQLAlchemy.
    
    :param meta_db_path: Path to the meta-database file
    :return: List of Organization objects
    """
    with get_meta_db_session(meta_db_path) as session:
        try:
            return session.query(Organization).all()
        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")
            return []


def get_organization_by_name(org_name: str, meta_db_path: str = "organizations_meta.db"):
    """
    Get organization information by name using SQLAlchemy.
    
    :param org_name: Name of the organization
    :param meta_db_path: Path to the meta-database file
    :return: Organization object or None
    """
    with get_meta_db_session(meta_db_path) as session:
        try:
            return session.query(Organization).filter_by(OrgName=org_name).first()
        except Exception as e:
            logger.error(f"Error finding organization by name: {e}")
            return None


class DatabaseManager:
    """
    A class to manage database operations using SQLAlchemy.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.engine = create_database_engine(db_path)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables defined in the models."""
        Base.metadata.create_all(self.engine)
        logger.info(f"Created tables for database: {self.db_path}")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """Context manager for database sessions."""
        session = self.get_session()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close() 