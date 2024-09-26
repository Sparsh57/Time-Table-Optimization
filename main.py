from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import os
import httpx

from database_management.Courses import insert_courses_professors
from database_management.busy_slot import insert_professor_busy_slots
from database_management.course_stud import insert_course_students
from database_management.databse_connection import DatabaseConnection

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Middleware and static files configuration
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates configuration
templates = Jinja2Templates(directory="views")

class TimeSlot(BaseModel):
    days: list
    times: list

db_config = {'host': "byfapocx02at8jbunymk-mysql.services.clever-cloud.com",
             'user': "urao5yk0erbiklfr",
             'password': "tpgCmLhZdwPk8iAxzVMd",
             'database': "byfapocx02at8jbunymk"}

@app.post("/send_admin_data")
async def send_admin_data(
    courses_file: UploadFile = File(...),
    faculty_preferences_file: UploadFile = File(...),
    student_courses_file: UploadFile = File(...)
):
    responses = {}
    files = {
        "courses_file": (courses_file.file, insert_courses_professors),
        "faculty_preferences_file": (faculty_preferences_file.file, insert_professor_busy_slots),
        "student_courses_file": (student_courses_file.file, insert_course_students)
    }

    for file_key, (file, db_function) in files.items():
        if file.filename.endswith('.csv') or file.filename.endswith('.xlsx'):
            df = pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
            try:
                db_function(df, db_config)
                responses[file.filename] = "Data inserted successfully"
            except Exception as e:
                responses[file.filename] = str(e)
        else:
            responses[file.filename] = "Unsupported file format"

    return JSONResponse(content=responses)

@app.get("/auth/google")
async def login_with_google():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = "http://localhost:4000/auth/google/callback"
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code"
        f"&redirect_uri={redirect_uri}&scope=email profile openid"
    )

@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = "http://localhost:4000/auth/google/callback"
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        tokens = response.json()
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_info_response = await client.get(user_info_url, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        user_info = user_info_response.json()

    request.session['user'] = user_info
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_info = request.session.get('user')
    if not user_info:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user_info})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=4000)
