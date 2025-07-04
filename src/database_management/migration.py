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
        
        # Also run Credits column migration if needed
        try:
            if check_credits_column_migration_needed(db_path):
                logger.info("SQLite Credits column migration needed...")
                migrate_column_rename_credits_to_classes_per_week(db_path)
                logger.info("SQLite Credits column migration completed")
        except Exception as e:
            logger.error(f"Error during SQLite Credits column migration: {e}")
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
        
        # Check if Credits column migration is needed
        try:
            if check_credits_column_migration_needed(db_path):
                logger.info("PostgreSQL Credits column migration needed...")
                migrate_postgresql_credits_column(db_path)
                logger.info("PostgreSQL Credits column migration completed")
        except Exception as e:
            logger.error(f"Error during PostgreSQL Credits column migration: {e}")
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
                
            # Also check if Credits column migration is needed
            if check_credits_column_migration_needed(db_path):
                logger.info("Migration needed: Credits column needs to be renamed to ClassesPerWeek")
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
            
            # Also check if Credits column migration is needed
            if check_credits_column_migration_needed(db_path):
                logger.info("Migration needed: Credits column needs to be renamed to ClassesPerWeek")
                return True
                
            return False  # Migration not needed
    except Exception as e:
        logger.error(f"Error checking PostgreSQL migration status: {e}")
        return True  # Migration needed if we can't check


