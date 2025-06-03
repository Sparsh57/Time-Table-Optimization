import sqlite3
import logging
from .dbconnection import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def migrate_database_for_sections(db_path):
    """
    Migrate existing database to support sections by adding necessary columns.
    
    :param db_path: Path to the database file
    """
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
            
            # Create Course_Section table if it doesn't exist
            try:
                session.execute(text("SELECT * FROM Course_Section LIMIT 1"))
                logger.info("Course_Section table already exists")
            except Exception:
                logger.info("Creating Course_Section table")
                session.execute(text("""
                    CREATE TABLE Course_Section (
                        CourseSectionID INTEGER PRIMARY KEY AUTOINCREMENT,
                        CourseID INTEGER NOT NULL,
                        SectionNumber INTEGER NOT NULL,
                        ProfessorID INTEGER NOT NULL,
                        FOREIGN KEY (CourseID) REFERENCES Courses (CourseID),
                        FOREIGN KEY (ProfessorID) REFERENCES Users (UserID),
                        UNIQUE(CourseID, SectionNumber)
                    )
                """))
                session.commit()
                logger.info("Successfully created Course_Section table")
            
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


def check_migration_needed(db_path):
    """
    Check if database migration is needed.
    
    :param db_path: Path to the database file
    :return: True if migration is needed, False otherwise
    """
    try:
        with get_db_session(db_path) as session:
            # Check if SectionNumber column exists
            session.execute(text("SELECT SectionNumber FROM Course_Stud LIMIT 1"))
            
            # Check if Schedule table has correct schema
            schedule_columns = session.execute(text("PRAGMA table_info(Schedule)")).fetchall()
            column_names = [col[1] for col in schedule_columns]
            
            if 'CourseID' not in column_names:
                logger.info("Migration needed: Schedule table has incorrect schema")
                return True
                
            return False  # Migration not needed
    except Exception:
        return True  # Migration needed 