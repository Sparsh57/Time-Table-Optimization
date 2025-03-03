import os
import sqlite3
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from dotenv import load_dotenv
import httpx
import pandas as pd
from io import BytesIO
import uvicorn

# -------------------- Import your local modules --------------------
# For demonstration, these are placeholders. Update them with your own modules.
from create_database_tables import get_or_create_org_database  # Make sure this creates a Users table with 'role'
from src.database_management.Users import insert_user_data, add_admin
from src.database_management.Courses import insert_courses_professors
from src.database_management.busy_slot import insert_professor_busy_slots
from src.database_management.course_stud import insert_course_students
from src.database_management.schedule import (
    timetable_made,
    fetch_schedule_data,
    generate_csv,
    get_student_schedule,
    generate_csv_for_student,
)
from src.database_management.Slot_info import insert_time_slots
from src.database_management.truncate_db import truncate_detail
from src.main_algorithm import gen_timetable

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

app = FastAPI()

# -------------------- Middleware and static files --------------------
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------- Templates --------------------
templates = Jinja2Templates(directory="views")


# -------------------- Utility / DB Helpers --------------------

def get_db_path_for_org(org_name: str) -> str:
    """
    Look up the organization's db_path from the meta-database (organizations_meta.db).
    """
    try:
        conn = sqlite3.connect("organizations_meta.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DatabasePath FROM Organizations WHERE OrgName = ?", (org_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        else:
            return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing meta-database: {e}")


def fetch_user_role_from_org_db(email: str, db_path: str) -> str:
    """
    Fetch the user's role from the organization's DB by email.
    Returns the role or 'Student' if not found.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM Users WHERE email=?", (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return row[0]
        else:
            # If user not in table, you might default them to 'Student'
            return "Student"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching user role: {exc}")


# -------------------- Role Check Helpers --------------------

def is_admin(request: Request) -> bool:
    """
    Return True if the currently logged-in user is an Admin; else False.
    """
    user = request.session.get("user")
    if not user or user.get("role") != "Admin":
        return False
    return True


def require_admin(request: Request):
    """
    FastAPI dependency that raises 403 if the user is not Admin.
    Usage: pass as a dependency in a route, e.g.:
        @app.post("/some-route")
        async def some_func(..., user=Depends(require_admin)):
            ...
    """
    user = request.session.get("user")
    if not user or user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")
    return user


# -------------------- OAuth / Auth Endpoints --------------------

@app.get("/auth/google")
async def login_with_google():
    """
    Initiates Google sign-in by redirecting the user to Google's OAuth consent screen.
    """
    redirect_uri = "http://localhost:4000/auth/google/callback"
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code"
        f"&redirect_uri={redirect_uri}&scope=email profile openid"
    )


@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str):
    """
    Handles the Google OAuth callback. Retrieves user info, checks the email domain,
    finds the organization's db_path, fetches the user's role, and stores all in session.
    """
    redirect_uri = "http://localhost:4000/auth/google/callback"
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    # -- Exchange auth code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=data)
        tokens = token_response.json()
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_info_response = await client.get(
            user_info_url,
            headers={"Authorization": f"Bearer {tokens.get('access_token')}"}
        )
        user_info = user_info_response.json()

    user_email = user_info.get("email")
    org_found = None
    db_path = None

    # -- Check if user_email matches any org domains
    try:
        conn = sqlite3.connect("organizations_meta.db")
        cursor = conn.cursor()
        cursor.execute("SELECT OrgName, OrgDomains, DatabasePath FROM Organizations")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)}, status_code=500)

    for org_name, org_domains, path in rows:
        allowed_domains = [d.strip() for d in org_domains.split(",")]
        for domain in allowed_domains:
            if user_email.endswith("@" + domain):
                org_found = org_name
                db_path = path
                break
        if org_found:
            break

    if org_found and db_path:
        # -- Fetch the user's role from the org DB
        user_role = fetch_user_role_from_org_db(user_email, db_path)

        # -- Store in session
        request.session["user"] = {
            **user_info,
            "org": org_found,
            "role": user_role  # e.g., "Admin", "Student", etc.
        }
        request.session["db_path"] = db_path

        return RedirectResponse(url="/dashboard")
    else:
        # If no matching org found, direct user to register an organization
        request.session["user"] = user_info
        return RedirectResponse(url="/register-organization")


@app.get("/logout")
async def logout(request: Request):
    """
    Logs out the user by clearing the session and redirecting to the home page.
    """
    request.session.pop("user", None)
    request.session.pop("db_path", None)
    return RedirectResponse(url="/", status_code=302)


# -------------------- Organization Registration --------------------

@app.get("/register-organization", response_class=HTMLResponse)
async def show_register_organization(request: Request):
    """
    Renders the organization registration page.
    """
    user_info = request.session.get("user")
    if not user_info:
        return RedirectResponse(url="/home")
    return templates.TemplateResponse("register_organization.html", {"request": request, "user": user_info})


@app.post("/register-organization")
async def register_organization(
        request: Request,
        email: str = Form(...),
        domain: str = Form(...),
        org_name: str = Form(...),
        allowed_domains: str = Form(...),
        user_name: str = Form(...)
):
    """
    Processes the organization registration form. Creates the org DB if needed,
    adds the registering user as Admin, updates session with the new db_path.
    """
    try:
        allowed_domains_list = [d.strip() for d in allowed_domains.split(",")]
        # Compute the organization's database path based on the org_name
        db_path = os.path.join(os.getcwd(), "data", f"{org_name.replace(' ', '_')}.db")

        # Create or get the org DB (make sure it has a 'role' column in the Users table)
        get_or_create_org_database(org_name, allowed_domains_list)

        # Insert this user as an Admin in the org's DB
        add_admin(
            user_name=user_name,
            email=email,
            role="Admin",
            db_path=db_path
        )

        # Update meta-database (organizations_meta.db) if needed, or ensure it's already done in get_or_create_org_database

        # Store in session
        request.session["db_path"] = db_path
        request.session["user"] = {
            **request.session.get("user", {}),
            "org": org_name,
            "role": "Admin"
        }

        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)}, status_code=500)


# -------------------- Admin-Only Data Insertion / Upload Endpoints --------------------

@app.post("/insert_timeslots")
async def insert_timeslots(request: Request, timeslot_data: dict):
    """
    Inserts time slots into the organization's database. Admin-only route.
    """
    # 1. Admin check
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    # 2. Proceed
    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        formatted_data = {}
        for day, slots in timeslot_data.items():
            formatted_data[day] = []
            for slot in slots:
                formatted_data[day].append([slot[0], slot[1]])
        insert_time_slots(formatted_data, db_path)
        return JSONResponse(status_code=200, content={"message": "Timeslots inserted successfully!"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/send_admin_data")
async def send_admin_data(
        request: Request,
        courses_file: UploadFile = File(...),
        faculty_preferences_file: UploadFile = File(...),
        student_courses_file: UploadFile = File(...)
):
    """
    Processes admin data uploads, inserts data, generates the timetable, redirects to the dashboard.
    Admin-only route.
    """
    # 1. Admin check
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    truncate_detail(db_path)
    responses = {}
    files = {
        "courses_file": courses_file,
        "faculty_preferences_file": faculty_preferences_file,
        "student_courses_file": student_courses_file,
    }

    data = {}

    # -- Load each file into a DataFrame
    for file_key, file in files.items():
        if file.filename.endswith('.csv'):
            data[file_key] = pd.read_csv(file.file)
        elif file.filename.endswith('.xlsx'):
            file_bytes = await file.read()
            data[file_key] = pd.read_excel(BytesIO(file_bytes))
        else:
            responses[file.filename] = "Unsupported file format"

    # -- Insert data into DB
    files_to_process = {
        "insert_user_data": ([data["courses_file"], data["student_courses_file"]], insert_user_data),
        "courses_file": (data["courses_file"], insert_courses_professors),
        "faculty_preferences_file": (data["faculty_preferences_file"], insert_professor_busy_slots),
        "student_courses_file": (data["student_courses_file"], insert_course_students)
    }

    for file_key, (file_data, db_function) in files_to_process.items():
        try:
            db_function(file_data, db_path)
            responses[file_key] = "Data inserted successfully"
        except Exception as e:
            responses[file_key] = str(e)

    # -- Generate timetable
    gen_timetable(db_path)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# -------------------- Page Endpoints --------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ Renders the home page. """
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """ Alternative home page route. """
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/select_timeslot")
async def select_timeslot(request: Request):
    """
    Renders the page for selecting time slots. Admin-only.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    return templates.TemplateResponse("select_timeslots.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Dashboard redirection logic:
      - If admin and timetable exists -> /timetable
      - If admin and no timetable -> /get_admin_data
      - If NOT admin -> show their personal schedule (assuming roll_number is known)
                       or redirect to appropriate page if no timetable is generated.
    """
    user_info = request.session.get("user")
    db_path = request.session.get("db_path")
    if not user_info or not db_path:
        return RedirectResponse(url="/")

    user_role = user_info.get("role")

    if user_role == "Admin":
        # Admin logic
        if timetable_made(db_path):
            return RedirectResponse(url="/timetable")
        else:
            return RedirectResponse(url="/get_admin_data")
    else:
        # Non-admin logic (e.g., a Student)
        if not timetable_made(db_path):
            # If no timetable is generated yet, user can’t see schedule
            # Just redirect them home or show a message
            return RedirectResponse(url="/home")

        # If you store the student’s roll_number in session or DB, retrieve it:
        # (Below is just an example if you have user_info["roll_number"])
        roll_number = user_info.get("roll_number")
        if not roll_number:
            # If for some reason you don't store roll_number in session,
            # you might ask them to enter it or handle differently
            return RedirectResponse(url="/get_role_no")

        # Show the student's personal schedule
        return RedirectResponse(url=f"/timetable/{roll_number}")


@app.get("/get_role_no", response_class=HTMLResponse)
async def get_role_no(request: Request):
    """
    Renders a page to let user input their roll number (if you need this logic).
    """
    return templates.TemplateResponse("get_role_number.html", {"request": request})


@app.get("/get_admin_data", response_class=HTMLResponse)
async def get_admin_data(request: Request):
    """
    Renders the admin data entry page. Admin-only.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    user_info = request.session.get("user")
    db_path = request.session.get("db_path")
    if not user_info or not db_path:
        return RedirectResponse(url="/home")
    return templates.TemplateResponse("data_entry.html", {"request": request, "user": user_info, "db_path": db_path})


@app.get("/timetable", response_class=HTMLResponse)
async def show_timetable(request: Request):
    """
    Renders the overall timetable page if an admin is logged in and the timetable is generated.
    Non-admin: you can choose to forbid or show a different view.
    """
    user_info = request.session.get("user")
    db_path = request.session.get("db_path")
    if not user_info or not db_path:
        return RedirectResponse(url="/home")

    # Optionally, require admin for the overall timetable page:
    if not is_admin(request):
        # If you want to let non-admin see only their own schedule, redirect them:
        roll_number = user_info.get("roll_number")
        return RedirectResponse(url=f"/timetable/{roll_number}")

    # Admin path
    if timetable_made(db_path):
        schedule_data = fetch_schedule_data(db_path)
        return templates.TemplateResponse(
            "timetable.html",
            {
                "request": request,
                "user": user_info,
                "schedule_data": schedule_data
            }
        )
    else:
        return RedirectResponse(url="/get_admin_data")


# -------------------- Schedule Download / View --------------------

@app.get("/download-timetable")
async def download_schedule_csv(request: Request):
    """
    Provides a CSV download of the entire timetable. Admin-only.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")
    try:
        file_path = generate_csv(db_path)
        return FileResponse(file_path, media_type="application/octet-stream", filename="Timetable.csv")
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})


