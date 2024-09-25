import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
from dotenv import load_dotenv
from starlette.staticfiles import StaticFiles

load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Serve static files like CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure session middleware
app.add_middleware(SessionMiddleware, secret_key="secret")

templates = Jinja2Templates(directory="views")

users = {}


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
