import os
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import bcrypt

# Database configuration
import shutil
import tempfile
import sqlite3
import hashlib

def get_db_path():
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
    local_db_path = os.path.join(os.path.dirname(DB_DIR), "data", "student_system.db")
    
    # Generate a unique database name to prevent permission collisions in shared /tmp folders
    unique_suffix = hashlib.md5(local_db_path.encode('utf-8')).hexdigest()[:12]
    
    # 1. Force /tmp fallback on Streamlit Cloud to prevent write-permission issues
    is_streamlit_cloud = (
        "STREAMLIT_SHARING_AUTHOR" in os.environ or 
        "STREAMLIT_RUNTIME" in os.environ or
        "mount/src" in __file__.replace("\\", "/")
    )
    
    if is_streamlit_cloud:
        tmp_dir = tempfile.gettempdir()
        writable_db_path = os.path.join(tmp_dir, f"student_system_{unique_suffix}.db")
        # Check if the existing DB is missing critical tables — if so, delete and recopy
        if os.path.exists(writable_db_path):
            try:
                conn = sqlite3.connect(writable_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='announcements'")
                ann_exists = cursor.fetchone()
                conn.close()
                if not ann_exists:
                    os.remove(writable_db_path)
            except Exception:
                pass

        if not os.path.exists(writable_db_path) and os.path.exists(local_db_path):
            try:
                shutil.copy2(local_db_path, writable_db_path)
            except Exception:
                pass
        return writable_db_path
        
    # 2. Strict SQLite write-capability check for other environments
    test_writable = False
    try:
        os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
        conn = sqlite3.connect(local_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS _write_test (id INTEGER)")
        cursor.execute("DROP TABLE _write_test")
        conn.commit()
        conn.close()
        test_writable = True
    except Exception:
        test_writable = False
        
    if not test_writable:
        tmp_dir = tempfile.gettempdir()
        writable_db_path = os.path.join(tmp_dir, f"student_system_{unique_suffix}.db")
        if not os.path.exists(writable_db_path) and os.path.exists(local_db_path):
            try:
                shutil.copy2(local_db_path, writable_db_path)
            except Exception:
                pass
        return writable_db_path
    return local_db_path

def _run_migrations(db_path):
    """Run lightweight schema migrations on an existing database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if 'department' column exists in 'users' table
        cursor.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cursor.fetchall()]
        if "department" in cols:
            conn.close()
            return
        # Add the column
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT")
        # Backfill existing HOD/Faculty rows with 'CSE' as default
        cursor.execute("UPDATE users SET department = 'CSE' WHERE role IN ('HOD', 'Faculty') AND department IS NULL")
        # Migrate old 'CS' department values to 'CSE'
        cursor.execute("UPDATE users SET department = 'CSE' WHERE department = 'CS' AND role IN ('HOD', 'Faculty')")
        conn.commit()
        conn.close()
    except Exception:
        pass

DB_PATH = get_db_path()
_run_migrations(DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
def hash_password(password: str) -> str:
    passwd = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(passwd, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'HOD', 'Faculty', 'Student', 'Parent'
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    department = Column(String, nullable=True)  # 'CSE', 'ECE', 'EEE', 'DS', 'AIML', 'CS'
    
    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, foreign_keys="StudentProfile.user_id")
    parent_profiles = relationship("StudentProfile", back_populates="parent", foreign_keys="StudentProfile.parent_id")

class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    roll_number = Column(String, unique=True, index=True, nullable=False)
    class_section = Column(String, nullable=False)
    attendance_pct = Column(Float, default=100.0)
    
    # Relationships
    user = relationship("User", back_populates="student_profile", foreign_keys=[user_id])
    parent = relationship("User", back_populates="parent_profiles", foreign_keys=[parent_id])
    marks = relationship("AcademicMarks", back_populates="student", cascade="all, delete-orphan")
    remarks = relationship("FacultyRemarks", back_populates="student", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="student", cascade="all, delete-orphan")
    alerts = relationship("AlertLog", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")

class AcademicMarks(Base):
    __tablename__ = "academic_marks"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    subject = Column(String, nullable=False)  # 'Mathematics', 'Science', 'English', 'History', 'Computer Science'
    internal_marks = Column(Float, nullable=False)  # Out of 30
    assignment_scores = Column(Float, nullable=False)  # Out of 20
    exam_marks = Column(Float, nullable=True)  # Out of 50
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship("StudentProfile", back_populates="marks")

class AttendanceRecord(Base):
    """Per-day, per-subject attendance log."""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    subject = Column(String, nullable=False)
    # 'Present', 'Absent', 'Late'
    status = Column(String, nullable=False, default="Present")

    student = relationship("StudentProfile", back_populates="attendance_records")

class FacultyRemarks(Base):
    __tablename__ = "faculty_remarks"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remark_text = Column(Text, nullable=False)
    sentiment_score = Column(Float, default=0.0)  # -1.0 to 1.0
    date_added = Column(Date, default=date.today)
    
    student = relationship("StudentProfile", back_populates="remarks")
    faculty = relationship("User")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="Pending")  # 'Pending', 'Submitted', 'Graded'
    score = Column(Float, nullable=True)  # Out of 100
    
    student = relationship("StudentProfile", back_populates="assignments")

class AlertLog(Base):
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    type = Column(String, nullable=False)  # 'SMS', 'Email', 'WhatsApp'
    message = Column(Text, nullable=False)
    status = Column(String, default="Sent")  # 'Sent', 'Failed'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("StudentProfile", back_populates="alerts")

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    audio_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # 'HOD', 'Faculty'
    target_department = Column(String, nullable=False, default="All")  # 'CS', 'ECE', 'All', etc.
    target_year = Column(String, nullable=False, default="All")  # '1', '2', '3', '4', 'All'
    target_section = Column(String, nullable=False, default="All")  # 'A', 'B', 'All', etc.
    priority = Column(String, nullable=False, default="Normal")  # 'Normal', 'Important', 'Urgent'
    publish_date = Column(Date, nullable=False, default=date.today)
    expiry_date = Column(Date, nullable=False, default=lambda: date.today() + timedelta(days=7))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    creator = relationship("User", foreign_keys=[created_by])

# Database session management helper
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database Seeding Function
def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if users already exist
        if db.query(User).count() > 0:
            print("Database already seeded.")
            return

        print("Seeding database from Excel template...")
        import os
        import pandas as pd
        from datetime import date
        
        DB_DIR = os.path.dirname(os.path.abspath(__file__))
        excel_path = os.path.join(os.path.dirname(DB_DIR), "college_data_template.xlsx")
        
        if not os.path.exists(excel_path):
            print(f"Excel file not found at {excel_path}. Skipping dynamic seed.")
            return
            
        dfs = pd.read_excel(excel_path, sheet_name=None)
        sheet_list = list(dfs.values())
        
        # 0: Instructions, 1: Departments, 2: Staff, 3: Students, 4: Marks, 5: Attendance
        
        # Extract HOD usernames from Departments sheet
        hod_map = {}
        if len(sheet_list) > 1:
            dept_df = sheet_list[1]
            dept_data = dept_df.iloc[1:].dropna(subset=["department_code"])
            for _, row in dept_data.iterrows():
                dept_code = str(row["department_code"]).strip()
                hod_usr = str(row["hod_username"]).strip() if pd.notna(row["hod_username"]) else ""
                if hod_usr:
                    hod_map[dept_code] = hod_usr

        # 1. Staff
        created_hods = set()
        if len(sheet_list) > 2:
            staff_df = sheet_list[2]
            staff_data = staff_df.iloc[1:].dropna(subset=["username", "password"])
            for _, row in staff_data.iterrows():
                usr = str(row["username"]).strip()
                dept = str(row["department_code"]).strip()
                
                # Determine role: HOD if username matches the hod_username in Departments sheet
                is_hod = (usr == hod_map.get(dept)) or ("HOD" in str(row["role"]).upper())
                role_str = "HOD" if is_hod else "Faculty"
                
                if is_hod:
                    created_hods.add(dept)
                    
                u = User(
                    username=usr,
                    hashed_password=hash_password(str(row["password"]).strip()),
                    name=str(row["full_name"]).strip(),
                    email=str(row["email"]).strip() if pd.notna(row["email"]) else "",
                    phone=str(row["phone"]).strip() if pd.notna(row["phone"]) else "",
                    role=role_str,
                    department=dept
                )
                db.add(u)
            db.commit()
            
        # Create fallback HODs if they were missing from the Staff sheet
        for dept_code, hod_usr in hod_map.items():
            if dept_code not in created_hods:
                fallback_hod = User(
                    username=hod_usr,
                    hashed_password=hash_password("hod123"),
                    name=f"HOD {dept_code}",
                    email=f"{hod_usr}@college.edu",
                    phone="",
                    role="HOD",
                    department=dept_code
                )
                db.add(fallback_hod)
        db.commit()

        # 2. Students & Parents
        if len(sheet_list) > 3:
            students_df = sheet_list[3]
            student_data = students_df.iloc[1:].dropna(subset=["username", "password"])
            for _, row in student_data.iterrows():
                p = User(
                    username=str(row["username"]).strip() + "_parent",
                    hashed_password=hash_password(str(row["password"]).strip()),
                    name=str(row["parent_name"]).strip() if pd.notna(row["parent_name"]) else "Parent",
                    email=str(row["parent_email"]).strip() if pd.notna(row["parent_email"]) else "",
                    phone=str(row["parent_phone"]).strip() if pd.notna(row["parent_phone"]) else "",
                    role="Parent"
                )
                db.add(p)
                db.commit()
                
                s = User(
                    username=str(row["username"]).strip(),
                    hashed_password=hash_password(str(row["password"]).strip()),
                    name=str(row["full_name"]).strip(),
                    email=str(row["email"]).strip() if pd.notna(row["email"]) else "",
                    phone=str(row["phone"]).strip() if pd.notna(row["phone"]) else "",
                    role="Student"
                )
                db.add(s)
                db.commit()
                
                # Check for string "nan" because pandas astype(str) sometimes creates "nan" strings
                raw_att = row["attendance_pct"]
                att = float(raw_att) if pd.notna(raw_att) and str(raw_att).lower() != "nan" else 0.0
                sec = f"{str(row['department_code']).strip()}-{str(row['section']).strip()}"
                
                profile = StudentProfile(
                    user_id=s.id,
                    parent_id=p.id,
                    roll_number=str(row["roll_number"]).strip(),
                    class_section=sec,
                    attendance_pct=att
                )
                db.add(profile)
            db.commit()

        # 3. Marks
        if len(sheet_list) > 4:
            marks_df = sheet_list[4]
            marks_data = marks_df.iloc[1:].dropna(subset=["roll_number", "subject"])
            for _, row in marks_data.iterrows():
                roll = str(row["roll_number"]).strip()
                profile = db.query(StudentProfile).filter(StudentProfile.roll_number == roll).first()
                if profile:
                    raw_inter = row["internal_marks"]
                    raw_assign = row["assignment_scores"]
                    raw_exam = row["exam_marks"]
                    
                    m = AcademicMarks(
                        student_id=profile.id,
                        subject=str(row["subject"]).strip(),
                        internal_marks=float(raw_inter) if pd.notna(raw_inter) and str(raw_inter).lower() != "nan" else 0.0,
                        assignment_scores=float(raw_assign) if pd.notna(raw_assign) and str(raw_assign).lower() != "nan" else 0.0,
                        exam_marks=float(raw_exam) if pd.notna(raw_exam) and str(raw_exam).lower() != "nan" else 0.0
                    )
                    db.add(m)
            db.commit()
            
        # 4. Attendance
        if len(sheet_list) > 5:
            att_df = sheet_list[5]
        if att_df is not None:
            att_data = att_df.iloc[1:].dropna(subset=["roll_number", "date"])
            for _, row in att_data.iterrows():
                roll = str(row["roll_number"]).strip()
                profile = db.query(StudentProfile).filter(StudentProfile.roll_number == roll).first()
                if profile:
                    try:
                        d = pd.to_datetime(row["date"]).date()
                    except:
                        d = date.today()
                    
                    record = AttendanceRecord(
                        student_id=profile.id,
                        date=d,
                        subject=str(row["subject"]).strip(),
                        status=str(row["status"]).strip()
                    )
                    db.add(record)
            db.commit()

        print("Database seeded successfully from Excel!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
