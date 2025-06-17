import os
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, status, Depends, Form, Body
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from dotenv import load_dotenv
import httpx
import pandas as pd
from io import BytesIO
import uvicorn
import json
from typing import Optional
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from collections import defaultdict
from typing import List

# -------------------- Importing your local modules --------------------
from create_database_tables import get_or_create_org_database, init_meta_database
from src.database_management.Users import insert_user_data, add_admin, fetch_user_data,fetch_professor_emails, fetch_admin_emails
from src.database_management.Courses import insert_courses_professors
from src.database_management.busy_slot import insert_professor_busy_slots, insert_professor_busy_slots_from_ui,fetch_user_id
from src.database_management.course_stud import insert_course_students
from src.database_management.Slot_info import fetch_slots
from src.database_management.schedule import (
    timetable_made,
    fetch_schedule_data,
    generate_csv,
    get_student_schedule,
    generate_csv_for_student,
)
from src.database_management.course_stud import (
    get_section_mapping_dataframe,
    print_section_summary
)
from src.database_management.section_allocation import (
    get_section_allocation_summary,
    export_section_mapping_to_csv
)
from src.database_management.Slot_info import insert_time_slots
from src.database_management.truncate_db import truncate_detail
from src.main_algorithm import gen_timetable_auto
from src.database_management.dbconnection import (
    get_organization_by_domain, 
    get_organization_by_name, 
    get_db_session,
    create_tables
)
from src.database_management.models import User
from src.database_management.admin_manager import (
    add_admin_user,
    remove_admin_user,
    get_all_admins,
    is_user_admin,
    ensure_first_admin,
    get_admin_count,
    can_remove_admin
)
from src.database_management.settings_manager import (
    get_max_classes_per_slot,
    set_max_classes_per_slot,
    initialize_default_settings,
    get_all_settings
)
from src.database_management.organization_manager import (
    validate_organization_creation,
    get_user_organization,
    should_redirect_to_registration,
    create_organization_with_validation,
    check_domain_availability
)
from sqlalchemy import text

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

app = FastAPI()

# -------------------- Initialize meta-database on startup --------------------
@app.on_event("startup")
async def startup_event():
    """Initialize the meta-database only if it does not already exist."""
    try:
        meta_db_path = "organizations_meta.db"
        if not os.path.exists(meta_db_path):
            init_meta_database()
            logger.info("Meta-database initialized successfully")
        else:
            logger.info("Meta-database already exists, skipping initialization")
    except Exception as e:
        logger.error(f"Failed to initialize meta-database: {e}")

# -------------------- Middleware and static files --------------------
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------- Templates --------------------
templates = Jinja2Templates(directory="views")


# -------------------- Utility / DB Helpers --------------------
def get_db_path_for_org(org_name: str) -> str:
    """
    Look up the organization's db_path from the meta-database using SQLAlchemy.
    """
    try:
        org = get_organization_by_name(org_name)
        if org:
            return org.DatabasePath
        else:
            return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing meta-database: {e}")


def fetch_user_role_from_org_db(email: str, db_path: str, user_name: str = None) -> str:
    """
    Fetch the user's role from the organization's DB by email using SQLAlchemy.
    If user doesn't exist, creates them as a Student.
    Returns the role.
    
    This function is the key fix for the production issue where users were missing from the database.
    """
    try:
        # First, ensure tables exist
        try:
            with get_db_session(db_path) as session:
                # Check if Users table exists by querying it
                session.execute(text("SELECT 1 FROM Users LIMIT 1"))
                logger.info(f"✅ Users table exists at {db_path}")
        except Exception as e:
            # If table doesn't exist, create all tables
            logger.info(f"🔧 Users table not found at {db_path}, creating tables...")
            create_tables(db_path)
            logger.info(f"✅ Tables created successfully at {db_path}")
        
        # Now proceed with user lookup/creation
        with get_db_session(db_path) as session:
            user = session.query(User).filter_by(Email=email).first()
            if user:
                logger.info(f"✅ Found existing user: {email} with role: {user.Role}")
                return user.Role
            else:
                # User doesn't exist, create them as Student
                logger.info(f"👤 User {email} not found, creating as Student...")
                
                # Use provided name or derive from email
                display_name = user_name or email.split('@')[0]
                
                new_user = User(
                    Name=display_name,
                    Email=email,
                    Role='Student',
                    CreatedByAdminID=None,
                    IsFounderAdmin=0
                )
                session.add(new_user)
                session.commit()
                
                logger.info(f"✅ Successfully created new Student user: {email} (Name: {display_name})")
                return "Student"
                
    except Exception as exc:
        logger.error(f"❌ Critical error in fetch_user_role_from_org_db for {email}: {exc}")
        logger.error(f"   Database path: {db_path}")
        logger.error(f"   User name: {user_name}")
        raise HTTPException(status_code=500, detail=f"Error fetching/creating user: {exc}")


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
async def login_with_google(request: Request):
    # Use environment variable for base URL or derive from request
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip('/'))
    redirect_uri = f"{base_url}/auth/google/callback"
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code"
        f"&redirect_uri={redirect_uri}&scope=email profile openid"
    )


