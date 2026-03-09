# QR Code Based Attendance System

A secure, dynamic QR Code Based Attendance System for college classrooms (100+ students) built with **Python Flask**, **SQLAlchemy**, and **Bootstrap 5**.

---

## Features

| Feature | Details |
|---|---|
| **Dynamic QR codes** | Rotates every 20 seconds to prevent screenshot sharing |
| **Session expiry** | Attendance sessions expire after 2 minutes |
| **Network validation** | Only accepts attendance from the college WiFi (192.168.x.x, 10.x.x.x) |
| **Duplicate prevention** | A student can only mark attendance once per session |
| **Teacher dashboard** | View per-course stats: present, absent, attendance % |
| **Attendance export** | Download an Excel (.xlsx) report for any session |
| **Responsive UI** | Bootstrap 5, works on mobile and desktop |

---

## Technology Stack

- **Backend:** Python 3.9+ / Flask
- **Database:** SQLite (default, zero-config) or MySQL
- **ORM:** Flask-SQLAlchemy
- **QR Code:** `qrcode[pil]`
- **Excel export:** `openpyxl`
- **Password hashing:** `werkzeug.security`
- **Frontend:** Bootstrap 5, Vanilla JavaScript

---

## Project Structure

```
qr-attendance-system/
│
├── app.py                         # Main Flask application with all routes
├── models.py                      # SQLAlchemy database models
├── database.py                    # Database connection and initialization
├── config.py                      # Configuration (DB URI, secret key, IP ranges, …)
├── seed.py                        # Script to seed sample data (teachers, students, courses)
│
├── templates/
│   ├── base.html                  # Base template with Bootstrap 5
│   ├── login.html                 # Login page (teacher & student)
│   ├── teacher_dashboard.html     # Teacher dashboard – course stats, generate QR
│   ├── qr_display.html            # QR display with auto-refresh countdown
│   ├── student_dashboard.html     # Student attendance history
│   ├── attendance_success.html    # Confirmation page after successful attendance
│   ├── attendance_error.html      # Error page (expired QR, wrong network, duplicate)
│   └── attendance_list.html       # Full attendance list + export button
│
├── static/
│   ├── css/style.css              # Custom styles
│   └── js/qr_refresh.js          # JavaScript for auto-refreshing the QR code
│
├── requirements.txt               # Python dependencies
├── schema.sql                     # MySQL-compatible DDL (tables auto-created for SQLite)
└── README.md                      # This file
```

---

## Prerequisites

- Python 3.9 or higher
- pip

For MySQL support (optional):
- MySQL 5.7+ / MariaDB 10.3+

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/qr-attendance-system.git
cd qr-attendance-system
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Database Setup

### Option A – SQLite (default, no extra setup needed)

The database file `qr_attendance.db` is created automatically the first time you run the app.

### Option B – MySQL

1. Create the database using the provided schema:

   ```bash
   mysql -u root -p < schema.sql
   ```

2. Set the `DATABASE_URL` environment variable before running:

   ```bash
   export DATABASE_URL="mysql+pymysql://user:password@localhost/qr_attendance"
   ```

---

## Seed Sample Data

Populate the database with 2 teachers, 4 courses, and 100 students:

```bash
python seed.py
```

---

## Running the Application

```bash
python app.py
```

The server starts at **http://127.0.0.1:5000**

---

## Default Credentials (after running `seed.py`)

| Role | Email | Password |
|---|---|---|
| Teacher | alice@college.edu | teacher123 |
| Teacher | bob@college.edu | teacher456 |
| Student | student001@college.edu | student123 |
| Student | student002@college.edu | student123 |
| … | student001–100@college.edu | student123 |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (dev key) | Flask session secret – **change in production** |
| `DATABASE_URL` | `sqlite:///qr_attendance.db` | SQLAlchemy database URI |
| `SERVER_BASE_URL` | `http://127.0.0.1:5000` | Base URL embedded in QR codes |

---

## System Workflow

### Teacher

1. Log in at `/login` (select **Teacher** role).
2. View all assigned courses on the dashboard.
3. Click **Generate Attendance QR** for the desired course.
4. The QR code is displayed and rotates every 20 seconds.
5. Share your screen with students (projector / TV).
6. View attendance live; export to Excel when done.

### Student

1. Connect to the **college WiFi** (required).
2. Log in at `/login` (select **Student** role).
3. Scan the QR code displayed by the teacher.
4. Attendance is recorded automatically.
5. View your attendance history in the student dashboard.

---

## Security Features

| Threat | Mitigation |
|---|---|
| Screenshot sharing | QR token rotates every 20 seconds |
| QR reuse after class | Session expires after 2 minutes |
| Off-campus attendance | IP address checked against allowed ranges |
| Duplicate marking | Unique constraint on (student_id, session_id) |
| Password storage | Passwords hashed with `werkzeug.security` (PBKDF2-HMAC-SHA256) |

### Configuring Allowed IP Ranges

Edit `config.py` to restrict which IP prefixes are accepted:

```python
ALLOWED_IP_RANGES = [
    '192.168.1.',   # lab block
    '10.0.',        # staff network
    '127.0.0.1',    # localhost (testing only – remove in production)
]
```

---

## API Endpoints

| Method | URL | Description |
|---|---|---|
| GET/POST | `/login` | Login page |
| GET | `/logout` | Logout |
| GET | `/teacher/dashboard` | Teacher dashboard |
| POST | `/teacher/generate_qr` | Create attendance session & QR |
| GET | `/teacher/qr_display/<id>` | QR display page |
| POST | `/teacher/refresh_qr/<id>` | Rotate QR token (JSON) |
| GET | `/teacher/attendance/<id>` | Attendance list |
| GET | `/teacher/export/<id>` | Download Excel report |
| GET | `/student/dashboard` | Student attendance history |
| GET | `/attend/<token>` | Mark attendance via QR scan |

---

## Architecture Overview

```
Browser (teacher)           Flask App              Database
      │                         │                      │
      │  POST /teacher/generate_qr ─────────────────► Create AttendanceSession
      │◄─ redirect to /qr_display ──────────────────  (unique token, expiry time)
      │                         │
      │  GET  /qr_display/<id>  │─ query session ─────► Return QR b64 image
      │                         │
      │  POST /teacher/refresh_qr  ────────────────── Rotate token in DB
      │◄─ { qr_b64, expired } ─────────────────────
      │
      │ (QR code shown on projector)
      │
Browser (student, mobile)
      │
      │  GET /attend/<token> ──────────────────────── Validate token
      │                                                Check IP range
      │                                                Check not duplicate
      │                                                INSERT attendance row
      │◄─ attendance_success.html
```

