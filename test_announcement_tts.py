import os
import sys
from datetime import date, timedelta

# Add root directory to python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.database import SessionLocal, User, Announcement, StudentProfile
from src.tts_service import generate_voice_file
from src.alerts import broadcast_announcement_to_telegram

def test_flow():
    print("--- Starting Announcement & TTS verification tests ---")
    db = SessionLocal()
    
    # 1. Fetch a Faculty/HOD user to create an announcement
    creator = db.query(User).filter(User.role.in_(["Faculty", "HOD"])).first()
    if not creator:
        print("❌ Error: No Faculty/HOD user found in database. Seed the database first.")
        db.close()
        return
        
    print(f"Using Creator: {creator.name} ({creator.role})")
    
    # 2. Define announcement attributes
    title = "Test Voice Alert: Technical Seminar"
    description = "A technical seminar on Advanced Artificial Intelligence will be conducted tomorrow at 10 AM in the main auditorium."
    
    print("\n--- Testing Edge-TTS Service ---")
    audio_filename = "test_verification.mp3"
    audio_path = os.path.join(BASE_DIR, "data", "announcements", audio_filename)
    
    # Clean previous test audio if exists
    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    # Generate MP3
    text_to_speak = f"Announcement: {title}. {description}"
    success = generate_voice_file(text_to_speak, audio_path)
    
    if success and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        print(f"✅ Edge-TTS Voice Generation Successful! Saved file: {audio_path}")
        print(f"File Size: {os.path.getsize(audio_path)} bytes")
    else:
        print("❌ Edge-TTS Voice Generation Failed.")
        db.close()
        return
        
    # 3. Create db announcement record
    print("\n--- Testing Database Insertion ---")
    new_ann = Announcement(
        title=title,
        description=description,
        created_by=creator.id,
        role=creator.role,
        target_department="All",
        target_year="All",
        target_section="All",
        priority="Important",
        publish_date=date.today(),
        expiry_date=date.today() + timedelta(days=2),
        audio_url=f"data/announcements/{audio_filename}"
    )
    
    db.add(new_ann)
    db.commit()
    db.refresh(new_ann)
    
    print(f"✅ Announcement created successfully! ID: {new_ann.id}")
    print(f"Title: {new_ann.title}")
    print(f"Audio Path: {new_ann.audio_url}")
    print(f"Creator Link: {new_ann.creator.name if new_ann.creator else 'Broken Relationship'}")
    
    # 4. Dry Run Broadcast function
    print("\n--- Testing Broadcast Logic (Simulation mode) ---")
    # Temporarily set Telegram tokens/chat ids if not present to print logs
    original_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    original_chat = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Set mock variables if not set
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    if not os.environ.get("TELEGRAM_CHAT_ID"):
        os.environ["TELEGRAM_CHAT_ID"] = "12345678"
        
    sent_count = broadcast_announcement_to_telegram(db, new_ann.id)
    print(f"Broadcasted to {sent_count} channels (including developer fallback).")
    
    # Restore environment variables
    if original_token is not None:
        os.environ["TELEGRAM_BOT_TOKEN"] = original_token
    else:
        del os.environ["TELEGRAM_BOT_TOKEN"]
        
    if original_chat is not None:
        os.environ["TELEGRAM_CHAT_ID"] = original_chat
    else:
        del os.environ["TELEGRAM_CHAT_ID"]
        
    # 5. Cleanup test data
    print("\n--- Cleaning Up Test Data ---")
    db.delete(new_ann)
    db.commit()
    print("✅ Database cleaned up successfully.")
    
    if os.path.exists(audio_path):
        os.remove(audio_path)
    print("✅ Files cleaned up successfully.")
    
    db.close()
    print("\n🎉 Verification Flow Completed successfully!")

if __name__ == "__main__":
    test_flow()
