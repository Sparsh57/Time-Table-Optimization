from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import os
import httpx
from fastapi.responses import FileResponse


from src.database_management.databse_connection import DatabaseConnection
from src.database_management.Users import insert_user_data
from src.database_management.Courses import insert_courses_professors
from src.database_management.busy_slot import insert_professor_busy_slots
from src.database_management.course_stud import insert_course_students
from src.database_management.schedule import timetable_made, fetch_schedule_data, generate_csv
from src.main_algorithm import gen_timetable
from src.database_management.truncate_db import truncate_detail

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

app = FastAPI()

# Middleware and static files configuration
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates configuration
templates = Jinja2Templates(directory="views")

class TimeSlot(BaseModel):
    days: list
    times: list

db_config = {'host': os.getenv("DATABASE_HOST"),
             'user': os.getenv("DATABASE_USER"),
             'port': os.getenv("DATABASE_PORT"),
             'password': os.getenv("DATABASE_PASSWORD"),
             'database': os.getenv("DATABASE_REF"),}

@app.post("/send_admin_data")
async def send_admin_data(
        courses_file: UploadFile = File(...),
        faculty_preferences_file: UploadFile = File(...),
        student_courses_file: UploadFile = File(...)
):
    truncate_detail(db_config)
    responses = {}
    files = {
        "courses_file": courses_file,
        "faculty_preferences_file": faculty_preferences_file,
        "student_courses_file": student_courses_file,
    }
    data = {}
    # Load valid dataframes
    for file_key, file in files.items():
        if file.filename.endswith(('.csv', '.xlsx')):
            data[file_key] = (
                pd.read_csv(file.file) if file.filename.endswith('.csv') else pd.read_excel(file.file)
            )
        else:
            responses[file.filename] = "Unsupported file format"

    files = {
        "insert_user_data": ([data["courses_file"], data["student_courses_file"]], insert_user_data),
        "courses_file": (data["courses_file"], insert_courses_professors),
        "faculty_preferences_file": (data["faculty_preferences_file"], insert_professor_busy_slots),
        "student_courses_file": (data["student_courses_file"], insert_course_students)
    }
    for file_key, (file, db_function) in files.items():
            try:
                db_function(file, db_config)
                responses[file_key] = "Data inserted successfully"
            except Exception as e:
                responses[file.filename] = str(e)
    gen_timetable()
    return RedirectResponse(url="/dashboard",status_code=status.HTTP_303_SEE_OTHER)

@app.get("/auth/google")
async def login_with_google():

    redirect_uri = "http://localhost:4000/auth/google/callback"
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code"
        f"&redirect_uri={redirect_uri}&scope=email profile openid"
    )

@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str):
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
    if user_info.get('email') in (os.getenv("ALLOWED_EMAILS")):
        request.session['user'] = user_info
        return RedirectResponse(url="/dashboard")
    else: 
        return templates.TemplateResponse("access_denied.html", {"request": request}, status_code=403)
    
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_info = request.session.get('user')
    if not user_info:
        return RedirectResponse(url="/")
    if timetable_made():
        return RedirectResponse(url="/timetable")
    else:
        return RedirectResponse(url="/get_admin_data")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/get_admin_data", response_class=HTMLResponse)
async def get_admin_data(request: Request):
    user_info = request.session.get('user')
    return templates.TemplateResponse("data_entry.html", {"request": request, "user": user_info})

@app.get("/timetable", response_class=HTMLResponse)
async def show_timetable(request: Request):
   
    user_info = request.session.get('user')
    if not user_info:
        return RedirectResponse(url="/") 
    if timetable_made(): 
        schedule_data = fetch_schedule_data()  
        return templates.TemplateResponse("timetable.html", {
            "request": request,
            "user": user_info,
            "schedule_data": schedule_data
        })
    else:
        return RedirectResponse(url="/get_admin_data") 

@app.get("/download-timetable")
async def download_schedule_csv():
    try:
        file_path = generate_csv()
        return FileResponse(file_path, media_type='application/octet-stream', filename="Timetable.csv")
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=4000)