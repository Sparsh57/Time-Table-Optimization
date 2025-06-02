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
    
    # Relationships
    taught_courses = relationship("Course", back_populates="professor")
    enrolled_courses = relationship("CourseStud", back_populates="student")
    busy_slots = relationship("ProfessorBusySlot", back_populates="professor")
    
    __table_args__ = (
        UniqueConstraint('Email'),
    )


class Course(Base):
    __tablename__ = 'Courses'
    
    CourseID = Column(Integer, primary_key=True, autoincrement=True)
    CourseName = Column(String, unique=True, nullable=False)
    ProfessorID = Column(Integer, ForeignKey('Users.UserID'))
    CourseType = Column(String)  # Elective, Required
    Credits = Column(Integer)
    
    # Relationships
    professor = relationship("User", back_populates="taught_courses")
    enrolled_students = relationship("CourseStud", back_populates="course")
    schedule_slots = relationship("Schedule", back_populates="course")


class CourseStud(Base):
    __tablename__ = 'Course_Stud'
    
    CourseID = Column(Integer, ForeignKey('Courses.CourseID'), primary_key=True)
    StudentID = Column(Integer, ForeignKey('Users.UserID'), primary_key=True)
    
    # Relationships
    course = relationship("Course", back_populates="enrolled_students")
    student = relationship("User", back_populates="enrolled_courses")


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
    
    # Relationships
    course = relationship("Course", back_populates="schedule_slots")
    slot = relationship("Slot", back_populates="scheduled_courses") 