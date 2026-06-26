# EduInsight AI - Student Performance Monitoring & Alert System

A complete, AI-powered system designed to monitor student academic progress, identify students at risk of failure, explain model predictions using Explainable AI (XAI) concepts, send automated SMS, WhatsApp, and Email alerts, and automate attendance and marks entry using OpenCV Face Recognition and OCR.

## Features

1. **Role-Based Streamlit Dashboard**: Portals for **HODs**, **Faculty**, **Students**, and **Parents** with JWT authorization. Automatically defaults to a premium **Dark Mode** interface after login. Includes an interactive **Forgot Password** account recovery panel and dynamic navigation buttons to switch between Login and Sign Up screens programmatically.
2. **AutoML Risk Classifier**: PyCaret-based model training and automated selection of the best-performing model (Decision Tree, Random Forest, XGBoost, SVM, KNN, Logistic Regression) with Scikit-Learn fallback pipelines.
3. **Explainable AI (XAI)**: SHAP/LIME-inspired explanation systems pinpointing key risk factors (e.g. low attendance, assignment delays).
4. **FastAPI REST Service**: Clean, documented endpoints for mobile integration (`/students`, `/attendance`, `/marks`, `/prediction`, `/risk`).
5. **Multi-Channel Alert Engine**: Telegram Bot, Twilio SMS/WhatsApp, and SMTP email dispatch with dynamic AI message templating:
   - **Student & Parent template splits** with custom greetings.
   - **Emails are deduplicated** if student and parent emails match.
   - **Phone and Telegram alerts are sent separately** so parents and students always receive their respective warning reports.
   - **Regards closings formatting** overridden globally: `Regards,\nDepartment of [Course Name] and Student Performance Cell` (no HOD names).
6. **Telegram Bot Integration**:
   - Live Telegram chat routing to custom parent/student Telegram Chat IDs.
   - **Rich alerts format**: Dispatches full, multi-line performance status reports directly on Telegram instead of a short summary.
   - **Pacing & Rate Limit Resilience**: Integrates a `0.05`s dispatch pacing interval and a retry sleep mechanism (handling `429 Too Many Requests` API status codes) to ensure 100% broadcast reliability.
   - Telegram Bot Onboarding Banner and connection settings expander placed at the bottom of the Parent Dashboard.
   - Automatic failed message fallback routing to the developer's chat ID (`1688994372`).
7. **Automation**:
   - OpenCV-based Haar Cascade Face Recognition for marking attendance.
   - OCR-based tabular grade sheets scanning (EasyOCR/Tesseract fallbacks).
   - Automated Overdue Assignment Tracker (dispatches reminders to both student and parent).
8. **Professional PDF Reports**: Auto-generated report cards using ReportLab.
9. **Streamlit Cloud Permission Fallbacks**: Automatic database replication to `/tmp/student_system_[md5].db` if the default project folder is read-only (Streamlit Cloud containers).

---

## Directory Layout

```text
student_performance_monitoring/
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
│   ├── database.py             # SQLAlchemy models & database seed
│   ├── ml_models.py            # AutoML training & predictions
│   └── reporting.py            # ReportLab PDF report generator
├── requirements.txt            # Python dependencies manifest
├── run.py                      # Orchestrator runner script
└── README.md                   # Setup guide
```

---

## Quick Setup & Start

### 1. Create Environment & Install Dependencies
Create a virtual environment and install the required modules:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Initialize Database & Train Models
Run the orchestrator script to automatically seed the database and train the ML models:
```bash
python run.py
```
This seeds the following default accounts (Demo Mode):
* **HOD**: username `hod` | password `hod123`
* **Faculty**: username `faculty1` | password `fac123`
* **Student**: username `student1` | password `student123`
* **Parent**: username `parent1` | password `parent123`

If you import your custom Excel template using `python import_data.py` (which replaces demo data), credentials will match your spreadsheet rows:
* **HOD**: username `hod_cs` (or other department HOD codes) | password `hod123` (auto-assigned for HODs)
* **Faculty**: username `cs_prof_ramesh` (as set in Staff sheet) | password `cs123` (as set in Staff sheet)
* **Student**: username `cs_john_2024` (as set in Students sheet) | password `23r11a6201` (as set in Students sheet)
* **Parent**: username `parent_cs_john_2024` (prefixed with `parent_` + student username) | password `parent123` (auto-assigned for parents)

### 3. Launch Services

* **Start the Streamlit Web Application**:
  ```bash
  python run.py --dashboard
  ```
  Open your browser and navigate to `http://localhost:8501`.

