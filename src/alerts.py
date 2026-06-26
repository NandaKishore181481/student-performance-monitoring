import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from twilio.rest import Client
from src.database import AlertLog

# Credentials Configuration
# In production, these should be loaded from env variables.
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886") # Sandbox number

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "alerts@studentmonitor.edu")

def generate_personalized_ai_alert(student_name: str, attendance: float, risk_label: str, weak_subjects: list, risk_score: float) -> str:
    """
    Generates a highly personalized, context-aware notification message using custom rule-based templates.
    """
    greeting = f"Dear Parent, here is an academic status update for your ward, {student_name}.\n\n"
    
    # 1. Performance status
    status = f"Our AI-assisted evaluation has identified {student_name}'s current performance risk as *{risk_label}* (Risk Score: {risk_score:.1f}/100).\n"
    
    # 2. Attendance alerts
    attendance_part = ""
    if attendance < 75.0:
        attendance_part = f"- Attendance alert: The class attendance has fallen to {attendance:.1f}%, which is below the minimum threshold of 75%.\n"
    else:
        attendance_part = f"- Attendance status: Attendance is healthy at {attendance:.1f}%.\n"
        
    # 3. Weak subjects alerts
    subjects_part = ""
    if weak_subjects:
        sub_list = ", ".join(weak_subjects)
        subjects_part = f"- Academic focus required: Low grades were recorded in: {sub_list}.\n"
    else:
        subjects_part = "- Academic status: Academic marks are satisfactory across all subjects.\n"
        
    # 4. Action items
    action_part = "\nRecommended action plan:\n"
    if risk_label == "High":
        action_part += "1. Schedule a counseling session with the class teacher.\n"
        action_part += "2. Ensure daily attendance in remedial classes.\n"
        action_part += "3. Submit all pending assignments by this weekend."
    elif risk_label == "Medium":
        action_part += "1. Review weak subjects weekly.\n"
        action_part += "2. Monitor homework submission timeline."
    else:
        action_part += "1. Maintain the current study schedule.\n"
        action_part += "2. Explore enrichment projects in computer programming or advanced science."
        
    closing = "\n\nRegards,\nOffice of Dean, Student Performance Cell"
    
    return greeting + status + attendance_part + subjects_part + action_part + closing

def log_alert_to_db(db: Session, student_id: int, alert_type: str, message: str, status: str = "Sent") -> AlertLog:
    """Logs the alert event into SQLite database."""
    log_entry = AlertLog(
        student_id=student_id,
        type=alert_type,
        message=message,
        status=status
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def send_sms(db: Session, student_id: int, recipient_phone: str, message: str) -> bool:
    """
    Sends SMS using Twilio REST API. Falls back to Simulation Log mode if credentials are not configured.
    """
    print(f"[{student_id}] Attempting SMS send to {recipient_phone}...")
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=recipient_phone
            )
            log_alert_to_db(db, student_id, "SMS", message, "Sent")
            print("SMS successfully sent via Twilio.")
            return True
        except Exception as e:
            log_alert_to_db(db, student_id, "SMS", message, "Failed")
            print(f"Twilio SMS delivery failed: {e}")
            return False
    else:
        # Simulation Mode
        sim_message = f"[SIMULATION - SMS to {recipient_phone}]: {message}"
        log_alert_to_db(db, student_id, "SMS", sim_message, "Sent (Simulated)")
        print(f"Twilio SMS credentials empty. {sim_message}")
        return True

def send_whatsapp(db: Session, student_id: int, recipient_phone: str, message: str) -> bool:
    """
    Sends WhatsApp messages using Twilio WhatsApp API. Falls back to Simulation Log if credentials missing.
    """
    print(f"[{student_id}] Attempting WhatsApp send to {recipient_phone}...")
    
    formatted_to = f"whatsapp:{recipient_phone}" if not recipient_phone.startswith("whatsapp:") else recipient_phone
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=formatted_to
            )
            log_alert_to_db(db, student_id, "WhatsApp", message, "Sent")
            print("WhatsApp successfully sent via Twilio.")
            return True
        except Exception as e:
            log_alert_to_db(db, student_id, "WhatsApp", message, "Failed")
            print(f"Twilio WhatsApp delivery failed: {e}")
            return False
    else:
        # Simulation Mode
        sim_message = f"[SIMULATION - WhatsApp to {formatted_to}]: {message}"
        log_alert_to_db(db, student_id, "WhatsApp", sim_message, "Sent (Simulated)")
        print(f"Twilio WhatsApp credentials empty. {sim_message}")
        return True

def send_email(db: Session, student_id: int, recipient_email: str, subject: str, message: str) -> bool:
    """
    Sends email alert via SMTP. Falls back to Simulation Log mode if credentials missing.
    """
    print(f"[{student_id}] Attempting Email send to {recipient_email}...")
    
    if SMTP_USERNAME and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            log_alert_to_db(db, student_id, "Email", f"Subject: {subject}\n{message}", "Sent")
            print("Email successfully sent via SMTP.")
            return True
        except Exception as e:
            log_alert_to_db(db, student_id, "Email", f"Subject: {subject}\n{message}", "Failed")
            print(f"SMTP Email delivery failed: {e}")
            return False
    else:
        # Simulation Mode
        sim_message = f"[SIMULATION - Email to {recipient_email}]\nSubject: {subject}\nBody: {message}"
        log_alert_to_db(db, student_id, "Email", sim_message, "Sent (Simulated)")
        print(f"SMTP Credentials empty. {sim_message}")
        return True

if __name__ == "__main__":
    # Test message builder
    msg = generate_personalized_ai_alert("John Doe", 62.5, "High", ["Mathematics", "Science"], 78.5)
    print("Generated AI Alert:\n", msg)
