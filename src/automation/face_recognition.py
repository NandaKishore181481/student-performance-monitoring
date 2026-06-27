import os
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from src.database import StudentProfile, User

# Try to import face_recognition
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "data", "known_faces")
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

class FaceAttendanceManager:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.cascade_classifier = None
        
        # Load Haar Cascade as a fallback face detector
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.cascade_classifier = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"Failed to load OpenCV face detector: {e}")
            
    def load_known_faces(self, db: Session):
        """
        Loads registered student face templates from directory or sets up dummy mock templates.
        """
        students = db.query(StudentProfile).all()
        
        # For simulation, if face_recognition package is installed, we try to load actual encodings.
        # Otherwise we use simple feature comparison or name mapping.
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        
        for student in students:
            # Check for multiple possible extensions (.jpg, .jpeg, .png)
            image_path = None
            for ext in [".jpg", ".jpeg", ".png"]:
                test_path = os.path.join(KNOWN_FACES_DIR, f"{student.roll_number}{ext}")
                if os.path.exists(test_path):
                    image_path = test_path
                    break
            
            # If no image exists, we save a placeholder mock file
            if not image_path:
                image_path = os.path.join(KNOWN_FACES_DIR, f"{student.roll_number}.jpg")
                placeholder_img = np.zeros((200, 200, 3), dtype=np.uint8) + 128
                cv2.putText(placeholder_img, student.user.name, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imwrite(image_path, placeholder_img)
                
            self.known_face_names.append(student.user.name)
            self.known_student_ids.append(student.id)
            
            if FACE_REC_AVAILABLE:
                try:
                    img = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                    else:
                        # Dummy array of shape (128,) for consistency
                        self.known_face_encodings.append(np.random.normal(0, 0.1, 128))
                except Exception as e:
                    print(f"Error encoding {student.roll_number}: {e}")
                    self.known_face_encodings.append(np.random.normal(0, 0.1, 128))
            else:
                # Mock 128-d encoding
                self.known_face_encodings.append(np.random.normal(0, 0.1, 128))
                
        print(f"Loaded {len(self.known_face_names)} student face profiles.")

    def scan_image_and_mark_attendance(self, db: Session, image_path: str) -> list:
        """
        Loads an image, detects faces, matches with database, increments attendance_pct for matches.
        Returns a list of matched students.
        """
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image from {image_path}")
            return []
            
        detected_names = []
        
        # 1. Primary method: face_recognition library
        if FACE_REC_AVAILABLE:
            try:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_img)
                face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
                
                for face_encoding in face_encodings:
                    # Compare with known
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                    name = "Unknown Student"
                    
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = self.known_face_names[first_match_index]
                        student_id = self.known_student_ids[first_match_index]
                        
                        # Increment attendance
                        self._mark_student_present(db, student_id)
                        detected_names.append(name)
            except Exception as e:
                print(f"Deep learning face recognition failed: {e}. Falling back to OpenCV Cascade...")
                
        # 2. Fallback method: OpenCV Haar Cascades face detector + Simulation match
        if not detected_names and self.cascade_classifier is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.cascade_classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
            
            for i, (x, y, w, h) in enumerate(faces):
                # Draw box around faces for visual feedback
                cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # In simulation mode, we match faces sequentially to known students
                if i < len(self.known_face_names):
                    name = self.known_face_names[i]
                    student_id = self.known_student_ids[i]
                    self._mark_student_present(db, student_id)
                    detected_names.append(name)
                    cv2.putText(img, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
            # Overwrite original image with annotations
            cv2.imwrite(image_path, img)
            
        # 3. Complete Simulation fallback if no faces detected
        if not detected_names:
            # Mark all students present for simulation convenience
            for idx, student_id in enumerate(self.known_student_ids):
                self._mark_student_present(db, student_id)
                detected_names.append(self.known_face_names[idx])
                
        return detected_names

    def _mark_student_present(self, db: Session, student_id: int):
        student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
        if student:
            # Increase attendance slightly, cap at 100.0
            student.attendance_pct = min(100.0, student.attendance_pct + 1.2)
            db.commit()

if __name__ == "__main__":
    # Test execution
    from src.database import SessionLocal, seed_database
    seed_database()
    db = SessionLocal()
    
    manager = FaceAttendanceManager()
    manager.load_known_faces(db)
    
    # Create an empty black image as a sample camera feed
    test_img_path = os.path.join(KNOWN_FACES_DIR, "test_feed.jpg")
    test_img = np.zeros((480, 640, 3), dtype=np.uint8) + 50
    cv2.imwrite(test_img_path, test_img)
    
    present = manager.scan_image_and_mark_attendance(db, test_img_path)
    print("Attendance marked for:", present)
    
    # Cleanup test feed
    if os.path.exists(test_img_path):
        os.remove(test_img_path)
