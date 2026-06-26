import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.database import get_db, User, StudentProfile, AcademicMarks, seed_database, verify_password
from src.ml_models import predict_student_risk, get_explainable_ai
from src.analytics import predict_exam_pass_probability
from src.reporting import generate_student_pdf_report

# Initialize database on API startup
seed_database()

app = FastAPI(
    title="Student Performance Monitoring & Alert API",
    description="REST API backing the AI Student Performance System with JWT security.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Secret Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-student-performance-system-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Pydantic Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

class StudentOut(BaseModel):
    id: int
    name: str
    roll_number: str
    class_section: str
    attendance_pct: float
    parent_name: Optional[str]

    class Config:
        orm_mode = True

class MarksOut(BaseModel):
    subject: str
    internal_marks: float
    assignment_scores: float
    exam_marks: Optional[float]
    total_marks: float

class PredictionOut(BaseModel):
    student_id: int
    name: str
    risk_label: str
    risk_score: float
    exam_pass_probability: float

class MarksUpdateInput(BaseModel):
    student_id: int
    subject: str
    internal_marks: float
    assignment_scores: float
    exam_marks: Optional[float] = None

class AttendanceUpdateInput(BaseModel):
    student_id: int
    attendance_pct: float

# JWT Helpers
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Helper to verify role permission
def check_role(required_roles: List[str]):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {required_roles}"
            )
        return current_user
    return dependency

# Endpoints
@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name
    }

@app.get("/api/students", response_model=List[StudentOut])
def get_students(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # HOD and Faculty see everyone, Students and Parents see only themselves/their ward
    if current_user.role in ["HOD", "Faculty"]:
        profiles = db.query(StudentProfile).all()
    elif current_user.role == "Student":
        profiles = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).all()
    elif current_user.role == "Parent":
        profiles = db.query(StudentProfile).filter(StudentProfile.parent_id == current_user.id).all()
    else:
        profiles = []
        
    out = []
    for p in profiles:
        out.append(StudentOut(
            id=p.id,
            name=p.user.name,
            roll_number=p.roll_number,
            class_section=p.class_section,
            attendance_pct=p.attendance_pct,
            parent_name=p.parent.name if p.parent else None
        ))
    return out

@app.get("/api/marks/{student_id}", response_model=List[MarksOut])
def get_student_marks(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Authorization checks
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if current_user.role == "Student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if current_user.role == "Parent" and student.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    marks = db.query(AcademicMarks).filter(AcademicMarks.student_id == student_id).all()
    out = []
    for m in marks:
        total = m.internal_marks + m.assignment_scores + (m.exam_marks or 0.0)
        out.append(MarksOut(
            subject=m.subject,
            internal_marks=m.internal_marks,
            assignment_scores=m.assignment_scores,
            exam_marks=m.exam_marks,
            total_marks=total
        ))
    return out

@app.post("/api/marks")
def update_marks(data: MarksUpdateInput, db: Session = Depends(get_db), current_user: User = Depends(check_role(["Faculty", "HOD"]))):
    student = db.query(StudentProfile).filter(StudentProfile.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    record = db.query(AcademicMarks).filter(
        AcademicMarks.student_id == data.student_id,
        AcademicMarks.subject == data.subject
    ).first()
    
    if record:
        record.internal_marks = data.internal_marks
        record.assignment_scores = data.assignment_scores
        record.exam_marks = data.exam_marks
    else:
        record = AcademicMarks(
            student_id=data.student_id,
            subject=data.subject,
            internal_marks=data.internal_marks,
            assignment_scores=data.assignment_scores,
            exam_marks=data.exam_marks
        )
        db.add(record)
        
    db.commit()
    return {"status": "success", "message": f"Marks updated for {data.subject}"}

@app.post("/api/attendance")
def update_attendance(data: AttendanceUpdateInput, db: Session = Depends(get_db), current_user: User = Depends(check_role(["Faculty", "HOD"]))):
    student = db.query(StudentProfile).filter(StudentProfile.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    student.attendance_pct = data.attendance_pct
    db.commit()
    return {"status": "success", "message": f"Attendance updated for {student.user.name}"}

@app.get("/api/prediction/{student_id}", response_model=PredictionOut)
def get_prediction(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    marks = student.marks
    avg_internal = sum(m.internal_marks for m in marks) / len(marks) if marks else 0.0
    avg_assign = sum(m.assignment_scores for m in marks) / len(marks) if marks else 0.0
    avg_exam = sum(m.exam_marks for m in marks if m.exam_marks is not None) / len(marks) if marks else 0.0
    
    assignments = student.assignments
    sub_rate = sum(1 for a in assignments if a.status in ["Submitted", "Graded"]) / len(assignments) if assignments else 1.0
    remarks = student.remarks
    avg_sentiment = sum(r.sentiment_score for r in remarks) / len(remarks) if remarks else 0.0
    
    ml_data = {
        "attendance_pct": student.attendance_pct,
        "internal_marks_avg": avg_internal,
        "assignment_score_avg": avg_assign,
        "exam_marks_avg": avg_exam,
        "assignment_completion_rate": sub_rate,
        "sentiment_score_avg": avg_sentiment
    }
    
    pred = predict_student_risk(ml_data)
    pass_prob = predict_exam_pass_probability(student.attendance_pct, avg_internal, sub_rate)
    
    return PredictionOut(
        student_id=student.id,
        name=student.user.name,
        risk_label=pred["risk_label"],
        risk_score=pred["risk_score"],
        exam_pass_probability=pass_prob
    )

@app.get("/api/risk/{student_id}/explain")
def get_explainability(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    marks = student.marks
    avg_internal = sum(m.internal_marks for m in marks) / len(marks) if marks else 0.0
    avg_assign = sum(m.assignment_scores for m in marks) / len(marks) if marks else 0.0
    avg_exam = sum(m.exam_marks for m in marks if m.exam_marks is not None) / len(marks) if marks else 0.0
    
    assignments = student.assignments
    sub_rate = sum(1 for a in assignments if a.status in ["Submitted", "Graded"]) / len(assignments) if assignments else 1.0
    remarks = student.remarks
    avg_sentiment = sum(r.sentiment_score for r in remarks) / len(remarks) if remarks else 0.0
    
    ml_data = {
        "attendance_pct": student.attendance_pct,
        "internal_marks_avg": avg_internal,
        "assignment_score_avg": avg_assign,
        "exam_marks_avg": avg_exam,
        "assignment_completion_rate": sub_rate,
        "sentiment_score_avg": avg_sentiment
    }
    
    explain = get_explainable_ai(ml_data)
    return explain

@app.get("/api/reports/pdf/{student_id}")
def download_pdf_report(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Authorization checks
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if current_user.role == "Student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if current_user.role == "Parent" and student.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    try:
        pdf_path = generate_student_pdf_report(db, student_id)
        return FileResponse(
            path=pdf_path,
            filename=os.path.basename(pdf_path),
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")
