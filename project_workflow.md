# Project Architecture & Workflow - EduInsight AI

This document details the operational workflow, data pipelines, machine learning logic, and automation sequences of the **EduInsight AI - Student Performance Monitoring & Alert System**.

---

## 1. Core System Architecture

The following flowchart details the end-to-end data and execution workflow:

```mermaid
graph TD
    %% Excel Seeding
    A[college_data_template.xlsx] -->|import_data.py| B[(student_system.db)]
    
    %% ML Training
    B -->|data_processor.py| C{ML Engine}
    C -->|AutoML comparisons| D[models/best_student_model.pkl]
    
    %% User Authentication
    E[User Access] -->|src/dashboard/app.py| F{JWT Auth Shield}
    F -->|Fail| G[Frosted Glass Login Page]
    F -->|Success| H{Role Router}
    
    %% Portal Routing
    H -->|Student| I[Student Portal]
    H -->|Parent| J[Parent Portal]
    H -->|Faculty| K[Faculty Portal]
    H -->|HOD| L[HOD Dashboard]
    
    %% Portal Features
    I -->|Query Grades & Risk| M[Plotly Trends & SHAP Explanations]
    J -->|Review Logs| N[Parent Alert Logs]
    K -->|Attendance/Remarks| O[OpenCV Face Scan & EasyOCR Marks]
    L -->|Risk Audit| P[K-Means Clustering & Alert Broadcasts]
```

---

## 2. Component Workflows

### Workflow A: Excel Data Ingestion
This pipeline cleans and populates the system database from the college spreadsheet template:

```mermaid
sequenceDiagram
    participant Excel as college_data_template.xlsx
    participant Importer as import_data.py
    participant DB as SQLite DB (student_system.db)
    
    Excel->>Importer: Read Sheets (Depts, Staff, Students, Marks, Attendance)
    Importer->>Importer: Map staff roles (e.g. Professor -> Faculty)
    Importer->>Importer: Auto-create HOD users from Department HOD names
    Importer->>Importer: Match Student records and generate child-parent links
    Importer->>Importer: Verify marks ranges (Internals <=30, Assignment <=20, Exam <=50)
    Importer->>Importer: Normalize attendance records (Present, Absent, Late)
    Importer->>Importer: Parse the 'Percentage' column (auto-compute fallback)
    Importer->>DB: Wipe database & Bulk Insert all mapped entities
```

### Workflow B: ML Risk Prediction & Diagnostic Explainability
This loop determines student risk and translates statistical weights into readable reasons:

```mermaid
graph LR
    subgraph Input Features
        F1[Attendance %]
        F2[Internal Marks Avg]
        F3[Assignment Score Avg]
        F4[Exam Marks Avg]
        F5[Assignment Submission Rate]
        F6[Remark Sentiment Score]
    end
    
    subgraph SVM Pipeline
        F1 & F2 & F3 & F4 & F5 & F6 --> Scale[Standard Scaler]
        Scale --> Model[Support Vector Machine Predictor]
    end
    
    subgraph Diagnostic Output
        Model --> Label[Risk Category: Low, Medium, High]
        Model --> Score[Risk Score: 0 to 100]
        Model --> Explainer[SHAP Fallback Rule Engine]
    end
    
    Explainer --> Reason1{Attendance < 75%}
    Reason1 -->|Yes| R1[High Risk: Attendance below mandatory limit]
    Explainer --> Reason2{Internals < 15/30}
    Reason2 -->|Yes| R2[High Risk: Failing internal test average]
```

### Workflow C: Automation Pipelines (OCR & Face Scan)
The automated workflows run under the Faculty Portal tab:

1.  **Face Scan Classroom Attendance**:
    *   **Input**: Classroom camera image upload or live frame.
    *   **Processing**:
        *   OpenCV Face Cascades locate faces in the grid.
        *   Cross-references face encodings with registered image files in `data/known_faces`.
    *   **Database Write**: Adds a daily `AttendanceRecord` entry marked `Present` for each matched student.
2.  **OCR Report Card Ingestion**:
    *   **Input**: Grade sheet scan upload.
    *   **Processing**: EasyOCR segmenter localizes bounding boxes and reads grade tables.
    *   **Database Write**: Writes structured marks records to `AcademicMarks` for the target student.

---

## 3. Communication & Alert Dispatch Workflow
This engine automatically communicates academic status updates to parents:

```mermaid
sequenceDiagram
    participant HOD as HOD Dashboard
    participant Alert as alerts.py (Alert Engine)
    participant Template as AI personalized templates
    participant SMTP as SMTP (Email Server)
    participant SMS as Twilio SMS API
    
    HOD->>Alert: Trigger broadcast warn (High/Medium Risk Students)
    Alert->>Template: Generate custom advice text based on student's weak subjects
    Template-->>Alert: Returns warning message
    Alert->>SMTP: Send Email to Parent account
    Alert->>SMS: Send short warning warning SMS/WhatsApp to Parent phone
    Alert->>Alert: Log transmission result (Sent/Failed) in database table
```

---

## 4. Role Navigation Map

### 👨‍🎓 Student Portal
1.  **Visual Metrics**: Gauges overall attendance rate.
2.  **ML Predictions**: View AI Risk Status (Low/Medium/High) and exam pass probability.
3.  **Grades Trend**: Dynamic Plotly bar chart mapping internals, assignments, and exam grades.
4.  **AI Diagnostics**: SHAP-style explanation cards detailing positive and risk-inducing habits.
5.  **Export**: Instantly download a ReportLab-generated PDF Progress Report.

### 👪 Parent Portal
1.  **Ward Status**: Tracks attendance percentage and current academic risk classification.
2.  **Alert log**: Table record showing all emails, SMS, and WhatsApp alerts dispatched to their inbox.

### 👩‍🏫 Faculty Portal
1.  **Manual Grades**: Selectbox select student, input grades (out of 100), update attendance slider, and add behavioral remarks (processed with NLTK sentiment analysis).
2.  **OpenCV Attendance**: Upload classroom images to run face matches.
3.  **OCR Marks**: Parse scanned report cards to auto-populate grade databases.

### 🏛️ HOD Portal
1.  **Overview Cards**: View total enrolled students, average department attendance, and total active high-risk cases.
2.  **Risk Audit Grid**: Interactive table of all student data.
3.  **Broadcast warnings**: Exposes the trigger interface for SMS, WhatsApp, and Email alerts.
4.  **Clustering Map**: Plotly Scatter diagram using K-Means to cluster students into distinct academic classes.
5.  **Performance metrics**: Pass/fail percentages broken down by subject.
