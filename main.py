import os
from fastapi import FastAPI, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
from dotenv import load_dotenv
from starlette.staticfiles import StaticFiles
import fastapi
from pydantic import BaseModel
from typing import List, Tuple
from database_management.Courses import insert_courses_professors
from database_management.busy_slot import insert_professor_busy_slots
from database_management.Slot_info import insert_time_slots
from database_management.course_stud import insert_course_students
from database_management.databse_connection import DatabaseConnection
from pathlib import Path


load_dotenv()
print(os.getenv("CLIENT_ID"))

# Initialize FastAPI
app = FastAPI()

# Serve static files like CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure session middleware
app.add_middleware(SessionMiddleware, secret_key="secret")

templates = Jinja2Templates(directory="views")


# Define the input data structure using Pydantic model
class TimeSlot(BaseModel):
    days: List[str]
    times: List[Tuple[str, str]]  # List of tuples (start_time, end_time)

db_config = {'host': "byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
             'user': "urao5yk0erbiklfr",
             'password': "tpgCmLhZdwPk8iAxzVMd",
             'database': "byfapocx02at8jbunymk"}

users = {}

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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/auth/google")
async def login_with_google():
    redirect_uri = "http://localhost:4000/auth/google/callback"
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&"
        f"client_id={os.getenv('CLIENT_ID')}&redirect_uri={redirect_uri}&"
        "scope=email profile"
    )
    return RedirectResponse(google_auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str, request: Request):
    token_url = "https://oauth2.googleapis.com/token"
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data={
            "code": code,
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uri": "http://localhost:4000/auth/google/callback",
            "grant_type": "authorization_code"
        })
        tokens = response.json()

    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    async with httpx.AsyncClient() as client:
        user_info_response = await client.get(user_info_url,
                                              headers={"Authorization": f"Bearer {tokens['access_token']}"})
        user_info = user_info_response.json()

    email = user_info["email"]
    users[email] = user_info

    request.session['user'] = email

    return RedirectResponse("/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_email = request.session.get('user')
    if user_email is None:
        return RedirectResponse("/")

    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "name": user_email})


@app.get("/timetable", response_class=HTMLResponse)
async def timetable(request: Request):
    data = {
        "Monday": ["08:30 to 10:30", "10:30 to 12:30", "14:30 to 16:30"],
        "Tuesday": ["08:30 to 10:30", "10:30 to 12:30", "14:30 to 16:30"]
    }
    user_email = request.session.get('user')
    return templates.TemplateResponse("timetable.html", {"request": request, "data": data, "user_email": user_email})


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=4000)
