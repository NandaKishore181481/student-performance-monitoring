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

        print("Seeding database...")
        
        # 1. Create HOD
        hod_user = User(
            username="hod",
            hashed_password=hash_password("hod123"),
            role="HOD",
            name="Dr. Eleanor Vance",
            email="hod.cse@university.edu",
            phone="+1555010099",
            department="CSE"
        )
        db.add(hod_user)
        
        # 2. Create Faculty
        fac1 = User(
            username="faculty1",
            hashed_password=hash_password("fac123"),
            role="Faculty",
            name="Prof. Alan Turing",
            email="alan.turing@university.edu",
            phone="+1555010088",
            department="CSE"
        )
        fac2 = User(
            username="faculty2",
            hashed_password=hash_password("fac123"),
            role="Faculty",
            name="Dr. Grace Hopper",
            email="grace.hopper@university.edu",
            phone="+1555010077",
            department="CSE"
        )
        db.add_all([fac1, fac2])
        db.commit()  # commit to get ids

        # Additional HODs and Faculty for other departments
        hod_ece = User(username="hod_ece", hashed_password=hash_password("hod123"), role="HOD", name="Dr. Ramesh Kumar", email="hod.ece@university.edu", phone="+1555020099", department="ECE")
        hod_eee = User(username="hod_eee", hashed_password=hash_password("hod123"), role="HOD", name="Dr. Sunita Sharma", email="hod.eee@university.edu", phone="+1555030099", department="EEE")
        hod_ds = User(username="hod_ds", hashed_password=hash_password("hod123"), role="HOD", name="Dr. Priya Nair", email="hod.ds@university.edu", phone="+1555040099", department="DS")
        hod_aiml = User(username="hod_aiml", hashed_password=hash_password("hod123"), role="HOD", name="Dr. Vikram Singh", email="hod.aiml@university.edu", phone="+1555050099", department="AIML")
        hod_cs = User(username="hod_cs", hashed_password=hash_password("hod123"), role="HOD", name="Dr. Kavitha Rao", email="hod.cybersec@university.edu", phone="+1555060099", department="CS")
        db.add_all([hod_ece, hod_eee, hod_ds, hod_aiml, hod_cs])
        
        fac_ece = User(username="faculty_ece", hashed_password=hash_password("fac123"), role="Faculty", name="Prof. Suresh Reddy", email="suresh.reddy@university.edu", phone="+1555020088", department="ECE")
        fac_eee = User(username="faculty_eee", hashed_password=hash_password("fac123"), role="Faculty", name="Prof. Lakshmi Devi", email="lakshmi.devi@university.edu", phone="+1555030088", department="EEE")
        fac_ds = User(username="faculty_ds", hashed_password=hash_password("fac123"), role="Faculty", name="Prof. Arjun Mehta", email="arjun.mehta@university.edu", phone="+1555040088", department="DS")
        fac_aiml = User(username="faculty_aiml", hashed_password=hash_password("fac123"), role="Faculty", name="Prof. Deepa Iyer", email="deepa.iyer@university.edu", phone="+1555050088", department="AIML")
        fac_cs = User(username="faculty_cs", hashed_password=hash_password("fac123"), role="Faculty", name="Prof. Rajesh Pillai", email="rajesh.pillai@university.edu", phone="+1555060088", department="CS")
        db.add_all([fac_ece, fac_eee, fac_ds, fac_aiml, fac_cs])
        db.commit()

        # 3. Create Parents
        parents_data = [
            # CSE parents
            ("parent1", "parent123", "Mr. Arthur Doe", "arthur.doe@email.com", "+1555010011"),
            ("parent2", "parent123", "Mrs. Mary Smith", "mary.smith@email.com", "+1555010022"),
            ("parent3", "parent123", "Mr. Robert Johnson", "robert.johnson@email.com", "+1555010033"),
            ("parent4", "parent123", "Mrs. Sarah Williams", "sarah.williams@email.com", "+1555010044"),
            # ECE parents
            ("parent5", "parent123", "Mr. Venkat Rao", "venkat.rao@email.com", "+1555020011"),
            ("parent6", "parent123", "Mrs. Anitha Kumari", "anitha.kumari@email.com", "+1555020022"),
            # EEE parents
            ("parent7", "parent123", "Mr. Mohan Das", "mohan.das@email.com", "+1555030011"),
            ("parent8", "parent123", "Mrs. Radha Krishnan", "radha.krishnan@email.com", "+1555030022"),
            # DS parents
            ("parent9", "parent123", "Mr. Sanjay Gupta", "sanjay.gupta@email.com", "+1555040011"),
            ("parent10", "parent123", "Mrs. Meena Patel", "meena.patel@email.com", "+1555040022"),
            # AIML parents
            ("parent11", "parent123", "Mr. Karthik Subramanian", "karthik.sub@email.com", "+1555050011"),
            ("parent12", "parent123", "Mrs. Divya Nandini", "divya.nandini@email.com", "+1555050022"),
            # CS (Cyber Security) parents
            ("parent13", "parent123", "Mr. Anil Verma", "anil.verma@email.com", "+1555060011"),
            ("parent14", "parent123", "Mrs. Pooja Sinha", "pooja.sinha@email.com", "+1555060022"),
        ]
        parents_list = []
        for username, password, name, email, phone in parents_data:
            p = User(
                username=username,
                hashed_password=hash_password(password),
                role="Parent",
                name=name,
                email=email,
                phone=phone
            )
            db.add(p)
            parents_list.append(p)
        db.commit()

        # 4. Create Students and Link Parents
        students_data = [
            # CSE students
            ("student1", "student123", "John Doe", "john.doe@student.edu", "+1555010111", "ROLL001", "CSE-A", 62.5, parents_list[0].id),
            ("student2", "student123", "Jane Smith", "jane.smith@student.edu", "+1555010222", "ROLL002", "CSE-A", 78.0, parents_list[1].id),
            ("student3", "student123", "Bob Johnson", "bob.johnson@student.edu", "+1555010333", "ROLL003", "CSE-B", 91.5, parents_list[2].id),
            ("student4", "student123", "Alice Williams", "alice.williams@student.edu", "+1555010444", "ROLL004", "CSE-B", 96.0, parents_list[3].id),
            # ECE students
            ("student5", "student123", "Ravi Shankar", "ravi.shankar@student.edu", "+1555020111", "ROLL005", "ECE-A", 74.0, parents_list[4].id),
            ("student6", "student123", "Sneha Reddy", "sneha.reddy@student.edu", "+1555020222", "ROLL006", "ECE-A", 85.5, parents_list[5].id),
            # EEE students
            ("student7", "student123", "Amit Kumar", "amit.kumar@student.edu", "+1555030111", "ROLL007", "EEE-A", 69.0, parents_list[6].id),
            ("student8", "student123", "Priya Sharma", "priya.sharma@student.edu", "+1555030222", "ROLL008", "EEE-A", 88.0, parents_list[7].id),
            # DS students
            ("student9", "student123", "Rahul Verma", "rahul.verma@student.edu", "+1555040111", "ROLL009", "DS-A", 72.5, parents_list[8].id),
            ("student10", "student123", "Anjali Nair", "anjali.nair@student.edu", "+1555040222", "ROLL010", "DS-A", 90.0, parents_list[9].id),
            # AIML students
            ("student11", "student123", "Deepak Patel", "deepak.patel@student.edu", "+1555050111", "ROLL011", "AIML-A", 67.5, parents_list[10].id),
            ("student12", "student123", "Kavya Menon", "kavya.menon@student.edu", "+1555050222", "ROLL012", "AIML-A", 92.0, parents_list[11].id),
            # CS (Cyber Security) students
            ("student13", "student123", "Suresh Babu", "suresh.babu@student.edu", "+1555060111", "ROLL013", "CS-A", 70.0, parents_list[12].id),
            ("student14", "student123", "Nithya Krishnan", "nithya.krishnan@student.edu", "+1555060222", "ROLL014", "CS-A", 87.5, parents_list[13].id),
        ]
        students_list = []
        for username, password, name, email, phone, roll, sec, att, parent_id in students_data:
            user = User(
                username=username,
                hashed_password=hash_password(password),
                role="Student",
                name=name,
                email=email,
                phone=phone
            )
            db.add(user)
            db.commit()  # Commit to get user ID
            
            profile = StudentProfile(
                user_id=user.id,
                parent_id=parent_id,
                roll_number=roll,
                class_section=sec,
                attendance_pct=att
            )
            db.add(profile)
            students_list.append(profile)
        db.commit()

        # Subjects: 'Mathematics', 'Science', 'English', 'History', 'Computer Science'
        # 5. Add Academic Marks
        # student1 (John Doe) - Low Marks (High Risk)
        # student2 (Jane Smith) - Medium Marks (Medium Risk)
        # student3 (Bob Johnson) - High Marks (Low Risk)
        # student4 (Alice Williams) - High Marks (Low Risk)
        subjects = ['Mathematics', 'Science', 'English', 'History', 'Computer Science']
        
        # Marks ranges: internal_marks out of 30, assignment_scores out of 20, exam_marks out of 50
        marks_data = {
            students_list[0].id: [  # John Doe
                ('Mathematics', 12.0, 8.0, 18.0),
                ('Science', 14.0, 10.0, 22.0),
                ('English', 18.0, 12.0, 28.0),
                ('History', 15.0, 11.0, 25.0),
                ('Computer Science', 11.0, 9.0, 19.0)
            ],
            students_list[1].id: [  # Jane Smith
                ('Mathematics', 21.0, 14.0, 35.0),
                ('Science', 18.0, 13.0, 31.0),
                ('English', 22.0, 16.0, 38.0),
                ('History', 20.0, 15.0, 34.0),
                ('Computer Science', 24.0, 17.0, 42.0)
            ],
            students_list[2].id: [  # Bob Johnson
                ('Mathematics', 28.0, 19.0, 47.0),
                ('Science', 27.0, 18.0, 46.0),
                ('English', 25.0, 17.0, 43.0),
                ('History', 24.0, 16.0, 41.0),
                ('Computer Science', 29.0, 19.0, 49.0)
            ],
            students_list[3].id: [  # Alice Williams
                ('Mathematics', 29.0, 19.5, 48.0),
                ('Science', 28.5, 19.0, 47.0),
                ('English', 27.0, 18.0, 45.0),
                ('History', 28.0, 19.0, 46.0),
                ('Computer Science', 30.0, 20.0, 50.0)
            ],
            students_list[4].id: [  # Ravi Shankar (ECE)
                ('Mathematics', 20.0, 13.0, 32.0),
                ('Science', 22.0, 14.0, 36.0),
                ('English', 19.0, 12.0, 30.0),
                ('History', 17.0, 11.0, 28.0),
                ('Computer Science', 18.0, 12.0, 29.0)
            ],
            students_list[5].id: [  # Sneha Reddy (ECE)
                ('Mathematics', 26.0, 17.0, 44.0),
                ('Science', 25.0, 16.0, 42.0),
                ('English', 24.0, 15.0, 40.0),
                ('History', 23.0, 15.0, 39.0),
                ('Computer Science', 27.0, 18.0, 45.0)
            ],
            students_list[6].id: [  # Amit Kumar (EEE)
                ('Mathematics', 15.0, 10.0, 24.0),
                ('Science', 16.0, 11.0, 26.0),
                ('English', 18.0, 12.0, 28.0),
                ('History', 14.0, 9.0, 22.0),
                ('Computer Science', 13.0, 8.0, 20.0)
            ],
            students_list[7].id: [  # Priya Sharma (EEE)
                ('Mathematics', 27.0, 18.0, 46.0),
                ('Science', 26.0, 17.0, 44.0),
                ('English', 25.0, 16.0, 42.0),
                ('History', 26.0, 17.0, 43.0),
                ('Computer Science', 28.0, 19.0, 48.0)
            ],
            students_list[8].id: [  # Rahul Verma (DS)
                ('Mathematics', 19.0, 13.0, 31.0),
                ('Science', 20.0, 14.0, 33.0),
                ('English', 21.0, 14.0, 34.0),
                ('History', 18.0, 12.0, 29.0),
                ('Computer Science', 22.0, 15.0, 36.0)
            ],
            students_list[9].id: [  # Anjali Nair (DS)
                ('Mathematics', 28.0, 19.0, 47.0),
                ('Science', 27.0, 18.0, 45.0),
                ('English', 26.0, 17.0, 44.0),
                ('History', 25.0, 16.0, 42.0),
                ('Computer Science', 29.0, 19.0, 48.0)
            ],
            students_list[10].id: [  # Deepak Patel (AIML)
                ('Mathematics', 16.0, 11.0, 25.0),
                ('Science', 17.0, 12.0, 27.0),
                ('English', 19.0, 13.0, 30.0),
                ('History', 15.0, 10.0, 23.0),
                ('Computer Science', 20.0, 14.0, 32.0)
            ],
            students_list[11].id: [  # Kavya Menon (AIML)
                ('Mathematics', 28.0, 18.0, 46.0),
                ('Science', 27.0, 17.0, 45.0),
                ('English', 26.0, 18.0, 44.0),
                ('History', 27.0, 18.0, 46.0),
                ('Computer Science', 29.0, 19.0, 49.0)
            ],
            students_list[12].id: [  # Suresh Babu (CS - Cyber Security)
                ('Mathematics', 18.0, 12.0, 29.0),
                ('Science', 19.0, 13.0, 31.0),
                ('English', 20.0, 14.0, 33.0),
                ('History', 17.0, 11.0, 27.0),
                ('Computer Science', 21.0, 14.0, 34.0)
            ],
            students_list[13].id: [  # Nithya Krishnan (CS - Cyber Security)
                ('Mathematics', 26.0, 17.0, 43.0),
                ('Science', 25.0, 16.0, 41.0),
                ('English', 24.0, 15.0, 40.0),
                ('History', 25.0, 16.0, 42.0),
                ('Computer Science', 27.0, 18.0, 46.0)
            ],
        }

        for student_id, sub_marks in marks_data.items():
            for sub, inter, assign, exam in sub_marks:
                m = AcademicMarks(
                    student_id=student_id,
                    subject=sub,
                    internal_marks=inter,
                    assignment_scores=assign,
                    exam_marks=exam
                )
                db.add(m)

        # 6. Add Faculty Remarks
        remarks_data = [
            (students_list[0].id, fac1.id, "Very poor attendance and struggles to stay awake in Math class.", -0.6),
            (students_list[0].id, fac2.id, "Struggles with assignments, needs urgent counseling.", -0.4),
            (students_list[1].id, fac1.id, "Good participation but distracted at times.", 0.2),
            (students_list[1].id, fac2.id, "Average academic performance. Can improve writing skills.", 0.1),
            (students_list[2].id, fac1.id, "Excellent analytic skills. Top performer in Science.", 0.9),
            (students_list[3].id, fac2.id, "Extremely diligent student. Demonstrates exceptional understanding.", 0.95),
        ]
        
        for stud_id, fac_id, text, sent in remarks_data:
            r = FacultyRemarks(
                student_id=stud_id,
                faculty_id=fac_id,
                remark_text=text,
                sentiment_score=sent
            )
            db.add(r)

        # 7. Add Assignments
        today = date.today()
        assignments_data = [
            # John Doe (student1)
            (students_list[0].id, "Calculus Practice Sheet", "Mathematics", today - timedelta(days=5), "Submitted", 60.0),
            (students_list[0].id, "Physics Lab Report 1", "Science", today - timedelta(days=2), "Pending", None),
            (students_list[0].id, "Database Design Project", "Computer Science", today + timedelta(days=3), "Pending", None),
            # Jane Smith (student2)
            (students_list[1].id, "Calculus Practice Sheet", "Mathematics", today - timedelta(days=5), "Submitted", 85.0),
            (students_list[1].id, "Physics Lab Report 1", "Science", today - timedelta(days=2), "Submitted", 78.0),
            (students_list[1].id, "Database Design Project", "Computer Science", today + timedelta(days=3), "Pending", None),
            # Bob Johnson (student3)
            (students_list[2].id, "Calculus Practice Sheet", "Mathematics", today - timedelta(days=5), "Submitted", 98.0),
            (students_list[2].id, "Physics Lab Report 1", "Science", today - timedelta(days=2), "Submitted", 95.0),
            (students_list[2].id, "Database Design Project", "Computer Science", today + timedelta(days=3), "Submitted", 96.0),
        ]

        for stud_id, title, sub, due, status, score in assignments_data:
            a = Assignment(
                student_id=stud_id,
                title=title,
                subject=sub,
                due_date=due,
                status=status,
                score=score
            )
            db.add(a)

        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
