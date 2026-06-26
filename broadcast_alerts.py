import os
import sys
import argparse

# Ensure root directory is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.database import SessionLocal, StudentProfile, AcademicMarks, User
from src.ml_models import predict_student_risk
from src.alerts import send_email, send_sms, send_whatsapp, generate_personalized_ai_alert

def get_student_ml_data(profile):
    marks = profile.marks
    avg_internal = sum(m.internal_marks for m in marks) / len(marks) if marks else 0.0
    avg_assign = sum(m.assignment_scores for m in marks) / len(marks) if marks else 0.0
    avg_exam = sum(m.exam_marks for m in marks if m.exam_marks is not None) / len(marks) if marks else 0.0
    
    assignments = profile.assignments
    sub_rate = sum(1 for a in assignments if a.status in ["Submitted", "Graded"]) / len(assignments) if assignments else 1.0
    remarks = profile.remarks
    avg_sentiment = sum(r.sentiment_score for r in remarks) / len(remarks) if remarks else 0.0
    
    return {
        "attendance_pct": profile.attendance_pct,
        "internal_marks_avg": avg_internal,
        "assignment_score_avg": avg_assign,
        "exam_marks_avg": avg_exam,
        "assignment_completion_rate": sub_rate,
        "sentiment_score_avg": avg_sentiment,
        "overall_academic": avg_internal + avg_assign + avg_exam
    }

def broadcast_warnings(target_risk: str):
    db = SessionLocal()
    try:
        student_list = db.query(StudentProfile).all()
        sent_count = 0
        
        print(f"\n==========================================")
        print(f"Broadcasting Warnings for Risk Category: {target_risk}")
        print(f"==========================================\n")
        
        for student in student_list:
            ml = get_student_ml_data(student)
            pred = predict_student_risk(ml)
            
            if target_risk != "All" and pred["risk_label"] != target_risk:
                continue
                
            student_email = student.user.email if student.user else ""
            parent_email = student.parent.email if student.parent else ""
            parent_phone = student.parent.phone if student.parent else ""
            
            # Fetch weak subjects (overall score < 40)
            weak_subs = [m.subject for m in student.marks if (m.internal_marks + m.assignment_scores + (m.exam_marks or 0)) < 40]
            
            # Dynamic HOD and Department lookup
            DEPT_MAP = {
                "CS": "Computer Science & Engineering",
                "ECE": "Electronics & Communication Engineering",
                "MECH": "Mechanical Engineering",
                "DS": "Data Science",
                "AIML": "Artificial Intelligence & Machine Learning"
            }
            dept_code = student.class_section.split("-")[0] if (student.class_section and "-" in student.class_section) else "CS"
            dept_name = DEPT_MAP.get(dept_code, "Computer Science & Engineering")
            
            # Query HOD user for this department
            hod_user = db.query(User).filter(User.username == f"hod_{dept_code.lower()}").first()
            hod_name = hod_user.name if hod_user else "Head of Department"
            
            # Generate custom alerts for student vs parent
            student_alert_text = generate_personalized_ai_alert(
                student.user.name,
                student.attendance_pct,
                pred["risk_label"],
                weak_subs,
                pred["risk_score"],
                recipient_type="student",
                hod_name=hod_name,
                dept_name=dept_name
            )
            
            parent_alert_text = generate_personalized_ai_alert(
                student.user.name,
                student.attendance_pct,
                pred["risk_label"],
                weak_subs,
                pred["risk_score"],
                recipient_type="parent",
                hod_name=hod_name,
                dept_name=dept_name
            )
            
            print(f"Sending to {student.user.name} (Risk: {pred['risk_label']}, Score: {pred['risk_score']:.1f})...")
            
            # Dispatch alerts
            if student_email:
                send_email(db, student.id, student_email, f"URGENT: Academic Status Warning - {student.user.name}", student_alert_text)
            if parent_email:
                send_email(db, student.id, parent_email, f"URGENT: Student Academic Warning - {student.user.name}", parent_alert_text)
            if parent_phone:
                sms_summary = f"EduInsight AI Alert: {student.user.name} identified in {pred['risk_label']} Risk zone (Risk Score: {pred['risk_score']:.1f}). Action plan dispatched via email."
                send_sms(db, student.id, parent_phone, sms_summary)
                send_whatsapp(db, student.id, parent_phone, sms_summary)
                
            sent_count += 1
            print("-" * 40)
            
        print(f"\nBroadcast complete! Alerts sent to {sent_count} student/parent accounts.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broadcast Academic Warnings via CLI")
    parser.add_argument(
        "--risk",
        choices=["High", "Medium", "Low", "All"],
        default="High",
        help="Target risk category for broadcasting alerts (default: High)"
    )
    args = parser.parse_args()
    broadcast_warnings(args.risk)