@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str):
    # Use environment variable for base URL or derive from request
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip('/'))
    redirect_uri = f"{base_url}/auth/google/callback"
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
    user_name = user_info.get("name")

    # -- Check if user belongs to an existing organization using new validation
    try:
        # Ensure meta-database is initialized
        init_meta_database()
        
        # Find organization by email domain using new organization manager
        org = get_user_organization(user_email)
        if org:
            logger.info(f"User {user_email} belongs to organization: {org.OrgName}")
            
            # Fetch user role from the organization's database (creating user if needed)
            user_role = fetch_user_role_from_org_db(user_email, org.DatabasePath, user_name)
            
            # Store complete user info in session
            request.session["user"] = {
                "email": user_email,
                "name": user_name,
                "picture": user_info.get("picture"),
                "org": org.OrgName,
                "role": user_role,
                "roll_number": user_email  # Use email as roll number
            }
            request.session["db_path"] = org.DatabasePath
            request.session["org_name"] = org.OrgName

            logger.info(f"User {user_email} authenticated with role: {user_role}")
            return RedirectResponse(url="/dashboard")
        else:
            logger.info(f"No organization found for user {user_email}")
            
            # Store basic user info for potential registration
            request.session["user"] = {
                "email": user_email,
                "name": user_name,
                "picture": user_info.get("picture")
            }
            
            # User does not belong to any organization -> redirect to registration
            return RedirectResponse(url="/register-organization")
            
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return JSONResponse(
            status_code=500, 
            content={"error": f"Authentication error: {str(e)}"}
        )


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
        user_name: str = Form(...),
        max_classes_per_slot: int = Form(24)
):
    """
    Processes the organization registration form with comprehensive validation.
    Prevents duplicate organizations and domain conflicts.
    """
    try:
        # Validate organization creation using new validation system
        is_valid, validation_message = validate_organization_creation(org_name, allowed_domains, email)
        
        if not is_valid:
            # Return to registration form with error
            user_info = request.session.get("user", {})
            return templates.TemplateResponse(
                "register_organization.html", 
                {
                    "request": request, 
                    "user": user_info,
                    "error": validation_message,
                    "org_name": org_name,
                    "allowed_domains": allowed_domains,
                    "user_name": user_name
                }
            )

        # Compute the organization's database path
        db_path = os.path.join(os.getcwd(), "data", f"{org_name.replace(' ', '_')}.db")

        # Create organization with validation
        success, message, org = create_organization_with_validation(
            org_name, allowed_domains, email, user_name, db_path, max_classes_per_slot
        )

        if not success:
            user_info = request.session.get("user", {})
            return templates.TemplateResponse(
                "register_organization.html", 
                {
                    "request": request, 
                    "user": user_info,
                    "error": message,
                    "org_name": org_name,
                    "allowed_domains": allowed_domains,
                    "user_name": user_name
                }
            )

        # Update session with organization info
        request.session["db_path"] = db_path
        request.session["org_name"] = org_name
        request.session["user"] = {
            **request.session.get("user", {}),
            "org": org_name,
            "role": "Admin",
            "roll_number": email
        }

        logger.info(f"Successfully created organization '{org_name}' with admin '{email}'")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        logger.error(f"Error in organization registration: {e}")
        user_info = request.session.get("user", {})
        return templates.TemplateResponse(
            "register_organization.html", 
            {
                "request": request, 
                "user": user_info,
                "error": f"Registration failed: {str(e)}",
                "org_name": org_name,
                "allowed_domains": allowed_domains,
                "user_name": user_name
            }
        )


