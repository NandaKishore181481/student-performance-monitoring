# EduInsight AI - Student Performance Monitoring & Alert System

A complete, AI-powered system designed to monitor student academic progress, identify students at risk of failure, explain model predictions using Explainable AI (XAI) concepts, send automated SMS, WhatsApp, and Email alerts, and automate attendance and marks entry using OpenCV Face Recognition and OCR.

## Departments Supported

| Code | Full Name |
|------|-----------|
| `CS` | Computer Science |
| `ECE` | Electronics & Communication Engineering |
| `DS` | Data Science |
| `AIML` | Artificial Intelligence & Machine Learning |
| `MECH` | Mechanical Engineering |
| `EEE` | Electrical & Electronics Engineering |

---

## Features

1. **Role-Based Streamlit Dashboard**: Portals for **HODs**, **Faculty**, **Students**, and **Parents** with JWT authorization. Automatically defaults to a premium **Dark Mode** interface after login. Includes an interactive **Forgot Password** account recovery panel and dynamic navigation buttons to switch between Login and Sign Up screens programmatically.
2. **AutoML Risk Classifier**: PyCaret-based model training and automated selection of the best-performing model (Decision Tree, Random Forest, XGBoost, SVM, KNN, Logistic Regression) with Scikit-Learn fallback pipelines.
3. **Explainable AI (XAI)**: SHAP/LIME-inspired explanation systems pinpointing key risk factors (e.g. low attendance, assignment delays).
4. **FastAPI REST Service**: Clean, documented endpoints for mobile integration (`/students`, `/attendance`, `/marks`, `/prediction`, `/risk`).
5. **Multi-Channel Alert Engine**: Telegram Bot, Twilio SMS/WhatsApp, and SMTP email dispatch with dynamic AI message templating.
6. **Announcement Hub**: HODs and Faculty can publish announcements targeted by Department, Year, Section, and Priority. Students see only announcements relevant to their department.
7. **Telegram Bot Integration**: Live Telegram chat routing, rich format alerts, rate-limit resilience, and automatic fallback routing.
8. **Automation**:
   - OpenCV-based Haar Cascade Face Recognition for marking attendance.
   - OCR-based tabular grade sheets scanning (EasyOCR/Tesseract fallbacks).
   - Automated Overdue Assignment Tracker.
9. **Professional PDF Reports**: Auto-generated report cards using ReportLab.
10. **Streamlit Cloud Permission Fallbacks**: Automatic database replication to `/tmp/student_system_[md5].db` if the default project folder is read-only.

---

## Directory Layout

```text
student_performance_monitoring/
├── college_data_template.xlsx  # Primary data source (Staff, Students, Marks, Attendance)
├── data/                       # Databases, synthetic datasets, and generated PDF reports
├── models/                     # Saved ML model binaries
├── src/
│   ├── api/
│   │   └── main.py             # FastAPI REST endpoints
│   ├── automation/
│   │   ├── face_recognition.py # OpenCV Face scanning
│   │   ├── ocr_marks.py        # EasyOCR/Tesseract Marks OCR scanner
│   │   └── assignment_tracker.py # Assignment scan & reminder agent
│   ├── dashboard/
│   │   └── app.py              # Streamlit Multi-Portal Client Dashboard
│   ├── alerts.py               # Twilio SMS/WhatsApp + SMTP emails
│   ├── analytics.py            # K-Means clustering + remark NLP sentiment analysis
│   ├── data_processor.py       # Data simulator & preprocessing
│   ├── database.py             # SQLAlchemy models & Excel-based database seed
│   ├── ml_models.py            # AutoML training & predictions
│   └── reporting.py            # ReportLab PDF report generator
├── requirements.txt            # Python dependencies manifest
├── run.py                      # Orchestrator runner script
└── README.md                   # Setup guide
```

---

## Quick Setup & Start

### 1. Create Environment & Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Prepare the Excel Data Template

Fill in `college_data_template.xlsx` with your college data. The workbook has these sheets (in order):

| Sheet # | Sheet Name | Purpose |
|---------|-----------|---------|
| 0 | Instructions | Guidance notes |
| 1 | Departments | Dept codes + HOD username mapping |
| 2 | Staff | Faculty & HOD login credentials, department |
| 3 | Students | Student login credentials, parent info, section |
| 4 | Marks | Subject-wise marks per roll number |
| 5 | Attendance | Attendance records per roll number |

> **Important:** The system reads sheets **by position (index)**, so do not add, remove, or reorder sheets.

#### Student Section Format (`class_section`)
When seeding the database, the system automatically reads `department_code`, `year`, and `section` from the Students sheet and generates a consolidated class section in the format:
```text
{department_code}-Y{year}{section}  (e.g., CS-Y1A, ECE-Y4A)
```
This specific formatting matches the pattern expected by the **Announcement Hub** in the student portal, allowing announcements targeted at specific years or sections to filter and display correctly.

### 3. Initialize Database & Train Models

```bash
python run.py
```

On first run, the database is automatically seeded from `college_data_template.xlsx`.

---

## Login Credentials

All credentials are read directly from the Excel file.

