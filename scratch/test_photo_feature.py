import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.photo_utils import (
    validate_photo,
    save_student_photo,
    delete_student_photo,
    get_profile_photo_abs_path,
    ensure_default_avatar,
    DEFAULT_AVATAR_PATH
)
from src.database import SessionLocal, StudentProfile, _run_migrations, DB_PATH
from src.automation.face_recognition import FaceAttendanceManager


def test_photo_management():
    print("--- 1. Testing Photo Validation ---")
    valid, msg = validate_photo("avatar.png", 500 * 1024)
    assert valid, f"Validation failed for valid PNG: {msg}"
    print("[PASS] Valid PNG passed validation.")

    valid_jpg, msg = validate_photo("pic.jpg", 100 * 1024)
    assert valid_jpg, f"Validation failed for valid JPG: {msg}"
    print("[PASS] Valid JPG passed validation.")

    invalid_ext, msg = validate_photo("document.pdf", 100 * 1024)
    assert not invalid_ext, "Validation should fail for PDF file extension."
    print("[PASS] Invalid file extension properly rejected.")

    oversized, msg = validate_photo("huge.jpg", 3 * 1024 * 1024)
    assert not oversized, "Validation should fail for file > 2MB."
    print("[PASS] Oversized file (>2MB) properly rejected.")

    print("\n--- 2. Testing Photo Storage & Save ---")
    dummy_bytes = b"fake_image_bytes_content_for_testing"
    rel_path = save_student_photo(dummy_bytes, "test_pic.jpg", "CS9999")
    print(f"Saved relative path: {rel_path}")
    abs_path = BASE_DIR / rel_path
    assert abs_path.exists(), f"Saved file does not exist at {abs_path}"
    print("[PASS] Photo file saved successfully to disk.")

    print("\n--- 3. Testing Photo Retrieval & Fallback ---")
    retrieved_abs = get_profile_photo_abs_path(rel_path, "CS9999")
    assert retrieved_abs == str(abs_path), "Retrieved absolute path mismatch."
    print("[PASS] Absolute path resolved correctly.")

    ensure_default_avatar()
    default_retrieved = get_profile_photo_abs_path(None, "UNKNOWN_ROLL")
    assert default_retrieved == str(DEFAULT_AVATAR_PATH), "Default avatar fallback failed."
    print("[PASS] Default avatar fallback verified.")

    print("\n--- 4. Testing Safe Photo Deletion ---")
    deleted = delete_student_photo(rel_path)
    assert deleted, "Photo deletion failed."
    assert not abs_path.exists(), "Photo file should be removed from disk."
    print("[PASS] Profile photo safely deleted from disk.")

    # Attempt to delete default avatar (should be protected)
    deleted_default = delete_student_photo("static/uploads/students/default_avatar.png")
    assert not deleted_default, "Default avatar should NEVER be deleted."
    assert DEFAULT_AVATAR_PATH.exists(), "Default avatar must remain intact."
    print("[PASS] Default avatar protection verified.")

    print("\n--- 5. Testing ArcFace Compatibility ---")
    db = SessionLocal()
    mgr = FaceAttendanceManager()
    found_path = mgr._find_student_image("TEST_ROLL", photo_rel_path := "static/uploads/students/default_avatar.png")
    assert os.path.abspath(found_path) == os.path.abspath(os.path.join(BASE_DIR, photo_rel_path)), "ArcFace image lookup failed to prioritize photo_path."
    print("[PASS] ArcFace _find_student_image prioritizes student photo_path correctly.")

    print("\nALL STUDENT PROFILE PHOTO FEATURE TESTS PASSED SUCCESSFULY!")


if __name__ == "__main__":
    test_photo_management()