@app.get("/download-timetable/{roll_number}")
async def download_student_schedule_csv(request: Request, roll_number: str):
    """
    Provides a CSV download of a single student's timetable.
    Optionally allow only if the user is the student or an admin.
    """
    user_info = request.session.get("user")
    if not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user_role = user_info.get("role")
    user_roll_in_session = user_info.get("roll_number")

    # If not admin, check that requested roll_number matches session roll_number
    if user_role != "Admin" and roll_number != user_roll_in_session:
        raise HTTPException(status_code=403, detail="You can only download your own schedule.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")
    try:
        file_path = generate_csv_for_student(roll_number, db_path)
        return FileResponse(file_path, media_type="application/octet-stream", filename=f"Timetable_{roll_number}.csv")
    except HTTPException as http_exc:
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/timetable/{roll_number}", response_class=HTMLResponse)
async def show_student_timetable(request: Request, roll_number: str):
    """
    Renders a specific student's timetable.
    If user is not admin, ensure they only access their own roll number schedule.
    """
    user_info = request.session.get("user")
    db_path = request.session.get("db_path")
    if not user_info or not db_path:
        return RedirectResponse(url="/home")

    user_role = user_info.get("role")
    user_roll_in_session = user_info.get("roll_number")

    # If not admin, ensure the roll_number matches the user's roll_number
    #if user_role != "Admin" and roll_number != user_roll_in_session:
    #    raise HTTPException(status_code=403, detail="Access forbidden: not your roll number.")

    schedule_data = get_student_schedule(roll_number, db_path)
    return templates.TemplateResponse(
        "student_timetable.html",
        {
            "request": request,
            "user": user_info,
            "schedule_data": schedule_data,
            "roll_number": roll_number
        }
    )


# -------------------- Main --------------------

if __name__ == "__main__":
    # Run with:  uvicorn main:app --reload  (or python main.py)
    uvicorn.run(app, host="localhost", port=4000)