import sqlite3
import logging
from .dbconnection import get_db_session, is_postgresql, get_organization_database_url
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def migrate_database_for_sections(db_path):
    """
    Migrate existing database to support sections by adding necessary columns.
    Only applies to SQLite databases - PostgreSQL schemas are created fresh.
    
    :param db_path: Path to the database file or schema identifier
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # For PostgreSQL, we need to handle migrations differently
    if is_postgresql():
        logger.info(f"Starting PostgreSQL migration for schema: {db_path}")
        migrate_postgresql_schema(db_path)
        return
    
    logger.info(f"Starting database migration for sections: {db_path}")
    
    try:
        with get_db_session(db_path) as session:
            # Check if Course_Stud.SectionNumber column exists
            try:
                session.execute(text("SELECT SectionNumber FROM Course_Stud LIMIT 1"))
                logger.info("SectionNumber column already exists in Course_Stud")
            except Exception:
                # Add SectionNumber column to Course_Stud table
                logger.info("Adding SectionNumber column to Course_Stud table")
                session.execute(text("ALTER TABLE Course_Stud ADD COLUMN SectionNumber INTEGER DEFAULT 1"))
                session.commit()
                logger.info("Successfully added SectionNumber column to Course_Stud")
            
            # Check if Courses.NumberOfSections column exists
            try:
                session.execute(text("SELECT NumberOfSections FROM Courses LIMIT 1"))
                logger.info("NumberOfSections column already exists in Courses")
            except Exception:
                # Add NumberOfSections column to Courses table
                logger.info("Adding NumberOfSections column to Courses table")
                session.execute(text("ALTER TABLE Courses ADD COLUMN NumberOfSections INTEGER DEFAULT 1"))
                session.commit()
                logger.info("Successfully added NumberOfSections column to Courses")
            
            # Check if Course_Professor.SectionNumber column exists
            try:
                session.execute(text("SELECT SectionNumber FROM Course_Professor LIMIT 1"))
                logger.info("SectionNumber column already exists in Course_Professor")
            except Exception:
                # Need to recreate Course_Professor table with new schema
                logger.info("Migrating Course_Professor table to support sections")
                
                # Backup existing course-professor relationships
                existing_relationships = session.execute(text("SELECT CourseID, ProfessorID FROM Course_Professor")).fetchall()
                
                # Drop the old Course_Professor table
                session.execute(text("DROP TABLE Course_Professor"))
                
                # Create new Course_Professor table with SectionNumber
                session.execute(text("""
                    CREATE TABLE Course_Professor (
                        CourseID INTEGER NOT NULL,
                        ProfessorID INTEGER NOT NULL,
                        SectionNumber INTEGER DEFAULT 1,
                        PRIMARY KEY (CourseID, ProfessorID, SectionNumber),
                        FOREIGN KEY (CourseID) REFERENCES Courses (CourseID),
                        FOREIGN KEY (ProfessorID) REFERENCES Users (UserID)
                    )
                """))
                
                # Restore relationships with default section 1
                for course_id, professor_id in existing_relationships:
                    session.execute(text("""
                        INSERT INTO Course_Professor (CourseID, ProfessorID, SectionNumber)
                        VALUES (:course_id, :professor_id, 1)
                    """), {'course_id': course_id, 'professor_id': professor_id})
                
                session.commit()
                logger.info("Successfully migrated Course_Professor table with SectionNumber")
            
            # Handle Schedule table migration
            try:
                # Check if the old Schedule table has SectionID (old schema)
                old_schedule_columns = session.execute(text("PRAGMA table_info(Schedule)")).fetchall()
                column_names = [col[1] for col in old_schedule_columns]
                
                if 'SectionID' in column_names and 'CourseID' not in column_names:
                    logger.info("Migrating Schedule table from old schema (SectionID) to new schema (CourseID)")
                    
                    # Backup old schedule data if any exists
                    old_schedule_data = session.execute(text("SELECT * FROM Schedule")).fetchall()
                    
                    # Drop the old Schedule table
                    session.execute(text("DROP TABLE Schedule"))
                    
                    # Create new Schedule table with correct schema including SectionNumber
                    session.execute(text("""
                        CREATE TABLE Schedule (
                            CourseID INTEGER NOT NULL,
                            SlotID INTEGER NOT NULL,
                            SectionNumber INTEGER DEFAULT 1,
                            PRIMARY KEY (CourseID, SlotID, SectionNumber),
                            FOREIGN KEY (CourseID) REFERENCES Courses (CourseID),
                            FOREIGN KEY (SlotID) REFERENCES Slots (SlotID)
                        )
                    """))
                    
                    session.commit()
                    logger.info("Successfully migrated Schedule table to new schema with SectionNumber")
                    
                elif 'CourseID' in column_names and 'SectionNumber' not in column_names:
                    logger.info("Adding SectionNumber column to existing Schedule table")
                    # Add SectionNumber column to existing Schedule table
                    session.execute(text("ALTER TABLE Schedule ADD COLUMN SectionNumber INTEGER DEFAULT 1"))
                    session.commit()
                    logger.info("Successfully added SectionNumber column to Schedule table")
                    
                elif 'CourseID' in column_names and 'SectionNumber' in column_names:
                    logger.info("Schedule table already has correct schema with SectionNumber")
                else:
                    # Create Schedule table if it doesn't exist at all
                    logger.info("Creating Schedule table with correct schema")
                    session.execute(text("""
                        CREATE TABLE Schedule (
                            CourseID INTEGER NOT NULL,
                            SlotID INTEGER NOT NULL,
                            SectionNumber INTEGER DEFAULT 1,
                            PRIMARY KEY (CourseID, SlotID, SectionNumber),
                            FOREIGN KEY (CourseID) REFERENCES Courses (CourseID),
                            FOREIGN KEY (SlotID) REFERENCES Slots (SlotID)
                        )
                    """))
                    session.commit()
                    
            except Exception as e:
                logger.error(f"Error handling Schedule table migration: {e}")
                # If something goes wrong, create the table with correct schema
                try:
                    session.execute(text("DROP TABLE IF EXISTS Schedule"))
                    session.execute(text("""
                        CREATE TABLE Schedule (
                            CourseID INTEGER NOT NULL,
                            SlotID INTEGER NOT NULL,
                            SectionNumber INTEGER DEFAULT 1,
                            PRIMARY KEY (CourseID, SlotID, SectionNumber),
                            FOREIGN KEY (CourseID) REFERENCES Courses (CourseID),
                            FOREIGN KEY (SlotID) REFERENCES Slots (SlotID)
                        )
                    """))
                    session.commit()
                    logger.info("Created Schedule table with correct schema after error")
                except Exception as e2:
                    logger.error(f"Failed to create Schedule table: {e2}")
                    raise
        
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        raise


def migrate_postgresql_schema(db_path):
    """
    Migrate PostgreSQL schema to support sections by adding necessary columns.
    
    :param db_path: Schema identifier for PostgreSQL (e.g., "schema:org_myorg")
    """
    from .dbconnection import get_organization_database_url
    
    # Auto-detect org_name from db_path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    if not org_name:
        raise ValueError(f"Invalid PostgreSQL schema path: {db_path}")
    
    logger.info(f"Starting PostgreSQL migration for organization: {org_name}")
    
    try:
        with get_db_session(get_organization_database_url(), org_name) as session:
            # Check if Course_Professor table exists and has SectionNumber column
            try:
                # First check if the table exists at all
                session.execute(text('SELECT 1 FROM "Course_Professor" LIMIT 1'))
                table_exists = True
            except SQLAlchemyError:
                session.rollback()
                table_exists = False
                logger.info("Course_Professor table does not exist")
            
            if table_exists:
                # Table exists, check if SectionNumber column exists
                try:
                    session.execute(text('SELECT "SectionNumber" FROM "Course_Professor" LIMIT 1'))
                    logger.info("SectionNumber column already exists in Course_Professor")
                except SQLAlchemyError:
                    session.rollback()
                    logger.info("Adding SectionNumber column to Course_Professor table")
                    
                    try:
                        # First, try to add the column
                        session.execute(text('ALTER TABLE "Course_Professor" ADD COLUMN "SectionNumber" INTEGER DEFAULT 1'))
                        session.commit()
                        logger.info("Successfully added SectionNumber column to Course_Professor")
                    except SQLAlchemyError as e:
                        # Rollback and recreate table
                        session.rollback()
                        logger.warning(f"Could not add column directly: {e}")
                        logger.info("Recreating Course_Professor table with new schema")
                        
                        try:
                            # Backup existing relationships
                            existing_relationships = session.execute(text('SELECT "CourseID", "ProfessorID" FROM "Course_Professor"')).fetchall()
                            
                            # Drop the old table
                            session.execute(text('DROP TABLE "Course_Professor"'))
                            
                            # Create new table with SectionNumber
                            session.execute(text('''
                                CREATE TABLE "Course_Professor" (
                                    "CourseID" INTEGER NOT NULL,
                                    "ProfessorID" INTEGER NOT NULL,
                                    "SectionNumber" INTEGER DEFAULT 1,
                                    PRIMARY KEY ("CourseID", "ProfessorID", "SectionNumber"),
                                    FOREIGN KEY ("CourseID") REFERENCES "Courses" ("CourseID"),
                                    FOREIGN KEY ("ProfessorID") REFERENCES "Users" ("UserID")
                                )
                            '''))
                            
                            # Restore relationships with default section 1
                            for course_id, professor_id in existing_relationships:
                                session.execute(text('''
                                    INSERT INTO "Course_Professor" ("CourseID", "ProfessorID", "SectionNumber")
                                    VALUES (:course_id, :professor_id, 1)
                                '''), {'course_id': course_id, 'professor_id': professor_id})
                            
                            session.commit()
                            logger.info("Successfully recreated Course_Professor table with SectionNumber")
                        except SQLAlchemyError as e2:
                            session.rollback()
                            logger.error(f"Failed to recreate table: {e2}")
                            raise
            else:
                # Table doesn't exist, create it with correct schema
                logger.info("Creating Course_Professor table with new schema")
                try:
                    session.execute(text('''
                        CREATE TABLE "Course_Professor" (
                            "CourseID" INTEGER NOT NULL,
                            "ProfessorID" INTEGER NOT NULL,
                            "SectionNumber" INTEGER DEFAULT 1,
                            PRIMARY KEY ("CourseID", "ProfessorID", "SectionNumber"),
                            FOREIGN KEY ("CourseID") REFERENCES "Courses" ("CourseID"),
                            FOREIGN KEY ("ProfessorID") REFERENCES "Users" ("UserID")
                        )
                    '''))
                    session.commit()
                    logger.info("Successfully created Course_Professor table with SectionNumber")
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Failed to create Course_Professor table: {e}")
                    raise
            
            # Check if other necessary columns exist and add them if needed
            try:
                session.execute(text('SELECT "NumberOfSections" FROM "Courses" LIMIT 1'))
                logger.info("NumberOfSections column already exists in Courses")
            except SQLAlchemyError:
                session.rollback()
                logger.info("Adding NumberOfSections column to Courses table")
                try:
                    session.execute(text('ALTER TABLE "Courses" ADD COLUMN "NumberOfSections" INTEGER DEFAULT 1'))
                    session.commit()
                    logger.info("Successfully added NumberOfSections column to Courses")
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Failed to add NumberOfSections column: {e}")
                    raise
            
            try:
                session.execute(text('SELECT "SectionNumber" FROM "Course_Stud" LIMIT 1'))
                logger.info("SectionNumber column already exists in Course_Stud")
            except SQLAlchemyError:
                session.rollback()
                logger.info("Adding SectionNumber column to Course_Stud table")
                try:
                    session.execute(text('ALTER TABLE "Course_Stud" ADD COLUMN "SectionNumber" INTEGER DEFAULT 1'))
                    session.commit()
                    logger.info("Successfully added SectionNumber column to Course_Stud")
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Failed to add SectionNumber column to Course_Stud: {e}")
                    raise
        
        logger.info("PostgreSQL migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during PostgreSQL migration: {e}")
        raise


def check_migration_needed(db_path):
    """
    Check if database migration is needed.
    Only applies to SQLite databases - PostgreSQL schemas are created fresh.
    
    :param db_path: Path to the database file or schema identifier
    :return: True if migration is needed, False otherwise
    """
    # For PostgreSQL, check if migration is needed
    if is_postgresql():
        return check_postgresql_migration_needed(db_path)
    
    try:
        with get_db_session(db_path) as session:
            # Check if SectionNumber column exists in Course_Stud
            try:
                session.execute(text("SELECT SectionNumber FROM Course_Stud LIMIT 1"))
            except Exception:
                logger.info("Migration needed: Course_Stud.SectionNumber column missing")
                return True
            
            # Check if SectionNumber column exists in Course_Professor
            try:
                session.execute(text("SELECT SectionNumber FROM Course_Professor LIMIT 1"))
            except Exception:
                logger.info("Migration needed: Course_Professor.SectionNumber column missing")
                return True
            
            # Check if Schedule table has correct schema
            try:
                schedule_columns = session.execute(text("PRAGMA table_info(Schedule)")).fetchall()
                column_names = [col[1] for col in schedule_columns]
                
                if 'CourseID' not in column_names:
                    logger.info("Migration needed: Schedule table has incorrect schema")
                    return True
            except Exception:
                logger.info("Migration needed: Schedule table issues")
                return True
                
            return False  # Migration not needed
    except Exception:
        return True  # Migration needed


def check_postgresql_migration_needed(db_path):
    """
    Check if PostgreSQL schema needs migration.
    
    :param db_path: Schema identifier for PostgreSQL (e.g., "schema:org_myorg")
    :return: True if migration is needed, False otherwise
    """
    from .dbconnection import get_organization_database_url
    
    # Auto-detect org_name from db_path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    if not org_name:
        return False
    
    try:
        with get_db_session(get_organization_database_url(), org_name) as session:
            # Check if SectionNumber column exists in Course_Professor
            try:
                session.execute(text('SELECT "SectionNumber" FROM "Course_Professor" LIMIT 1'))
            except SQLAlchemyError:
                logger.info("Migration needed: Course_Professor.SectionNumber column missing")
                return True
            
            # Check if NumberOfSections column exists in Courses
            try:
                session.execute(text('SELECT "NumberOfSections" FROM "Courses" LIMIT 1'))
            except SQLAlchemyError:
                logger.info("Migration needed: Courses.NumberOfSections column missing")
                return True
            
            # Check if SectionNumber column exists in Course_Stud
            try:
                session.execute(text('SELECT "SectionNumber" FROM "Course_Stud" LIMIT 1'))
            except SQLAlchemyError:
                logger.info("Migration needed: Course_Stud.SectionNumber column missing")
                return True
                
            return False  # Migration not needed
    except Exception as e:
        logger.error(f"Error checking PostgreSQL migration status: {e}")
        return True  # Migration needed if we can't check 