# -------------------- Admin-Only Data Insertion / Upload Endpoints --------------------
@app.post("/send_admin_data")
async def send_admin_data(
        request: Request,
        courses_file: UploadFile = File(...),
        faculty_preferences_file: UploadFile = File(...),
        student_courses_file: UploadFile = File(...),
        column_mappings: Optional[str] = Form(None), 
        toggle_prof: bool = Form(True),
        toggle_capacity: bool = Form(True), 
        toggle_student: bool = Form(True), 
        toggle_same_day: bool = Form(True),
        toggle_consec_days: bool = Form(False),
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
    gen_timetable_auto(
        db_path,
        add_prof_constraints    = toggle_prof,
        add_timeslot_capacity   = toggle_capacity,
        add_student_conflicts   = toggle_student,
        add_no_same_day         = toggle_same_day,
        add_no_consec_days      = toggle_consec_days)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# -------------------- Page Endpoints --------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ Renders the home page. """
    user_info = request.session.get("user")
    return templates.TemplateResponse("home.html", {"request": request, "user": user_info})


@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """ Alternative home page route. """
    user_info = request.session.get("user")
    return templates.TemplateResponse("home.html", {"request": request, "user": user_info})


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
            if fetch_slots(db_path) == []:
                return RedirectResponse(url="/select_timeslot")
            else:
                return RedirectResponse(url="/get_admin_data")
    else:
        if user_role == "Professor":
            return RedirectResponse(url="/professor_slots")
        else:
            # Non-admin logic (e.g., a Student)
            if not timetable_made(db_path):
                # If no timetable is generated yet, user can't see schedule
                # Just redirect them home or show a message
                return RedirectResponse(url="/home")

            # If you store the student's roll_number in session or DB, retrieve it:
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
        
        # Get section mapping data
        section_mapping_df = get_section_mapping_dataframe(db_path)
        section_summary = get_section_allocation_summary(db_path)
        
        # Process section mapping for template
        section_mapping_data = {}
        if not section_mapping_df.empty:
            # Group by course and section
            for course in section_mapping_df['Course'].unique():
                course_data = section_mapping_df[section_mapping_df['Course'] == course]
                if course_data['NumberOfSections'].iloc[0] > 1:  # Only multi-section courses
                    section_mapping_data[course] = {}
                    for section_num in sorted(course_data['SectionNumber'].unique()):
                        section_students = course_data[course_data['SectionNumber'] == section_num]
                        students_list = []
                        for _, student in section_students.iterrows():
                            students_list.append({
                                'roll_no': student['Roll_No'],
                                'name': student['Student_Name'] if student['Student_Name'] != student['Roll_No'] else 'N/A'
                            })
                        section_mapping_data[course][section_num] = {
                            'students': students_list,
                            'count': len(students_list)
                        }
        
        return templates.TemplateResponse(
            "timetable.html",
            {
                "request": request,
                "user": user_info,
                "schedule_data": schedule_data,
                "section_mapping_data": section_mapping_data,
                "section_summary": section_summary
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


@app.get("/download-section-mapping")
async def download_section_mapping_csv(request: Request):
    """
    Provides a CSV download of the student-section mapping. Admin-only.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")
    try:
        file_path = export_section_mapping_to_csv(db_path)
        if file_path:
            return FileResponse(file_path, media_type="application/octet-stream", filename="Section_Mapping.csv")
        else:
            return JSONResponse(status_code=404, content={"detail": "No section mapping data found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


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

@app.get("/get_timeslots")
async def get_timeslots(request: Request):
    """Fetch existing time slots for the organization."""
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        slots = fetch_slots(db_path)
        slots_by_day = defaultdict(list)
        for _, day, start, end in slots:
            slots_by_day[day].append([start, end])
        return JSONResponse(status_code=200, content=slots_by_day)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

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

    schedule_data = get_student_schedule(roll_number, db_path)
    print("Schedule Data:", schedule_data)  # Add this line for debugging
    return templates.TemplateResponse(
        "student_timetable.html",
        {
            "request": request,
            "user": user_info,
            "schedule_data": schedule_data,
            "roll_number": roll_number
        }
    )



@app.post("/upload/")
async def upload_csv(file_type: str = Form(...), file: UploadFile = File(...)):
    """
    Single-file preview route.
    Returns:
      - preview: first 5 rows as JSON,
      - missing_cols: list of expected columns missing,
      - extra_cols: list of columns in CSV not expected,
      - error: error message if any required columns are missing.
    """
    try:
        content = await file.read()
        df = pd.read_csv(BytesIO(content))
        PREVIEW_COLUMNS = {
            "courses": ["Course code", "Faculty Name", "Type","Credits", "Number of Sections"],
            "students":  ["Roll No.", "G CODE", "Sections"],
            "faculty": ["Name", "Busy Slot"]
        }
        expected_cols = PREVIEW_COLUMNS.get(file_type, [])
    
        #Alternatively, if you're sure about formatting, you could simply use:
        missing_cols = [c for c in expected_cols if c not in df.columns];
        extra_cols = [c for c in df.columns if c not in expected_cols];

        response = {
            "preview": df.head(5).to_dict(orient="records"),
            "missing_cols": missing_cols,
            "extra_cols": extra_cols
        }
        if (len(missing_cols) > 0):
            response["error"] = "Missing required columns: " + ", ".join(missing_cols)
        return response
    except Exception as e:
        return {"error": str(e)}

@app.post("/map-columns")
async def map_columns(mapping: dict = Body(...)):
    """
    Receives column mapping from the user.
    For now, simply returns the mapping.
    """
    return {"message": "Column mapping received", "mapping": mapping}


@app.get("/professor_slots")
async def choose_busy_slots(request: Request):
    logger.debug("here")
    user_info = request.session.get("user")
    email = user_info.get("email")
    db_path = request.session.get("db_path")
    prof_email_list = fetch_professor_emails(db_path)
    admin_email_list = fetch_admin_emails(db_path)
    if (email in prof_email_list) or (email in admin_email_list):
        slots = fetch_slots(db_path)
        slots_by_day = defaultdict(list)
        for slot in slots:
            slots_by_day[slot[1]].append({
                "SlotID": slot[0],
                "StartTime": slot[2],
                "EndTime": slot[3]
            })
        return templates.TemplateResponse("prof_busy_slot_selection.html", {"request": request, "slots_by_day": slots_by_day})
    else:
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

@app.post("/submit_slots")
async def submit_slots(request: Request, slots: List[int] = Form(...), status: List[str] = Form(...)):
    db_path = request.session.get("db_path")
    user_info = request.session.get("user")
    professor_id = fetch_user_id(user_info.get("email"), db_path)
    if professor_id:
        busy_slots = [slot for slot, stat in zip(slots, status) if stat == "Busy"]
        insert_professor_busy_slots_from_ui(busy_slots, professor_id, db_path)
        return RedirectResponse(url="/", status_code=303)
    else:
        return {"status": "error", "message": "User not found"}
                
@app.get("/test")
async def testing(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})



# -------------------- Admin Management Routes --------------------
@app.get("/admin_management", response_class=HTMLResponse)
async def admin_management(request: Request):
    """
    Admin management page - shows current admins and allows adding/removing admins.
    Admin-only route.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        # Get current user email
        user_info = request.session.get("user")
        current_user_email = user_info.get("email") if user_info else None
        
        # Get all admins with hierarchy information
        admins_raw = get_all_admins(db_path)
        admin_count = get_admin_count(db_path)
        
        # Enhance admin information with hierarchy and permissions
        admins = []
        for admin in admins_raw:
            # Check if current user can remove this admin
            can_remove, reason = can_remove_admin(db_path, current_user_email, admin['email'])
            
            # Get creator information
            created_by = None
            if admin.get('created_by_admin_id'):
                with get_db_session(db_path) as session:
                    creator = session.query(User).filter_by(UserID=admin['created_by_admin_id']).first()
                    if creator:
                        created_by = creator.Email
            
            admin_info = {
                **admin,
                'can_be_removed': can_remove,
                'removal_reason': reason if not can_remove else None,
                'created_by': created_by,
                'is_founder': admin.get('is_founder_admin', 0) == 1
            }
            admins.append(admin_info)
        
        return templates.TemplateResponse(
            "admin_management.html",
            {
                "request": request,
                "admins": admins,
                "admin_count": admin_count,
                "current_user_email": current_user_email,
                "user": user_info
            }
        )
    except Exception as e:
        logger.error(f"Error in admin management page: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading admin management: {str(e)}")


@app.post("/add_admin")
async def add_admin_route(request: Request, admin_name: str = Form(...), admin_email: str = Form(...)):
    """
    Add a new admin user. Admin-only route.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        # Get current user email to track who created this admin
        user_info = request.session.get("user")
        current_user_email = user_info.get("email") if user_info else None
        
        success, message = add_admin_user(db_path, admin_name, admin_email, current_user_email)
        
        if success:
            # Redirect back to admin management with success message
            response = RedirectResponse(url="/admin_management", status_code=303)
            # You might want to add flash messages here
            return response
        else:
            # Redirect back with error message
            response = RedirectResponse(url="/admin_management", status_code=303)
            # You might want to add flash messages here
            return response
            
    except Exception as e:
        logger.error(f"Error adding admin: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding admin: {str(e)}")


@app.post("/remove_admin")
async def remove_admin_route(request: Request, admin_email: str = Form(...)):
    """
    Remove admin privileges from a user. Admin-only route.
    """
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only.")

    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        # Get current user email for hierarchy checks
        user_info = request.session.get("user")
        current_user_email = user_info.get("email") if user_info else None
        
        success, message = remove_admin_user(db_path, admin_email, current_user_email)
        
        # Redirect back to admin management
        return RedirectResponse(url="/admin_management", status_code=303)
        
    except Exception as e:
        logger.error(f"Error removing admin: {e}")
        raise HTTPException(status_code=500, detail=f"Error removing admin: {str(e)}")


@app.get("/setup_first_admin", response_class=HTMLResponse)
async def setup_first_admin_page(request: Request):
    """
    First-time admin setup page. Only accessible if no admins exist.
    """
    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        admin_count = get_admin_count(db_path)
        if admin_count > 0:
            # Admins already exist, redirect to home
            return RedirectResponse(url="/home", status_code=303)
        
        return templates.TemplateResponse("setup_first_admin.html", {"request": request})
        
    except Exception as e:
        logger.error(f"Error in setup first admin page: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading setup page: {str(e)}")


@app.post("/setup_first_admin")
async def setup_first_admin_submit(request: Request, admin_name: str = Form(...), admin_email: str = Form(...)):
    """
    Create the first admin user.
    """
    db_path = request.session.get("db_path")
    if not db_path:
        raise HTTPException(status_code=422, detail="Database path not provided in session.")

    try:
        admin_count = get_admin_count(db_path)
        if admin_count > 0:
            # Admins already exist, redirect to home
            return RedirectResponse(url="/home", status_code=303)
        
        success, message = ensure_first_admin(db_path, admin_name, admin_email)
        
        if success:
            # Update session to reflect admin status
            user_info = request.session.get("user", {})
            if user_info.get("email") == admin_email:
                user_info["role"] = "Admin"
                request.session["user"] = user_info
            
            return RedirectResponse(url="/home", status_code=303)
        else:
            return templates.TemplateResponse(
                "setup_first_admin.html", 
                {"request": request, "error": message}
            )
            
    except Exception as e:
        logger.error(f"Error setting up first admin: {e}")
        return templates.TemplateResponse(
            "setup_first_admin.html", 
            {"request": request, "error": f"Error creating admin: {str(e)}"}
        )


# -------------------- Settings Routes --------------------
# Settings functionality moved to organization registration


# -------------------- Main --------------------
if __name__ == "__main__":
    # Run with:  uvicorn main:app --reload  (or python main.py)
    uvicorn.run(app, host="localhost", port=4000)
