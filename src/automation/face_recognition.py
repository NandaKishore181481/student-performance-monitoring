import os
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from src.database import StudentProfile, User

# ──────────────────────────────────────────────
# ArcFace via insightface (primary)
# Falls back to OpenCV Haar + Eigenfaces if unavailable
# ──────────────────────────────────────────────
try:
    import insightface
    from insightface.app import FaceAnalysis
    ARCFACE_AVAILABLE = True
except ImportError:
    ARCFACE_AVAILABLE = False

# Legacy dlib-based face_recognition (secondary fallback)
try:
    import face_recognition as fr_lib
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "data", "known_faces")
ARCFACE_MODEL_DIR = os.path.join(BASE_DIR, "models", "arcface")
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(ARCFACE_MODEL_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# ArcFace cosine similarity threshold
# Values in range [0, 1]; higher = stricter
# ArcFace embeddings are L2-normalised, so
# cosine sim = dot product of two unit vectors.
# ──────────────────────────────────────────────
ARCFACE_THRESHOLD = 0.35   # min cosine similarity to count as a match


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised ArcFace embeddings."""
    a = a / (np.linalg.norm(a) + 1e-10)
    b = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a, b))


class FaceAttendanceManager:
    """
    Attendance manager with a three-tier recognition strategy:

    1. **ArcFace** (insightface)   — most accurate (~99.8% LFW)
    2. **face_recognition** (dlib) — accurate fallback
    3. **Eigenfaces + Histogram**  — offline / lightweight fallback
    """

    def __init__(self):
        self.known_embeddings: list[np.ndarray] = []   # ArcFace 512-d or dlib 128-d
        self.known_face_names: list[str] = []
        self.known_student_ids: list[int] = []

        # Eigenfaces fallback structures
        self.pca = None
        self.knn = None
        self.faces_data: list[np.ndarray] = []
        self.faces_labels: list[int] = []

        # OpenCV Haar cascade for fallback detection
        self.cascade_classifier = None
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.cascade_classifier = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"Warning: Could not load Haar cascade: {e}")

        # Initialise ArcFace model
        self.arcface_app = None
        if ARCFACE_AVAILABLE:
            try:
                self.arcface_app = FaceAnalysis(
                    name="buffalo_sc",           # lightweight ArcFace-backed model
                    root=ARCFACE_MODEL_DIR,
                    providers=["CPUExecutionProvider"]
                )
                self.arcface_app.prepare(ctx_id=0, det_size=(640, 640))
                print("✅ ArcFace (insightface buffalo_sc) loaded successfully.")
            except Exception as e:
                print(f"⚠️  ArcFace init failed ({e}). Will fall back to dlib / Eigenfaces.")
                self.arcface_app = None

    # ──────────────────────────────────────────
    # Public: load registered student templates
    # ──────────────────────────────────────────
    def load_known_faces(self, db: Session):
        """
        Builds the in-memory gallery of known face embeddings from
        images stored in data/known_faces/<roll_number>.[jpg|jpeg|png].

        For students without a real photo a grey placeholder is saved and
        a random embedding is used (so the system still starts cleanly).
        """
        students = db.query(StudentProfile).all()

        self.known_embeddings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.faces_data = []
        self.faces_labels = []

        for idx, student in enumerate(students):
            image_path = self._find_student_image(student.roll_number, getattr(student, "photo_path", None))

            # Create placeholder if no photo exists
            if not image_path:
                image_path = os.path.join(KNOWN_FACES_DIR, f"{student.roll_number}.jpg")
                placeholder = np.full((200, 200, 3), 128, dtype=np.uint8)
                cv2.putText(
                    placeholder,
                    student.user.name[:15],
                    (5, 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (255, 255, 255),
                    1,
                )
                cv2.imwrite(image_path, placeholder)

            self.known_face_names.append(student.user.name)
            self.known_student_ids.append(student.id)

            # ── Tier 1: ArcFace embedding ──────────────────────────────
            embedding = self._extract_arcface_embedding(image_path)
            if embedding is None:
                # ── Tier 2: dlib embedding ─────────────────────────────
                embedding = self._extract_dlib_embedding(image_path)
            if embedding is None:
                # ── Tier 3: random 512-d placeholder ──────────────────
                embedding = np.random.normal(0, 0.1, 512).astype(np.float32)

            self.known_embeddings.append(embedding)

            # Also collect grey images for the Eigenfaces fallback
            try:
                img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img_gray is not None:
                    self.faces_data.append(cv2.resize(img_gray, (60, 60)).flatten())
                    self.faces_labels.append(idx)
            except Exception:
                pass

        # Train Eigenfaces (PCA + KNN) fallback model
        if len(self.faces_data) >= 2:
            try:
                X = np.array(self.faces_data, dtype=np.float32)
                y = np.array(self.faces_labels)
                n_comp = min(len(self.faces_data), 15)
                self.pca = PCA(n_components=n_comp, whiten=True)
                X_pca = self.pca.fit_transform(X)
                self.knn = KNeighborsClassifier(n_neighbors=1, metric="euclidean")
                self.knn.fit(X_pca, y)
                print(f"✅ Eigenfaces model trained on {len(self.faces_data)} images.")
            except Exception as e:
                print(f"Eigenfaces training failed: {e}")

        print(f"Gallery loaded: {len(self.known_face_names)} students.")

    # ──────────────────────────────────────────
    # Public: scan image & mark attendance
    # ──────────────────────────────────────────
    def scan_image_and_mark_attendance(
        self, db: Session, image_path: str, original_filename: str = None
    ) -> list[str]:
        """
        Runs face recognition on *image_path* and marks matched students present.

        Recognition pipeline:
          1. Filename roll-number hint (instant, zero-cost)
          2. ArcFace (insightface) — highest accuracy
          3. dlib face_recognition — good fallback
          4. OpenCV Haar + Eigenfaces/Histogram — offline fallback

        Returns list of student names whose attendance was updated.
        """
        # ── 0. Fast filename hint ─────────────────────────────────────
        if original_filename:
            for i, sid in enumerate(self.known_student_ids):
                student = db.query(StudentProfile).filter(StudentProfile.id == sid).first()
                if student and student.roll_number.lower() in original_filename.lower():
                    self._mark_student_present(db, sid)
                    return [student.user.name]

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            print(f"Error: could not read {image_path}")
            return []

        detected_names: list[str] = []

        # ── 1. ArcFace ────────────────────────────────────────────────
        if self.arcface_app is not None:
            detected_names = self._recognize_arcface(db, img_bgr)

        # ── 2. dlib fallback ──────────────────────────────────────────
        if not detected_names and FACE_REC_AVAILABLE:
            detected_names = self._recognize_dlib(db, img_bgr)

        # ── 3. Eigenfaces / Histogram fallback ────────────────────────
        if not detected_names and self.cascade_classifier is not None:
            detected_names = self._recognize_eigenfaces(db, img_bgr, image_path)

        return detected_names

    # ──────────────────────────────────────────
    # Tier 1 – ArcFace recognition
    # ──────────────────────────────────────────
    def _recognize_arcface(self, db: Session, img_bgr: np.ndarray) -> list[str]:
        """
        Detects faces with RetinaFace and matches embeddings via ArcFace
        using cosine similarity.
        """
        detected_names: list[str] = []
        try:
            faces = self.arcface_app.get(img_bgr)          # returns list of Face objects
            for face in faces:
                query_emb = face.embedding                  # 512-d L2-normalised float32
                if query_emb is None:
                    continue

                best_sim = -1.0
                best_idx = -1
                for i, known_emb in enumerate(self.known_embeddings):
                    sim = _cosine_similarity(query_emb, known_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_idx = i

                if best_idx >= 0 and best_sim >= ARCFACE_THRESHOLD:
                    name = self.known_face_names[best_idx]
                    sid = self.known_student_ids[best_idx]
                    self._mark_student_present(db, sid)
                    detected_names.append(name)
                    print(f"  ArcFace matched: {name}  (cos_sim={best_sim:.4f})")
                else:
                    print(f"  ArcFace: face detected but no match (best_sim={best_sim:.4f})")
        except Exception as e:
            print(f"ArcFace inference error: {e}")
        return detected_names

    # ──────────────────────────────────────────
    # Tier 2 – dlib face_recognition
    # ──────────────────────────────────────────
    def _recognize_dlib(self, db: Session, img_bgr: np.ndarray) -> list[str]:
        detected_names: list[str] = []
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            locations = fr_lib.face_locations(rgb)
            encodings = fr_lib.face_encodings(rgb, locations)

            # Build dlib-compatible gallery (128-d only)
            dlib_gallery = [
                e for e in self.known_embeddings if e.shape[0] == 128
            ]
            if not dlib_gallery:
                return []

            for enc in encodings:
                matches = fr_lib.compare_faces(dlib_gallery, enc, tolerance=0.55)
                if True in matches:
                    idx = matches.index(True)
                    name = self.known_face_names[idx]
                    sid = self.known_student_ids[idx]
                    self._mark_student_present(db, sid)
                    detected_names.append(name)
                    print(f"  dlib matched: {name}")
        except Exception as e:
            print(f"dlib recognition error: {e}")
        return detected_names

    # ──────────────────────────────────────────
    # Tier 3 – Eigenfaces + Histogram
    # ──────────────────────────────────────────
    def _recognize_eigenfaces(
        self, db: Session, img_bgr: np.ndarray, image_path: str
    ) -> list[str]:
        detected_names: list[str] = []
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.cascade_classifier.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3
        )

        for x, y, w, h in faces:
            cv2.rectangle(img_bgr, (x, y), (x + w, y + h), (255, 0, 0), 2)
            face_crop = gray[y : y + h, x : x + w]
            face_crop_100 = cv2.resize(face_crop, (100, 100))

            # --- Eigenfaces match ---
            best_eigen_idx = -1
            if self.pca is not None and self.knn is not None:
                try:
                    vec = cv2.resize(face_crop, (60, 60)).flatten().reshape(1, -1)
                    vec_pca = self.pca.transform(vec.astype(np.float32))
                    dist, _ = self.knn.kneighbors(vec_pca, n_neighbors=1)
                    if dist[0][0] < 18.0:
                        best_eigen_idx = int(self.knn.predict(vec_pca)[0])
                except Exception:
                    pass

            # --- Histogram correlation match (if Eigenfaces failed) ---
            best_hist_idx = -1
            best_hist_score = -1.0
            if best_eigen_idx == -1:
                for i, sid in enumerate(self.known_student_ids):
                    student = db.query(StudentProfile).filter(
                        StudentProfile.id == sid
                    ).first()
                    if not student:
                        continue
                    tmpl_path = self._find_student_image(student.roll_number)
                    if not tmpl_path:
                        continue
                    try:
                        tmpl = cv2.imread(tmpl_path, cv2.IMREAD_GRAYSCALE)
                        if tmpl is None:
                            continue
                        tmpl_100 = cv2.resize(tmpl, (100, 100))
                        h1 = cv2.calcHist([face_crop_100], [0], None, [256], [0, 256])
                        h2 = cv2.calcHist([tmpl_100], [0], None, [256], [0, 256])
                        cv2.normalize(h1, h1, 0, 1, cv2.NORM_MINMAX)
                        cv2.normalize(h2, h2, 0, 1, cv2.NORM_MINMAX)
                        score = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
                        if score > best_hist_score:
                            best_hist_score = score
                            best_hist_idx = i
                    except Exception:
                        pass

            match_idx = best_eigen_idx if best_eigen_idx != -1 else (
                best_hist_idx if best_hist_score > 0.35 else -1
            )

            if match_idx != -1:
                name = self.known_face_names[match_idx]
                sid = self.known_student_ids[match_idx]
                self._mark_student_present(db, sid)
                detected_names.append(name)
                tag = "Eigen" if best_eigen_idx != -1 else f"Hist({best_hist_score:.2f})"
                cv2.putText(
                    img_bgr, f"{name} [{tag}]", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
            else:
                cv2.putText(
                    img_bgr, "Unknown", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
                )

        cv2.imwrite(image_path, img_bgr)
        return detected_names

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────
    def _find_student_image(self, roll_number: str, photo_path: str | None = None) -> str | None:
        if photo_path:
            full_p = os.path.join(BASE_DIR, photo_path)
            if os.path.exists(full_p):
                return full_p

        for ext in (".jpg", ".jpeg", ".png"):
            path = os.path.join(KNOWN_FACES_DIR, f"{roll_number}{ext}")
            if os.path.exists(path):
                return path
        return None

    def _extract_arcface_embedding(self, image_path: str) -> np.ndarray | None:
        """Extract 512-d ArcFace embedding from a single face image."""
        if self.arcface_app is None:
            return None
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            faces = self.arcface_app.get(img)
            if faces:
                return faces[0].embedding     # already L2-normalised
        except Exception as e:
            print(f"  ArcFace embedding error for {image_path}: {e}")
        return None

    def _extract_dlib_embedding(self, image_path: str) -> np.ndarray | None:
        """Extract 128-d dlib embedding from a single face image."""
        if not FACE_REC_AVAILABLE:
            return None
        try:
            img = fr_lib.load_image_file(image_path)
            encs = fr_lib.face_encodings(img)
            if encs:
                return np.array(encs[0], dtype=np.float32)
        except Exception:
            pass
        return None

    def _mark_student_present(self, db: Session, student_id: int):
        student = db.query(StudentProfile).filter(
            StudentProfile.id == student_id
        ).first()
        if student:
            student.attendance_pct = min(100.0, student.attendance_pct + 1.2)
            db.commit()


# ──────────────────────────────────────────────
# Quick smoke-test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from src.database import SessionLocal, seed_database

    seed_database()
    db = SessionLocal()

    manager = FaceAttendanceManager()
    manager.load_known_faces(db)

    # Synthetic black frame (no real faces — good for checking startup)
    test_path = os.path.join(KNOWN_FACES_DIR, "test_feed.jpg")
    cv2.imwrite(test_path, np.zeros((480, 640, 3), dtype=np.uint8) + 50)

    present = manager.scan_image_and_mark_attendance(db, test_path)
    print("Attendance marked for:", present)

    if os.path.exists(test_path):
        os.remove(test_path)

    db.close()
