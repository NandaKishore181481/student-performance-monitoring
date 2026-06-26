import os
import sys
import argparse

# Ensure root directory is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.database import SessionLocal
from src.alerts import send_email, send_sms

def test_config(email_recipient=None, phone_recipient=None):
    db = SessionLocal()
    
    print("\n" + "="*50)
    print("      EduInsight AI - Live Alerts Diagnostic Tool")
    print("="*50)
    
    # 1. Test SMTP / Gmail configuration
    smtp_user = os.getenv("SMTP_USERNAME", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SENDER_EMAIL", "")
    
    print(f"\n--- SMTP Gmail Settings ---")
    print(f"SMTP Username: {smtp_user if smtp_user else '[Empty]'}")
    print(f"SMTP Password: {'[Configured]' if smtp_pass else '[Empty]'}")
    print(f"Sender Email:  {sender if sender else '[Empty]'}")
    
    if smtp_user and smtp_pass and email_recipient:
        print(f"\nSending real test email to: {email_recipient}...")
        test_subject = "EduInsight AI - Connection Verification"
        test_body = (
            "Hello!\n\nThis is a real live verification email sent from your EduInsight AI "
            "academic status monitor. If you received this, your Gmail SMTP configuration "
            "is working 100% correctly!\n\nRegards,\nOffice of Dean, Student Performance Cell"
        )
        email_success = send_email(db, 999, email_recipient, test_subject, test_body)
        if email_success:
            print("[SUCCESS] SMTP Email Check Passed!")
        else:
            print("[FAILED] SMTP Email Check Failed! Check your Google App Password settings.")
    elif email_recipient:
        print("[WARNING] Skipping Email Test: SMTP credentials are not configured in your .env file.")
        
    # 2. Test Twilio SMS configuration
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    print(f"\n--- Twilio SMS Settings ---")
    print(f"Twilio Account SID:  {twilio_sid if twilio_sid else '[Empty]'}")
    print(f"Twilio Auth Token:   {'[Configured]' if twilio_token else '[Empty]'}")
    print(f"Twilio Phone Number: {twilio_phone if twilio_phone else '[Empty]'}")
    
    if twilio_sid and twilio_token and twilio_phone and phone_recipient:
        print(f"\nSending real test SMS to: {phone_recipient}...")
        test_sms_body = "EduInsight AI Alert Verification: Your Twilio SMS integration is configured correctly!"
        sms_success = send_sms(db, 999, phone_recipient, test_sms_body)
        if sms_success:
            print("[SUCCESS] Twilio SMS Check Passed!")
        else:
            print("[FAILED] Twilio SMS Check Failed! Check your Twilio credentials and phone formats.")
    elif phone_recipient:
        print("[WARNING] Skipping SMS Test: Twilio credentials are not configured in your .env file.")
        
    # 3. Test Telegram Bot configuration
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    
    print(f"\n--- Telegram Bot Settings ---")
    print(f"Telegram Bot Token: {'[Configured]' if telegram_token else '[Empty]'}")
    print(f"Telegram Chat ID:   {telegram_chat_id if telegram_chat_id else '[Empty]'}")
    
    if telegram_token and telegram_chat_id and test_telegram:
        print(f"\nSending real test Telegram message to chat {telegram_chat_id}...")
        import requests
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": "Hello! This is a verification message from your EduInsight AI Telegram Bot."}
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("[SUCCESS] Telegram Bot Check Passed!")
            else:
                print(f"[FAILED] Telegram Bot Check Failed! API response: {res.text}")
        except Exception as e:
            print(f"[FAILED] Telegram Bot Check Failed! Error: {e}")
    elif test_telegram:
        print("[WARNING] Skipping Telegram Test: Telegram credentials are not configured in your .env file.")
        
    print("\n" + "="*50)
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Gmail SMTP, Twilio SMS & Telegram Bot Alert Configurations")
    parser.add_argument("--email", help="Recipient email address to test SMTP alerts")
    parser.add_argument("--phone", help="Recipient phone number (e.g. +91XXXXXXXXXX) to test Twilio SMS alerts")
    parser.add_argument("--telegram", action="store_true", help="Send a test message to your configured Telegram Chat ID")
    
    args = parser.parse_args()
    
    if not (args.email or args.phone or args.telegram):
        print("Usage: python test_credentials.py --email recipient@domain.com --phone +91XXXXXXXXXX --telegram")
        sys.exit(1)
        
    test_config(email_recipient=args.email, phone_recipient=args.phone, test_telegram=args.telegram)
