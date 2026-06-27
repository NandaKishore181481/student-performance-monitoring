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
from src.database import AlertLog, StudentProfile, Announcement

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

def generate_personalized_ai_alert(
    student_name: str, 
    attendance: float, 
    risk_label: str, 
    weak_subjects: list, 
    risk_score: float,
    recipient_type: str = "parent",
    hod_name: str = "Head of Department",
    dept_name: str = "Student Performance Cell"
) -> str:
    """
    Generates a highly personalized, context-aware notification message using custom rule-based templates.
    Supports targeting parents or students with custom closings and actions.
    """
    if recipient_type == "parent":
        greeting = f"Dear Parent,\n\nHere is an academic status update for your ward, {student_name}.\n\n"
        status = f"Our AI-assisted evaluation has identified {student_name}'s current performance risk as *{risk_label}* (Risk Score: {risk_score:.1f}/100).\n"
    else:
        greeting = f"Dear {student_name},\n\nHere is an update on your academic performance this term.\n\n"
        status = f"Our AI-assisted evaluation has identified your current performance risk as *{risk_label}* (Risk Score: {risk_score:.1f}/100).\n"
    
    # 2. Attendance alerts
    attendance_part = ""
    if attendance < 75.0:
        attendance_part = f"- Attendance alert: Class attendance has fallen to {attendance:.1f}%, which is below the minimum threshold of 75%.\n"
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
        if recipient_type == "parent":
            action_part += "1. Schedule a counseling session with the HOD or class teacher.\n"
            action_part += "2. Ensure your ward attends remedial classes daily.\n"
            action_part += "3. Ensure submission of all pending assignments by this weekend."
        else:
            action_part += "1. Schedule a counseling session with your HOD or class teacher.\n"
            action_part += "2. Attend remedial classes daily.\n"
            action_part += "3. Submit all pending assignments by this weekend."
    elif risk_label == "Medium":
        if recipient_type == "parent":
            action_part += "1. Review weak subjects with your ward weekly.\n"
            action_part += "2. Monitor homework submission timelines."
        else:
            action_part += "1. Review weak subjects weekly.\n"
            action_part += "2. Ensure all homework is submitted on time."
    else:
        action_part += "1. Maintain the current study schedule.\n"
        action_part += "2. Explore enrichment projects in computer programming or advanced science."
        
    closing = f"\n\nRegards,\nDepartment of {dept_name} and Student Performance Cell"
    
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

