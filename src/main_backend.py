import fastapi
from pydantic import BaseModel
from typing import List, Tuple
from .database_management.Courses import insert_courses_professors
from .database_management.busy_slot import insert_professor_busy_slots
from .database_management.Slot_info import insert_time_slots
from .database_management.course_stud import insert_course_students
from .database_management.databse_connection import DatabaseConnection
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from pathlib import Path
import os

app = fastapi.FastAPI()


# Define the input data structure using Pydantic model
class TimeSlot(BaseModel):
    days: List[str]
    times: List[Tuple[str, str]]  # List of tuples (start_time, end_time)


db_config = {'host': "byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
             'user': "urao5yk0erbiklfr",
             'password': "tpgCmLhZdwPk8iAxzVMd",
             'database': "byfapocx02at8jbunymk"}


@app.post("/time_info/")
def insert_time(time_info: TimeSlot):
    """
    API endpoint to insert time slots into the database.
    Calls the existing insert_time_slots function.
    """
    # Convert the Pydantic model to dictionary format
    input_data = {
        "days": time_info.days,
        "times": time_info.times
    }
    # Call the existing insert_time_slots function
    insert_time_slots(db_config, input_data)

    return {"status": "success", "message": "Time slots inserted successfully!"}


@app.get("/time_info/")
def extract_time():
    """
    API endpoint to extract time slots from the database.
    Returns a list of time slots with start time, end time, and day.
    """
    # Initialize the database connection
    mydb = DatabaseConnection(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"]
    )
    mydb.connect()  # Connect to the database

    # Query to fetch time slots from the database
    query = "SELECT StartTime, EndTime, Day FROM Slots"

    try:
        # Execute the query
        results = mydb.fetch_query(query)

        # Process the results into a list of dictionaries
        time_slots = []
        for row in results:
            time_slots.append({
                "start_time": row[0],
                "end_time": row[1],
                "day": row[2]
            })

        # Return the list of time slots as a JSON response
        return {"status": "success", "time_slots": time_slots}

    except Exception as e:
        # Handle any errors during the database query
        return {"status": "error", "message": str(e)}

    finally:
        # Close the database connection
        mydb.close()

@app.post("/course_data/")
def course(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv') or file.filename.endswith('.xlsx'):
        return JSONResponse(content={"error": "Only csv or excel files are allowed."})
    insert_courses_professors(file.file, db_config)
    return JSONResponse(content={"success": "Inserted"})

@app.post('/faculty_preference/')
def faculty_pref(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv') or file.filename.endswith('.xlsx'):
        return JSONResponse(content={"error": "Only csv or excel files are allowed."})
    insert_professor_busy_slots(file.file, db_config)
    return JSONResponse(content={"success": "Inserted"})

@app.post('/student_courses/')
def student_course(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv') or file.filename.endswith('.xlsx'):
        return JSONResponse(content={"error": "Only csv or excel files are allowed."})
    insert_course_students(file.file, db_config)
    return JSONResponse(content={"success": "Inserted"})
