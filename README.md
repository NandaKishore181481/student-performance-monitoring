# EduInsight AI - Student Performance Monitoring & Alert System

A complete, AI-powered system designed to monitor student academic progress, identify students at risk of failure, explain model predictions using Explainable AI (XAI) concepts, send automated SMS, WhatsApp, and Email alerts, and automate attendance and marks entry using OpenCV Face Recognition and OCR.

## Features

1. **Role-Based Streamlit Dashboard**: Portals for **HODs**, **Faculty**, **Students**, and **Parents** with JWT authorization.
2. **AutoML Risk Classifier**: PyCaret-based model training and automated selection of the best-performing model (Decision Tree, Random Forest, XGBoost, SVM, KNN, Logistic Regression) with Scikit-Learn fallback pipelines.
3. **Explainable AI (XAI)**: SHAP/LIME-inspired explanation systems pinpointing key risk factors (e.g. low attendance, assignment delays).
4. **FastAPI REST Service**: Clean, documented endpoints for mobile integration (`/students`, `/attendance`, `/marks`, `/prediction`, `/risk`).
5. **Multi-Channel Alert Engine**: Twilio SMS/WhatsApp integration and SMTP email dispatch with dynamic AI message templating.
6. **Automation**:
   - OpenCV-based Haar Cascade Face Recognition for marking attendance.
   - OCR-based tabular grade sheets scanning (EasyOCR/Tesseract fallbacks).
   - Automated Overdue Assignment Tracker.
7. **Professional PDF Reports**: Auto-generated report cards using ReportLab.

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
This seeds the following default accounts:
* **HOD**: username `hod` | password `hod123`
* **Faculty**: username `faculty1` | password `fac123`
* **Student**: username `student1` | password `student123`
* **Parent**: username `parent1` | password `parent123`

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

## Credentials Configuration (Alerts)

To enable live notifications, configure the environment variables before running:
```env
# Twilio Configuration
export TWILIO_ACCOUNT_SID="your_twilio_sid"
export TWILIO_AUTH_TOKEN="your_twilio_auth_token"
export TWILIO_PHONE_NUMBER="your_twilio_phone_number"

# SMTP Email Configuration
export SMTP_USERNAME="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
```
*Note: If these settings are not configured, the system operates in **Simulation Mode**, logging the simulated alerts and database logs instantly so you can test all alert channels without credentials.*

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
