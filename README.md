# Timetable Generation System for KREA University: Our Clock

This project aims to automate the generation of optimized student and professor timetables at KREA University using a combination of dynamic programming techniques and a custom UI. The system utilizes **Google OR-Tools** for constraint-based optimization, FastAPI for the back-end, and MariaDB for data management. Additionally, **Google Authentication** is integrated for secure user login. This solution addresses the complex scheduling needs of students, professors, and administrators by resolving conflicts in course timing and professor availability efficiently.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [Endpoints](#endpoints)
- [How to Use](#how-to-use)
- [Contributors](#contributors)
  
## Overview

At KREA University, timetabling has traditionally been done manually, leading to inefficiencies, especially in resolving course clashes and accommodating the availability of professors. This project automates and optimizes the timetable generation process using a **Constraint Programming** algorithm from **Google OR-Tools**, ensuring an efficient and conflict-free schedule.

The project consists of:
- A **back-end** system that processes input data (courses, professor schedules, student enrollment) and generates timetables.
- A **front-end** that provides user-friendly interfaces for uploading data, viewing timetables, and downloading the generated schedule.
- A **Google OAuth** system for secure access.

Find complete diagrams on the docs page at [https://github.com/Sparsh57/Time-Table-Optimization/blob/master/docs/Timetable_Presentation.pdf](https://github.com/Sparsh57/Time-Table-Optimization/blob/master/docs/Timetable_Presentation.pdf)

## Features

- **Automatic Timetable Generation**: Generates conflict-free schedules using Google OR-Tools.
- **Custom UI for Data Entry**: Facilitates the input of data related to courses, faculty preferences, and student choices.
- **Google OAuth 2.0 Authentication**: Secure login and access control for administrators, professors, and students.
- **Downloadable Timetables**: Timetables can be downloaded as CSV files for both administrators and individual students.
- **Scalability**: Supports hundreds of courses, students, and faculty, with real-time timetable generation.
  
## Technology Stack

- **Google OR-Tools**: Used for Constraint Programming to optimize timetable generation.
- **FastAPI**: High-performance, asynchronous framework used for building the back-end.
- **MariaDB**: Relational database for storing course data, professor schedules, and student information.
- **Google OAuth 2.0**: Authentication system used for secure user login.
- **Pandas**: Data manipulation library for handling CSV and Excel files.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/username/timetable-generation-system.git
   cd timetable-generation-system
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (see section below).

5. **Run the application**:
   ```bash
   uvicorn app:app --reload
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

The project uses MariaDB for managing course, professor, and student data. Key tables include:

- **users**: Stores user information (students, professors, admins).
- **courses**: Stores information about courses offered.
- **professors**: Stores professor details and their assigned courses.
- **student_courses**: Records the enrollment of students in courses.
- **professor_busy_slots**: Stores the availability of professors to prevent clashes.

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

### Other Endpoints

- `GET /`: Home page.
- `GET /dashboard`: Admin dashboard for managing timetable data.
- `GET /get_role_no`: Form for students to enter their roll number.
  
## How to Use

1. **Login**: Users can log in using their Google account via OAuth 2.0.
2. **Upload Data**: Administrators can upload CSV/Excel files containing course details, professor schedules, and student enrollments.
3. **Generate Timetable**: Once the data is uploaded, the system will automatically generate an optimized timetable.
4. **View Timetable**: Administrators can view the generated timetable, while students can view and download their specific timetable by entering their roll number.
5. **Download**: Administrators and students can download the timetable in CSV format.

## How to Install and Run

1. **Clone the repo**: Download the repo from [github](https://github.com/Sparsh57/Time-Table-Optimization/) by cloning it or forking it.
2. **Download Libraries** Download all requirements using  ```pip install -r requirements.txt``` while in the project parent folder.
3. **Run the main python file using** ```python main.py``` while in the same folder.
4. **View app on Browser** view the app on [https://localhost:4000](https://localhost:4000)
     
---
For any bug reports please contact the repo contributor or submit issues on the github page

This project provides a scalable, optimized solution to the complex problem of scheduling in educational institutions, with a focus on automation, efficiency, and ease of use.