### HODs

HODs are automatically detected from the **Departments** sheet. The `hod_username` column maps a department to a staff member. If the username in the Staff sheet matches the `hod_username` in Departments, they get the `HOD` role.

**Fallback HODs** (auto-created if not found in Staff sheet):

| Department | Username | Password |
|------------|----------|----------|
| CS | `hod_cs` | `hod123` |
| ECE | `hod_ece` | `hod123` |
| DS | `hod_ds` | `hod123` |
| AIML | `hod_aiml` | `hod123` |
| MECH | `hod_mech` | `hod123` |

### Faculty

Credentials come directly from the **Staff sheet** in the Excel file.

Example (from default template):

| Username | Password | Department |
|----------|----------|------------|
| `cs_prof_ramesh` | `cs123` | CS |
| `ece_prof_anita` | `ece123` | ECE |
| `ds_prof_vikram` | `ds123` | DS |
| `aiml_prof_sneha` | `aiml123` | AIML |

### Students

Credentials come directly from the **Students sheet** in the Excel file.

Example (from default template):

| Username | Password | Roll No | Section |
|----------|----------|---------|---------|
| `cs_john_2024` | `23r11a6201` | 23r11a6201 | CS-Y1A |
| `cs_priya_2024` | `23r11a6202` | 23r11a6202 | CS-Y1A |
| `23r11a60202` | `23r11a60203` | 23r11a60203 | ECE-Y4A |
| `ds_peter_2024` | `23r11a6701` | 23r11a6701 | DS-Y1A |
| `aiml_katherine_24` | `23r11a6601` | 23r11a6601 | AIML-Y1A |

### Parents

Parent accounts are automatically created with the **same password as their child**. The username is `<student_username>_parent`.

Example (from default template):

| Parent Username | Password | Child Username |
|----------------|----------|----------------|
| `cs_john_2024_parent` | `23r11a6201` | `cs_john_2024` |
| `cs_priya_2024_parent` | `23r11a6202` | `cs_priya_2024` |
| `23r11a60202_parent` | `23r11a60203` | `23r11a60202` |
| `ds_peter_2024_parent` | `23r11a6701` | `ds_peter_2024` |
| `aiml_katherine_24_parent` | `23r11a6601` | `aiml_katherine_24` |

> **Note:** The parent username is always `<student_username>_parent` and the password is always the **same password as the student** (from the `password` column in the Students sheet).

---

## Launch Services

**Streamlit Web Application:**
```bash
streamlit run src/dashboard/app.py
```
Open your browser at `http://localhost:8501`.

**REST API Backend:**
```bash
uvicorn src.api.main:app --reload
```
Navigate to Swagger docs at `http://127.0.0.1:8000/docs`.

---

## REST API Endpoint Reference

| Method | Endpoint | Allowed Roles | Description |
|---|---|---|---|
| **POST** | `/api/auth/login` | *All Users* | Authenticate and receive a JWT Bearer Token |
| **GET** | `/api/students` | *All (Filtered)* | Retrieve student profiles |
| **GET** | `/api/marks/{student_id}` | *All (Filtered)* | Retrieve marks for a student |
| **POST** | `/api/marks` | `Faculty`, `HOD` | Create or update a student's marks |
| **POST** | `/api/attendance` | `Faculty`, `HOD` | Update attendance percentage |
| **GET** | `/api/prediction/{student_id}` | *All (Filtered)* | Predict student risk level |
| **GET** | `/api/risk/{student_id}/explain` | *All (Filtered)* | Retrieve XAI risk factors |
| **GET** | `/api/reports/pdf/{student_id}` | *All (Filtered)* | Download a PDF report card |

---

## Credentials Configuration (Alerts)

Configure these in environment variables or Streamlit Cloud Secrets:

```env
# Telegram Bot Alert Configuration
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# SMTP Email Configuration
SMTP_USERNAME="your_email@gmail.com"
SMTP_PASSWORD="your_app_password"
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT="587"
SENDER_EMAIL="your_email@gmail.com"

# Twilio (Optional)
TWILIO_ACCOUNT_SID="your_twilio_sid"
TWILIO_AUTH_TOKEN="your_twilio_auth_token"
TWILIO_PHONE_NUMBER="your_twilio_phone_number"
```

> If not configured, the system operates in **Simulation Mode** — all alerts are logged but not actually sent, so you can test without credentials.

---

## Production Deployment

### Database Migration

Change the connection URL in `src/database.py` to PostgreSQL or MySQL:

```python
# From SQLite:
DATABASE_URL = "sqlite:///student_system.db"
# To PostgreSQL:
DATABASE_URL = "postgresql://user:password@db-host:5432/dbname"
```

### Server Deployment (AWS / Heroku / Render)

```bash
# API
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app

# Dashboard — deploy on Streamlit Community Cloud
# Push to GitHub and connect at share.streamlit.io
```

### Streamlit Cloud Notes

- The SQLite database is **volatile** on Streamlit Cloud and resets on each container restart.
- On restart, the app automatically re-seeds from `college_data_template.xlsx`.
- Ensure the Excel file is committed to your repository root.
