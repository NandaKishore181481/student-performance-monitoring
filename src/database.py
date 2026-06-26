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

DB_PATH = get_db_path()
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
            email="hod.cs@university.edu",
            phone="+1555010099"
        )
        db.add(hod_user)
        
        # 2. Create Faculty
        fac1 = User(
            username="faculty1",
            hashed_password=hash_password("fac123"),
            role="Faculty",
            name="Prof. Alan Turing",
            email="alan.turing@university.edu",
            phone="+1555010088"
        )
        fac2 = User(
            username="faculty2",
            hashed_password=hash_password("fac123"),
            role="Faculty",
            name="Dr. Grace Hopper",
            email="grace.hopper@university.edu",
            phone="+1555010077"
        )
        db.add_all([fac1, fac2])
        db.commit()  # commit to get ids

        # 3. Create Parents
        parents_data = [
            ("parent1", "parent123", "Mr. Arthur Doe", "arthur.doe@email.com", "+1555010011"),
            ("parent2", "parent123", "Mrs. Mary Smith", "mary.smith@email.com", "+1555010022"),
            ("parent3", "parent123", "Mr. Robert Johnson", "robert.johnson@email.com", "+1555010033"),
            ("parent4", "parent123", "Mrs. Sarah Williams", "sarah.williams@email.com", "+1555010044"),
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
            ("student1", "student123", "John Doe", "john.doe@student.edu", "+1555010111", "ROLL001", "CS-A", 62.5, parents_list[0].id),
            ("student2", "student123", "Jane Smith", "jane.smith@student.edu", "+1555010222", "ROLL002", "CS-A", 78.0, parents_list[1].id),
            ("student3", "student123", "Bob Johnson", "bob.johnson@student.edu", "+1555010333", "ROLL003", "CS-B", 91.5, parents_list[2].id),
            ("student4", "student123", "Alice Williams", "alice.williams@student.edu", "+1555010444", "ROLL004", "CS-B", 96.0, parents_list[3].id),
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