def send_sms(db: Session, student_id: int, recipient_phone: str, message: str, full_body: str = None) -> bool:
    """
    Sends SMS using Twilio REST API, or falls back to Email-to-SMS Gateway if configured.
    Otherwise, defaults to Simulation Mode.
    """
    print(f"[{student_id}] Attempting SMS send to {recipient_phone}...")
    
    carrier_domain = os.getenv("CARRIER_GATEWAY_DOMAIN", "")
    
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
    elif os.getenv("TELEGRAM_BOT_TOKEN", ""):
        # Telegram Bot integration
        import requests
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Clean phone: remove non-digits
        clean_phone = "".join(filter(str.isdigit, recipient_phone))
        # Fallback to default developer chat ID only if it is a mock number (starts with 910000, 900000, 1555, 555) or empty.
        # Otherwise, attempt to send to the parent/student's actual custom Telegram Chat ID.
        is_mock = (
            clean_phone.startswith("910000") or 
            clean_phone.startswith("900000") or 
            clean_phone.startswith("1555") or 
            clean_phone.startswith("555") or 
            not clean_phone
        )
        
        chat_id = telegram_chat_id if is_mock else clean_phone
        
        # Use full body for Telegram if provided to make it easy for parents to see the detailed child info
        tg_message = full_body if full_body else message
        
        if not chat_id:
            print("Telegram Bot configured, but no valid Chat ID found.")
            sim_message = f"[SIMULATION - SMS/Telegram to {recipient_phone}]: {tg_message}"
            log_alert_to_db(db, student_id, "SMS", sim_message, "Sent (Simulated)")
            return True
            
        print(f"Routing SMS alert via Telegram to Chat ID: {chat_id}")
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": tg_message}
        
        import time
        # Pace requests to avoid hitting Telegram's rate limit (max 30 msgs/sec) when broadcasting
        time.sleep(0.05)
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            # Handle rate-limit retry
            if response.status_code == 429:
                try:
                    retry_after = response.json().get("parameters", {}).get("retry_after", 3)
                except Exception:
                    retry_after = 3
                print(f"Telegram rate limit hit. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                log_alert_to_db(db, student_id, "SMS", f"Telegram Chat: {chat_id}\nBody: {tg_message}", "Sent (Telegram)")
                print("Telegram SMS warning successfully delivered.")
                return True
            elif chat_id != telegram_chat_id and telegram_chat_id:
                print(f"Telegram API delivery failed for {chat_id} (Code {response.status_code}). Falling back to default developer Chat ID: {telegram_chat_id}")
                time.sleep(0.05)
                fallback_payload = {"chat_id": telegram_chat_id, "text": f"[Telegram Fallback from {chat_id}] {tg_message}"}
                fallback_response = requests.post(url, json=fallback_payload, timeout=10)
                if fallback_response.status_code == 429:
                    try:
                        retry_after = fallback_response.json().get("parameters", {}).get("retry_after", 3)
                    except Exception:
                        retry_after = 3
                    time.sleep(retry_after)
                    fallback_response = requests.post(url, json=fallback_payload, timeout=10)
                
                if fallback_response.status_code == 200:
                    log_alert_to_db(db, student_id, "SMS", f"Telegram Chat: {telegram_chat_id} (Fallback from {chat_id})\nBody: {tg_message}", "Sent (Telegram Fallback)")
                    print("Telegram SMS warning successfully delivered to developer chat ID (fallback).")
                    return True
            
            print(f"Telegram API delivery failed: {response.text}")
            log_alert_to_db(db, student_id, "SMS", message, f"Failed (Telegram: {response.text})")
            return False
        except Exception as e:
            print(f"Telegram API post failed: {e}")
            log_alert_to_db(db, student_id, "SMS", message, f"Failed (Telegram Exception: {e})")
            return False
    elif SMTP_USERNAME and SMTP_PASSWORD and carrier_domain:
        # Clean phone number: remove non-digits (e.g. +919676670515 -> 919676670515)
        clean_phone = "".join(filter(str.isdigit, recipient_phone))
        gateway_email = f"{clean_phone}@{carrier_domain}"
        print(f"Routing SMS for free via Email-to-SMS Gateway: {gateway_email}")
        
        # Dispatch SMS content as a clean email to the gateway
        success = send_email(db, student_id, gateway_email, "Academic Status Alert", message)
        if success:
            # Overwrite logged alert type to SMS
            log_alert_to_db(db, student_id, "SMS", f"Routed via gateway: {gateway_email}\nBody: {message}", "Sent (Gateway)")
            return True
        return False
    else:
        # Simulation Mode
        sim_message = f"[SIMULATION - SMS to {recipient_phone}]: {message}"
        log_alert_to_db(db, student_id, "SMS", sim_message, "Sent (Simulated)")
        print(f"Twilio SMS & Carrier Gateway credentials empty. {sim_message}")
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

def broadcast_announcement_to_telegram(db: Session, announcement_id: int) -> int:
    """
    Finds all students matching the target audience filters of the announcement
    and broadcasts the announcement text and AI voice MP3 to their Telegram chat IDs.
    Returns the count of successfully sent announcements.
    """
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        print(f"Announcement ID {announcement_id} not found.")
        return 0

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not telegram_token:
        print("Telegram bot token not configured. Skipping Telegram broadcast.")
        return 0

    import requests
    import time
    
    # 1. Fetch matching students
    students = db.query(StudentProfile).all()
    target_students = []
    for s in students:
        dept = s.class_section.split("-")[0] if "-" in s.class_section else "CS"
        sec_part = s.class_section.split("-")[1] if "-" in s.class_section else s.class_section
        year = "All"
        section = "All"
        if len(sec_part) >= 3 and sec_part.startswith("Y"):
            year = sec_part[1]
            section = sec_part[2:]
            
        if announcement.target_department != "All" and dept != announcement.target_department:
            continue
        if announcement.target_year != "All" and year != announcement.target_year:
            continue
        if announcement.target_section != "All" and section != announcement.target_section:
            continue
        target_students.append(s)

    print(f"Broadcasting announcement '{announcement.title}' to {len(target_students)} students...")
    sent_count = 0
    
    # Track unique chat IDs to avoid double-sending in this broadcast
    dispatched_chats = set()

    for student in target_students:
        # Collect chat IDs
        student_phone = student.user.phone if (student.user and student.user.phone) else ""
        parent_phone = student.parent.phone if student.parent else ""
        
        for recipient_phone, label in [(student_phone, "Student"), (parent_phone, "Parent")]:
            if not recipient_phone:
                continue
                
            clean_phone = "".join(filter(str.isdigit, recipient_phone))
            is_mock = (
                clean_phone.startswith("910000") or 
                clean_phone.startswith("900000") or 
                clean_phone.startswith("1555") or 
                clean_phone.startswith("555") or 
                not clean_phone
            )
            chat_id = telegram_chat_id if is_mock else clean_phone
            
            if chat_id in dispatched_chats:
                continue
            dispatched_chats.add(chat_id)
            
            # Format message text
            priority_tag = f"[{announcement.priority.upper()}] " if announcement.priority != "Normal" else ""
            msg_text = (
                f"📢 *NEW ANNOUNCEMENT* 📢\n\n"
                f"*Title:* {priority_tag}{announcement.title}\n"
                f"*Posted By:* {announcement.creator.name if announcement.creator else 'Admin'} ({announcement.role})\n"
                f"*Date:* {announcement.publish_date}\n\n"
                f"{announcement.description}"
            )
            
            # 1. Send Text Message
            url_msg = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": msg_text, "parse_mode": "Markdown"}
            
            try:
                time.sleep(0.05)  # Pace sending
                res = requests.post(url_msg, json=payload, timeout=10)
                if res.status_code == 200:
                    print(f"Sent announcement text to Chat ID: {chat_id}")
                else:
                    print(f"Failed to send text to {chat_id}: {res.text}")
                    if chat_id != telegram_chat_id and telegram_chat_id:
                        print("Trying fallback developer chat...")
                        fallback_payload = {"chat_id": telegram_chat_id, "text": f"[Telegram Fallback] {msg_text}", "parse_mode": "Markdown"}
                        requests.post(url_msg, json=fallback_payload, timeout=10)
            except Exception as e:
                print(f"Telegram send error: {e}")
                
            # 2. Send Voice MP3 File (if exists)
            if announcement.audio_url:
                # Find absolute file path
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                audio_path = os.path.join(base_dir, announcement.audio_url)
                
                if os.path.exists(audio_path):
                    url_voice = f"https://api.telegram.org/bot{telegram_token}/sendVoice"
                    try:
                        time.sleep(0.05)  # Pace sending
                        with open(audio_path, 'rb') as voice_file:
                            files = {'voice': voice_file}
                            data_payload = {'chat_id': chat_id, 'caption': f"AI Voice: {announcement.title}"}
                            res_voice = requests.post(url_voice, data=data_payload, files=files, timeout=15)
                            if res_voice.status_code == 200:
                                print(f"Sent announcement voice file to Chat ID: {chat_id}")
                            else:
                                print(f"Failed to send voice to {chat_id}: {res_voice.text}")
                                if chat_id != telegram_chat_id and telegram_chat_id:
                                    print("Trying fallback developer chat for voice...")
                                    voice_file.seek(0)
                                    fallback_data = {'chat_id': telegram_chat_id, 'caption': f"[Fallback] AI Voice: {announcement.title}"}
                                    requests.post(url_voice, data=fallback_data, files={'voice': voice_file}, timeout=15)
                    except Exception as e:
                        print(f"Telegram voice send error: {e}")
            
            sent_count += 1
            
    return sent_count


if __name__ == "__main__":
    # Test message builder
    msg = generate_personalized_ai_alert("John Doe", 62.5, "High", ["Mathematics", "Science"], 78.5)
    print("Generated AI Alert:\n", msg)
