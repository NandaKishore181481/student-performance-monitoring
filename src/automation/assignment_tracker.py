from datetime import date, timedelta
from sqlalchemy.orm import Session
from src.database import Assignment, StudentProfile
from src.alerts import send_email, send_sms, send_whatsapp

def check_pending_assignments_and_alert(db: Session) -> int:
    """
    Scans the database for assignments that are pending and due within the next 3 days, or already overdue.
    Sends reminders to students and parents and returns the count of reminders sent.
    """
    today = date.today()
    three_days_later = today + timedelta(days=3)
    
    # Query assignments that are pending and due <= 3 days from now
    urgent_assignments = db.query(Assignment).filter(
        Assignment.status == "Pending",
        Assignment.due_date <= three_days_later
    ).all()
    
    reminders_sent = 0
    
    # Group by student
    student_assignments = {}
    for assignment in urgent_assignments:
        student_id = assignment.student_id
        if student_id not in student_assignments:
            student_assignments[student_id] = []
        student_assignments[student_id].append(assignment)
        
    for student_id, assignments in student_assignments.items():
        student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
        if not student:
            continue
            
        student_name = student.user.name
        student_email = student.user.email if student.user else ""
        student_phone = student.user.phone if (student.user and student.user.phone) else ""
        parent_name = student.parent.name if student.parent else "Parent"
        parent_email = student.parent.email if student.parent else ""
        parent_phone = student.parent.phone if student.parent else ""
        
        # Build reminder summary
        overdue_list = []
        upcoming_list = []
        for ass in assignments:
            days_left = (ass.due_date - today).days
            if days_left < 0:
                overdue_list.append(f"'{ass.title}' ({ass.subject}) - OVERDUE by {abs(days_left)} days")
            elif days_left == 0:
                overdue_list.append(f"'{ass.title}' ({ass.subject}) - DUE TODAY")
            else:
                upcoming_list.append(f"'{ass.title}' ({ass.subject}) - due in {days_left} days (on {ass.due_date})")
                
        # Format the notification body for parent
        msg_body = f"Hello {parent_name},\n\nThis is an automated assignment tracker alert regarding your ward, {student_name}.\n\n"
        
        if overdue_list:
            msg_body += "CRITICAL: The following assignments are past due:\n"
            for item in overdue_list:
                msg_body += f"- {item}\n"
            msg_body += "\n"
            
        if upcoming_list:
            msg_body += "UPCOMING: The following assignments are due shortly:\n"
            for item in upcoming_list:
                msg_body += f"- {item}\n"
            msg_body += "\n"
            
        msg_body += "Please ensure these are submitted to avoid marks deduction.\n\nRegards,\nAcademic Assignment Tracker Office"
        
        # Format the notification body for student
        student_msg_body = f"Hello {student_name},\n\nThis is an automated assignment tracker alert regarding your pending assignments.\n\n"
        
        if overdue_list:
            student_msg_body += "CRITICAL: The following assignments are past due:\n"
            for item in overdue_list:
                student_msg_body += f"- {item}\n"
            student_msg_body += "\n"
            
        if upcoming_list:
            student_msg_body += "UPCOMING: The following assignments are due shortly:\n"
            for item in upcoming_list:
                student_msg_body += f"- {item}\n"
            student_msg_body += "\n"
            
        student_msg_body += "Please ensure these are submitted to avoid marks deduction.\n\nRegards,\nAcademic Assignment Tracker Office"
        
        # Send alerts
        # 1. Email to Student
        if student_email:
            send_email(db, student_id, student_email, "URGENT: Assignment Submission Reminders", student_msg_body)
            
        # 2. Email to Parent
        if parent_email and parent_email != student_email:
            send_email(db, student_id, parent_email, "URGENT: Student Assignment Submission Reminders", msg_body)
            
        # Clean phone numbers for comparison
        clean_student_phone = "".join(filter(str.isdigit, student_phone))
        clean_parent_phone = "".join(filter(str.isdigit, parent_phone))
        
        # 3. SMS / WhatsApp to Student
        if student_phone:
            student_sms_body = f"Assignment Reminder: You have {len(assignments)} pending assignment(s) that require urgent submission. Details sent to your email."
            send_sms(db, student_id, student_phone, student_sms_body, full_body=student_msg_body)
            send_whatsapp(db, student_id, student_phone, student_sms_body)
            
        # 4. SMS / WhatsApp to Parent
        if parent_phone and clean_parent_phone != clean_student_phone:
            sms_body = f"Assignment Reminder for {student_name}: You have {len(assignments)} pending assignment(s) that require urgent submission. Details sent to your email."
            send_sms(db, student_id, parent_phone, sms_body, full_body=msg_body)
            send_whatsapp(db, student_id, parent_phone, sms_body)
            
        reminders_sent += 1
        
    return reminders_sent

if __name__ == "__main__":
    from src.database import SessionLocal, seed_database
    seed_database()
    db = SessionLocal()
    count = check_pending_assignments_and_alert(db)
    print(f"Triggered assignment tracker. Reminders dispatched: {count}")
