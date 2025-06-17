from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
MetaBase = declarative_base()  # Separate base for meta-database


# Meta-database model (for organizations_meta.db)
class Organization(MetaBase):
    __tablename__ = 'Organizations'
    
    OrgID = Column(Integer, primary_key=True, autoincrement=True)
    OrgName = Column(String, unique=True, nullable=False)
    OrgDomains = Column(String, nullable=False)
    DatabasePath = Column(String, nullable=False)


# Organization database models
class User(Base):
    __tablename__ = 'Users'
    
    UserID = Column(Integer, primary_key=True, autoincrement=True)
    Email = Column(String, unique=True, nullable=False)
    Name = Column(String, nullable=False)
    Role = Column(String, nullable=False)  # Admin, Professor, Student
    CreatedByAdminID = Column(Integer, ForeignKey('Users.UserID'), nullable=True)  # Track who created this admin
    IsFounderAdmin = Column(Integer, default=0)  # 1 if this is the organization founder
    
    # Relationships
    taught_courses = relationship("CourseProfessor", back_populates="professor")
    enrolled_courses = relationship("CourseStud", back_populates="student")
    busy_slots = relationship("ProfessorBusySlot", back_populates="professor")
    
    __table_args__ = (
        UniqueConstraint('Email'),
    )


class Course(Base):
    __tablename__ = 'Courses'
    
    CourseID = Column(Integer, primary_key=True, autoincrement=True)
    CourseName = Column(String, unique=True, nullable=False)
    CourseType = Column(String)  # Elective, Required
    Credits = Column(Integer)
    NumberOfSections = Column(Integer, default=1)  # New column for section count
    
    # Relationships
    professors = relationship("CourseProfessor", back_populates="course")
    enrolled_students = relationship("CourseStud", back_populates="course")
    schedule_slots = relationship("Schedule", back_populates="course")


class CourseProfessor(Base):
    __tablename__ = 'Course_Professor'
    
    CourseID = Column(Integer, ForeignKey('Courses.CourseID'), primary_key=True)
    ProfessorID = Column(Integer, ForeignKey('Users.UserID'), primary_key=True)
    
    # Relationships
    course = relationship("Course", back_populates="professors")
    professor = relationship("User", back_populates="taught_courses")


class CourseStud(Base):
    __tablename__ = 'Course_Stud'
    
    CourseID = Column(Integer, ForeignKey('Courses.CourseID'), primary_key=True)
    StudentID = Column(Integer, ForeignKey('Users.UserID'), primary_key=True)
    SectionNumber = Column(Integer, default=1)  # New column for section assignment
    
    # Relationships
    course = relationship("Course", back_populates="enrolled_students")
    student = relationship("User", back_populates="enrolled_courses")
    
    __table_args__ = (
        UniqueConstraint('CourseID', 'StudentID'),  # One enrollment per student per course
    )


class Slot(Base):
    __tablename__ = 'Slots'
    
    SlotID = Column(Integer, primary_key=True, autoincrement=True)
    StartTime = Column(String, nullable=False)
    EndTime = Column(String, nullable=False)
    Day = Column(String, nullable=False)
    
    # Relationships
    busy_professors = relationship("ProfessorBusySlot", back_populates="slot")
    scheduled_courses = relationship("Schedule", back_populates="slot")
    
    __table_args__ = (
        UniqueConstraint('StartTime', 'EndTime', 'Day'),
    )


class ProfessorBusySlot(Base):
    __tablename__ = 'Professor_BusySlots'
    
    ProfessorID = Column(Integer, ForeignKey('Users.UserID'), primary_key=True)
    SlotID = Column(Integer, ForeignKey('Slots.SlotID'), primary_key=True)
    
    # Relationships
    professor = relationship("User", back_populates="busy_slots")
    slot = relationship("Slot", back_populates="busy_professors")


class Schedule(Base):
    __tablename__ = 'Schedule'
    
    CourseID = Column(Integer, ForeignKey('Courses.CourseID'), primary_key=True)
    SlotID = Column(Integer, ForeignKey('Slots.SlotID'), primary_key=True)
    SectionNumber = Column(Integer, primary_key=True, default=1)
    
    # Relationships
    course = relationship("Course", back_populates="schedule_slots")
    slot = relationship("Slot", back_populates="scheduled_courses")


class Settings(Base):
    __tablename__ = 'Settings'
    
    SettingID = Column(Integer, primary_key=True, autoincrement=True)
    SettingKey = Column(String, unique=True, nullable=False)
    SettingValue = Column(String, nullable=False)
    Description = Column(String)
    
    __table_args__ = (
        UniqueConstraint('SettingKey'),
    ) 