* **Start the REST API Backend**:
  ```bash
  python run.py --api
  ```
  Navigate to the Swagger documentation at `http://127.0.0.1:8000/docs`.

---

## Data Updates & Storage Architecture

When a faculty member or administrator updates student details (e.g., inputting marks, adjusting attendance percentages, or entering text remarks):
1. **Database Writes**: The application makes queries using SQLAlchemy sessions ([SessionLocal](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/src/database.py#L67)) and commits changes directly to the configured database.
2. **Database Resolution**: By default, it updates [student_system.db](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/data/student_system.db). If run on Streamlit Cloud or in a read-only environment, the app uses [get_db_path](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/src/database.py#L14) in [database.py](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/src/database.py) to automatically duplicate the seeded database to a writable location in the server's temporary directory (`/tmp/student_system_[md5].db`) to prevent permission errors.
3. **Execution Paths**: Data can be updated in two ways:
   - **Streamlit Faculty Dashboard**: Via the UI input fields, sliders, and buttons in [app.py](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/src/dashboard/app.py).
   - **REST API Endpoints**: Programmatically via authenticated HTTP requests to the REST server in [main.py](file:///C:/Users/Nanda%20Kishore/.gemini/antigravity/scratch/student_performance_monitoring/src/api/main.py).

---

## REST API Endpoint Reference

The system exposes a secure, JWT-authenticated FastAPI backend for programmatic access. The automatic OpenAPI Swagger UI is available at `http://127.0.0.1:8000/docs`.

### Key Endpoints

| Method | Endpoint | Allowed Roles | Description |
|---|---|---|---|
| **POST** | `/api/auth/login` | *All Users* | Authenticate credentials and receive a JWT Bearer Token |
| **GET** | `/api/students` | *All (Filtered)* | Retrieve student profiles (filtered by the user's role) |
| **GET** | `/api/marks/{student_id}` | *All (Filtered)* | Retrieve all subject marks for a student |
| **POST** | `/api/marks` | `Faculty`, `HOD` | Create or update a student's marks |
| **POST** | `/api/attendance` | `Faculty`, `HOD` | Update attendance percentage for a student |
| **GET** | `/api/prediction/{student_id}` | *All (Filtered)* | Run ML models to predict risk rating and pass probability |
| **GET** | `/api/risk/{student_id}/explain` | *All (Filtered)* | Retrieve SHAP/LIME-based explainability factors |
| **GET** | `/api/reports/pdf/{student_id}` | *All (Filtered)* | Generate and download a professional PDF report card |

---

## Credentials Configuration (Alerts)

To enable live notifications, configure the environment variables or Streamlit Cloud Secrets before running:
```env
# Twilio Configuration (Optional, falls back to Telegram / SMTP carrier gateways)
export TWILIO_ACCOUNT_SID="your_twilio_sid"
export TWILIO_AUTH_TOKEN="your_twilio_auth_token"
export TWILIO_PHONE_NUMBER="your_twilio_phone_number"

# Telegram Bot Alert Configuration
export TELEGRAM_BOT_TOKEN="8012759867:AAH3yR1pNsd8THXhZ2vnKzNnLONIAA2erE4"
export TELEGRAM_CHAT_ID="1688994372"  # Fallback/developer chat ID for testing

# SMTP Email Configuration
export SMTP_USERNAME="nani181481@gmail.com"
export SMTP_PASSWORD="bkdzvapzcgwepsgj"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER_EMAIL="nani181481@gmail.com"
```
*Note: If these settings are not configured, the system operates in **Simulation Mode**, logging the simulated alerts and database logs instantly so you can test all alert channels without credentials. If Telegram credentials are provided, messages route to the parent/student's configured Telegram Chat ID, automatically falling back to the developer's default `TELEGRAM_CHAT_ID` if delivery fails (e.g. invalid chat ID, or user has not started the bot).*

---

## Production Deployment

### Database Migration
Change the connection URL in `src/database.py` to point to MySQL or PostgreSQL:
```python
# From SQLite:
DATABASE_URL = "sqlite:///student_system.db"
# To PostgreSQL:
DATABASE_URL = "postgresql://user:password@db-host:5432/dbname"
```

### Server Deployment (AWS / Heroku / Render)
1. **API Deployment**: Deploy `src/api/main.py` on a cloud VM or platform like Render/Heroku running:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app
   ```
2. **Dashboard Deployment**: Deploy the dashboard folder on Streamlit Community Cloud or as a separate web service container pointing to the deployed API base URL.