def migrate_column_rename_credits_to_classes_per_week(db_path):
    """
    Migrate database to rename Credits column to ClassesPerWeek in Courses table.
    Handles both SQLite and PostgreSQL databases.
    
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
        logger.info(f"Starting PostgreSQL column rename migration for schema: {db_path}")
        migrate_postgresql_credits_column(db_path)
        return
    
    logger.info(f"Starting SQLite column rename migration: Credits -> ClassesPerWeek")
    
    try:
        with get_db_session(db_path) as session:
            # Check if Credits column exists and ClassesPerWeek doesn't
            try:
                session.execute(text("SELECT Credits FROM Courses LIMIT 1"))
                credits_exists = True
            except Exception:
                credits_exists = False
            
            try:
                session.execute(text("SELECT ClassesPerWeek FROM Courses LIMIT 1"))
                classes_per_week_exists = True
            except Exception:
                classes_per_week_exists = False
            
            if credits_exists and not classes_per_week_exists:
                logger.info("Migrating Credits column to ClassesPerWeek in SQLite")
                
                # SQLite doesn't support column rename directly, so we need to recreate the table
                # First, backup existing data
                existing_courses = session.execute(text("SELECT * FROM Courses")).fetchall()
                
                # Get table schema to understand column order
                table_info = session.execute(text("PRAGMA table_info(Courses)")).fetchall()
                
                # Drop the old table
                session.execute(text("DROP TABLE Courses"))
                
                # Create new table with ClassesPerWeek instead of Credits
                session.execute(text("""
                    CREATE TABLE Courses (
                        CourseID INTEGER PRIMARY KEY AUTOINCREMENT,
                        CourseName VARCHAR(255) UNIQUE NOT NULL,
                        CourseType VARCHAR(50),
                        ClassesPerWeek INTEGER,
                        NumberOfSections INTEGER DEFAULT 1
                    )
                """))
                
                # Restore data with column rename
                for course in existing_courses:
                    # Map old columns to new columns
                    course_dict = dict(course._mapping) if hasattr(course, '_mapping') else dict(course)
                    
                    # Insert with new column name
                    session.execute(text("""
                        INSERT INTO Courses (CourseID, CourseName, CourseType, ClassesPerWeek, NumberOfSections)
                        VALUES (:course_id, :course_name, :course_type, :classes_per_week, :num_sections)
                    """), {
                        'course_id': course_dict.get('CourseID'),
                        'course_name': course_dict.get('CourseName'),
                        'course_type': course_dict.get('CourseType'),
                        'classes_per_week': course_dict.get('Credits'),  # Map Credits to ClassesPerWeek
                        'num_sections': course_dict.get('NumberOfSections', 1)
                    })
                
                session.commit()
                logger.info("Successfully migrated Credits column to ClassesPerWeek in SQLite")
                
            elif classes_per_week_exists:
                logger.info("ClassesPerWeek column already exists in Courses table")
            else:
                logger.info("No Credits column found, assuming fresh installation")
        
        logger.info("SQLite column rename migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during SQLite column rename migration: {e}")
        raise


def migrate_postgresql_credits_column(db_path):
    """
    Migrate PostgreSQL schema to rename Credits column to ClassesPerWeek.
    
    :param db_path: Schema identifier for PostgreSQL (e.g., "schema:org_myorg")
    :return: True if migration was successful, False otherwise
    """
    from .dbconnection import get_organization_database_url, create_database_engine
    from sqlalchemy.engine import Connection
    
    # Auto-detect org_name from db_path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    if not org_name:
        logger.error(f"Invalid PostgreSQL schema path: {db_path}")
        return False
    
    logger.info(f"Starting PostgreSQL Credits column migration for organization: {org_name}")
    
    # Use direct engine connection with autocommit for DDL
    engine = create_database_engine(get_organization_database_url())
    
    try:
        from .dbconnection import get_schema_for_organization
        schema_name = get_schema_for_organization(org_name)
        
        # Step 1: Check if migration is needed
        credits_exists = False
        classes_per_week_exists = False
        
        # Use autocommit connection for checks
        with engine.connect().execution_options(autocommit=True) as conn:
            # Set search path
            conn.execute(text(f"SET search_path TO {schema_name}, public"))
            
            # Check if Credits column exists
            try:
                result = conn.execute(text('SELECT "Credits" FROM "Courses" LIMIT 1'))
                result.fetchone()  # Try to fetch to trigger any errors
                credits_exists = True
                logger.info("Found Credits column in Courses table")
            except Exception as e:
                logger.info(f"Credits column not found: {e}")
                credits_exists = False
            
            # Check if ClassesPerWeek column exists
            try:
                result = conn.execute(text('SELECT "ClassesPerWeek" FROM "Courses" LIMIT 1'))
                result.fetchone()  # Try to fetch to trigger any errors
                classes_per_week_exists = True
                logger.info("Found ClassesPerWeek column in Courses table")
            except Exception as e:
                logger.info(f"ClassesPerWeek column not found: {e}")
                classes_per_week_exists = False
        
        # Step 2: Perform migration if needed
        if credits_exists and not classes_per_week_exists:
            logger.info("Migration needed: Renaming Credits column to ClassesPerWeek")
            
            # Use autocommit for DDL statements
            with engine.connect().execution_options(autocommit=True) as conn:
                # Set search path
                conn.execute(text(f"SET search_path TO {schema_name}, public"))
                
                # Execute DDL statement
                conn.execute(text('ALTER TABLE "Courses" RENAME COLUMN "Credits" TO "ClassesPerWeek"'))
                
                logger.info("Successfully renamed Credits column to ClassesPerWeek")
            
        elif classes_per_week_exists:
            logger.info("ClassesPerWeek column already exists - migration not needed")
        elif not credits_exists and not classes_per_week_exists:
            logger.info("No Courses table found - assuming fresh installation")
        else:
            logger.info("Database schema is up to date")
        
        logger.info("PostgreSQL Credits column migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during PostgreSQL Credits column migration: {e}")
        return False
    finally:
        engine.dispose()


def check_credits_column_migration_needed(db_path):
    """
    Check if Credits to ClassesPerWeek column migration is needed.
    
    :param db_path: Path to the database file or schema identifier
    :return: True if migration is needed, False otherwise
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix
    
    # For PostgreSQL, check PostgreSQL schema
    if is_postgresql():
        from .dbconnection import get_organization_database_url, create_database_engine, get_schema_for_organization
        
        if not org_name:
            return False
        
        engine = create_database_engine(get_organization_database_url())
        
        try:
            with engine.connect().execution_options(autocommit=True) as conn:
                # Set search path
                schema_name = get_schema_for_organization(org_name)
                conn.execute(text(f"SET search_path TO {schema_name}, public"))
                
                # Check if Credits column exists and ClassesPerWeek doesn't
                try:
                    result = conn.execute(text('SELECT "Credits" FROM "Courses" LIMIT 1'))
                    result.fetchone()  # Try to fetch to trigger any errors
                    credits_exists = True
                except Exception:
                    credits_exists = False
                
                try:
                    result = conn.execute(text('SELECT "ClassesPerWeek" FROM "Courses" LIMIT 1'))
                    result.fetchone()  # Try to fetch to trigger any errors
                    classes_per_week_exists = True
                except Exception:
                    classes_per_week_exists = False
                
                # Migration needed if Credits exists but ClassesPerWeek doesn't
                return credits_exists and not classes_per_week_exists
                
        except Exception as e:
            logger.error(f"Error checking PostgreSQL Credits column migration status: {e}")
            return False
        finally:
            engine.dispose()
    
    # For SQLite
    try:
        with get_db_session(db_path) as session:
            # Check if Credits column exists and ClassesPerWeek doesn't
            try:
                session.execute(text("SELECT Credits FROM Courses LIMIT 1"))
                credits_exists = True
            except Exception:
                credits_exists = False
            
            try:
                session.execute(text("SELECT ClassesPerWeek FROM Courses LIMIT 1"))
                classes_per_week_exists = True
            except Exception:
                classes_per_week_exists = False
            
            # Migration needed if Credits exists but ClassesPerWeek doesn't
            return credits_exists and not classes_per_week_exists
            
    except Exception as e:
        logger.error(f"Error checking Credits column migration status: {e}")
        return False 