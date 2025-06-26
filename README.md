# Timetable Optimization System

This project provides an automated timetable generation system designed for educational institutions. It uses **Google OR-Tools** for constraint-based optimization, FastAPI for the backend, and SQLite for data management. The system features **Google Authentication**, **multi-organization support**, and **multiple professors per course** functionality to address complex scheduling needs efficiently.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [Endpoints](#endpoints)
- [How to Use](#how-to-use)
- [Deployment Timeout Configuration](#deployment-timeout-configuration)
  
## Overview

This timetable optimization system automates the complex process of scheduling courses, professors, and students. It supports **multiple organizations**, each with their own isolated database, and handles **multiple professors per course** with proper constraint management.

The system consists of:
- A **backend** that processes course data, professor schedules, and student enrollments to generate optimized timetables
- A **frontend** providing intuitive interfaces for data upload, timetable viewing, and schedule downloads
- A **multi-organization architecture** supporting separate institutions with domain-based authentication
- An **advanced constraint programming algorithm** using Google OR-Tools for conflict-free scheduling

## Features

- **Automatic Timetable Generation**: Generates conflict-free schedules using Google OR-Tools constraint programming
- **Multiple Professors per Course**: Full support for courses taught by multiple professors with proper constraint handling
- **Multi-Organization Support**: Separate databases and authentication for different educational institutions
- **Google OAuth 2.0 Authentication**: Secure, domain-based login and access control
- **Role-Based Access**: Differentiated access for Admins, Professors, and Students
- **CSV/Excel Data Import**: Flexible data upload supporting both CSV and Excel formats
- **Downloadable Timetables**: Export timetables as CSV files for administrators and individual students
- **Constraint Optimization**: Multi-phase algorithm handling professor conflicts, student conflicts, and time slot capacity
- **Professor Busy Slot Management**: Web interface for professors to set their availability
- **Scalable Architecture**: Supports hundreds of courses, students, and faculty members
- **Database Normalization**: Proper many-to-many relationships for courses and professors

## Technology Stack

- **Google OR-Tools**: Constraint Programming for optimization
- **FastAPI**: High-performance, asynchronous web framework
- **SQLite + SQLAlchemy**: Lightweight, file-based databases with ORM
- **Google OAuth 2.0**: Domain-based authentication system
- **Pandas**: Data manipulation for CSV/Excel processing
- **Jinja2**: Template engine for web interface

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Sparsh57/Time-Table-Optimization.git
   cd Time-Table-Optimization
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (see section below).

5. **Run the application**:
   ```bash
   python main.py
   ```

The application will be accessible at `http://localhost:4000`.

## Environment Variables

To run the application, you'll need to set up the following environment variables in a `.env` file in the project root directory:

```plaintext
CLIENT_ID=<Google OAuth Client ID>
CLIENT_SECRET=<Google OAuth Client Secret>
SECRET_KEY=<Session Secret Key>
DATABASE_HOST=<MariaDB Host>
DATABASE_USER=<MariaDB Username>
DATABASE_PORT=<MariaDB Port>
DATABASE_PASSWORD=<MariaDB Password>
DATABASE_REF=<MariaDB Database Name>
ALLOWED_EMAILS=<Comma-separated list of allowed emails for login>
```

## Database Schema

The system uses SQLite with SQLAlchemy ORM. Each organization gets a separate database file with the following structure:

### Core Tables
- **Users**: Stores all users (students, professors, admins) with role-based access
- **Courses**: Course information including credits and type (Required/Elective)
- **Course_Professor**: Junction table linking courses to multiple professors
- **Course_Stud**: Junction table linking students to their enrolled courses
- **Slots**: Available time slots (day, start time, end time)
- **Schedule**: Final timetable linking courses to time slots
- **Professor_BusySlots**: Professor availability constraints

### Meta Database
- **Organizations**: Tracks all registered organizations with their domains and database paths


## Endpoints

### Authentication

- `GET /auth/google`: Initiates the Google OAuth login flow.
- `GET /auth/google/callback`: Handles the OAuth callback and logs the user into the system.
- `GET /logout`: Logs the user out.

### Timetable Management

- `POST /send_admin_data`: Uploads CSV or Excel files containing course, professor, and student data, then generates the timetable.
- `GET /timetable`: Displays the generated timetable for administrators.
- `GET /timetable/{roll_number}`: Displays the timetable for a specific student.
- `GET /download-timetable`: Downloads the full timetable as a CSV file.
- `GET /download-timetable/{roll_number}`: Downloads a student's timetable as a CSV file.

### Time Slot Management
- `GET /select_timeslot`: Time slot configuration (Admin only)
- `POST /insert_timeslots`: Insert time slot data

## How to Use

### For Administrators

1. **Organization Setup**:
   - Register your organization with allowed email domains
   - First user becomes the admin automatically

2. **Data Upload**:
   - Upload three CSV/Excel files:
     - Course data with faculty assignments
     - Student registration data
     - Faculty preferences (busy slots)

3. **Timetable Generation**:
   - System automatically generates optimized timetable
   - View complete schedule or download as CSV

## How to Install and Run

1. **Clone the repo**: Download the repo from [github](https://github.com/Sparsh57/Time-Table-Optimization/) by cloning it or forking it.
2. **Download Libraries** Download all requirements using  ```pip install -r requirements.txt``` while in the project parent folder.
3. **Run the main python file using** ```python main.py``` while in the same folder.
4. **View app on Browser** view the app on [https://localhost:4000](https://localhost:4000)
     
---
For any bug reports please contact the repo contributor or submit issues on the github page

This project provides a scalable, optimized solution to the complex problem of scheduling in educational institutions, with a focus on automation, efficiency, and ease of use.

## Deployment Timeout Configuration

The timetable generation algorithm can take 10-20 minutes for complex datasets. When deploying to cloud platforms, you need to configure appropriate timeouts:

### Heroku
Add the following to your Heroku configuration:
```bash
heroku config:set WEB_TIMEOUT=1800  # 30 minutes
heroku config:set TIMEOUT=1800
```

### Railway
Configure in your `railway.toml`:
```toml
[build]
nixPacks = true

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
numReplicas = 1

[environment]
TIMEOUT = "1800"
```

### Docker/Nginx
For nginx reverse proxy, add to your configuration:
```nginx
proxy_read_timeout 1800s;
proxy_connect_timeout 1800s;
proxy_send_timeout 1800s;
```

### Local Development
For local development, the default uvicorn settings should work. The Procfile includes:
```
uvicorn main:app --timeout-keep-alive 1800 --timeout-graceful-shutdown 30
```
