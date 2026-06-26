import os
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from src.database import StudentProfile, AcademicMarks, FacultyRemarks, Assignment, get_db

# Create data directory if not exists
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

TRAINING_DATA_PATH = os.path.join(DATA_DIR, "student_training_data.csv")

def extract_student_features(db: Session) -> pd.DataFrame:
    """
    Extract features from the SQLite database for prediction.
    """
    students = db.query(StudentProfile).all()
    
    data = []
    for student in students:
        # Calculate averages for marks
        marks = student.marks
        if marks:
            avg_internal = np.mean([m.internal_marks for m in marks])
            avg_assignment = np.mean([m.assignment_scores for m in marks])
            avg_exam = np.mean([m.exam_marks for m in marks if m.exam_marks is not None])
            if np.isnan(avg_exam):
                avg_exam = 0.0
        else:
            avg_internal, avg_assignment, avg_exam = 0.0, 0.0, 0.0
            
        # Calculate assignment submission rate
        assignments = student.assignments
        if assignments:
            submitted = sum(1 for a in assignments if a.status in ["Submitted", "Graded"])
            sub_rate = submitted / len(assignments)
        else:
            sub_rate = 1.0  # assume completed if none assigned
            
        # Calculate faculty remark sentiment average
        remarks = student.remarks
        if remarks:
            avg_sentiment = np.mean([r.sentiment_score for r in remarks])
        else:
            avg_sentiment = 0.0  # neutral
            
        # Calculate overall academic score (out of 100)
        overall_academic = avg_internal + avg_assignment + avg_exam
        
        data.append({
            "student_id": student.id,
            "roll_number": student.roll_number,
            "name": student.user.name,
            "attendance_pct": student.attendance_pct,
            "internal_marks_avg": avg_internal,
            "assignment_score_avg": avg_assignment,
            "exam_marks_avg": avg_exam,
            "assignment_completion_rate": sub_rate,
            "sentiment_score_avg": avg_sentiment,
            "overall_academic": overall_academic
        })
        
    return pd.DataFrame(data)

def generate_synthetic_training_data(n_samples: int = 150) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset for training ML models.
    """
    np.random.seed(42)
    
    # Generate random features
    attendance = np.random.uniform(50, 100, n_samples)
    
    # Internal marks out of 30, highly correlated with attendance
    internal = np.clip(attendance * 0.25 + np.random.normal(5, 3, n_samples), 5, 30)
    
    # Assignment score out of 20
    assignment_score = np.clip(attendance * 0.16 + np.random.normal(3, 2, n_samples), 4, 20)
    
    # Exam marks out of 50
    exam = np.clip((internal + assignment_score) * 1.0 + np.random.normal(0, 5, n_samples), 10, 50)
    
    # Assignment completion rate (0.0 to 1.0)
    completion = np.clip(attendance / 100.0 - np.random.uniform(0, 0.2, n_samples), 0.0, 1.0)
    
    # Faculty remarks sentiment (-1.0 to 1.0)
    sentiment = np.clip((attendance - 75.0) / 25.0 + np.random.normal(0.0, 0.3, n_samples), -1.0, 1.0)
    
    df = pd.DataFrame({
        "attendance_pct": attendance,
        "internal_marks_avg": internal,
        "assignment_score_avg": assignment_score,
        "exam_marks_avg": exam,
        "assignment_completion_rate": completion,
        "sentiment_score_avg": sentiment
    })
    
    # Calculate Risk Score (0 to 100)
    # Higher score = Higher Risk.
    # Risk factors: low attendance, low marks, low completion, negative sentiment.
    risk_score = (
        (100.0 - df["attendance_pct"]) * 0.35 +
        (30.0 - df["internal_marks_avg"]) * 0.25 * (100.0 / 30.0) +
        (20.0 - df["assignment_score_avg"]) * 0.15 * (100.0 / 20.0) +
        (1.0 - df["assignment_completion_rate"]) * 10.0 +
        (1.0 - df["sentiment_score_avg"]) * 7.5
    )
    
    # Add noise to risk score
    risk_score += np.random.normal(0, 5, n_samples)
    risk_score = np.clip(risk_score, 0, 100)
    
    # Map to classes: High, Medium, Low
    def label_risk(score):
        if score >= 60:
            return "High"
        elif score >= 35:
            return "Medium"
        else:
            return "Low"
            
    df["risk_score"] = risk_score
    df["risk_label"] = df["risk_score"].apply(label_risk)
    
    # Save to file
    df.to_csv(TRAINING_DATA_PATH, index=False)
    print(f"Generated synthetic training data with {n_samples} samples at {TRAINING_DATA_PATH}")
    return df

if __name__ == "__main__":
    generate_synthetic_training_data()
