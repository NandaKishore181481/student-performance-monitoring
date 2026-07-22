import os
import uuid
from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "students"
DEFAULT_AVATAR_PATH = UPLOAD_DIR / "default_avatar.png"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def ensure_upload_dirs():
    """Ensure upload directories and default avatar exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ensure_default_avatar()


def ensure_default_avatar():
    """Create a clean default avatar image if it does not already exist."""
    if not os.path.exists(DEFAULT_AVATAR_PATH):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        # Create a 200x200 soft grey avatar image
        img = Image.new("RGBA", (200, 200), color=(240, 242, 245, 255))
        draw = ImageDraw.Draw(img)
        # Head circle
        draw.ellipse([70, 40, 130, 100], fill=(160, 170, 185, 255))
        # Body curve
        draw.ellipse([35, 110, 165, 240], fill=(160, 170, 185, 255))
        img.save(DEFAULT_AVATAR_PATH, "PNG")


def validate_photo(file_name: str, file_size: int) -> tuple[bool, str]:
    """
    Validate student profile photo file name extension and size.
    Returns (is_valid, error_message).
    """
    if not file_name:
        return False, "No file selected."
    
    ext = file_name.split(".")[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type '.{ext}'. Only JPG, JPEG, and PNG files are allowed."
    
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of 2 MB."
    
    return True, ""


def save_student_photo(file_bytes: bytes, original_filename: str, roll_number: str) -> str:
    """
    Save student profile photo to static/uploads/students/ with a unique filename.
    Returns relative path for database storage (e.g. 'static/uploads/students/student_CS101_abcd1234.png').
    """
    ensure_upload_dirs()
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "png"
    unique_id = uuid.uuid4().hex[:8]
    clean_roll = "".join(c for c in roll_number if c.isalnum() or c in ("-", "_"))
    filename = f"student_{clean_roll}_{unique_id}.{ext}"
    full_path = UPLOAD_DIR / filename
    
    with open(full_path, "wb") as f:
        f.write(file_bytes)
        
    # Return path relative to BASE_DIR using forward slashes
    rel_path = f"static/uploads/students/{filename}"
    return rel_path


def delete_student_photo(relative_path: str | None) -> bool:
    """
    Safely delete old student profile photo file from disk.
    Does not delete default avatar or files outside student upload directory.
    """
    if not relative_path:
        return False
    
    try:
        full_path = BASE_DIR / relative_path
        default_full_path = DEFAULT_AVATAR_PATH.resolve()
        target_path = full_path.resolve()
        
        # Don't delete default avatar
        if target_path == default_full_path:
            return False
            
        # Security check: must be inside UPLOAD_DIR
        upload_dir_resolved = UPLOAD_DIR.resolve()
        if upload_dir_resolved in target_path.parents and target_path.exists():
            os.remove(target_path)
            return True
    except Exception as e:
        print(f"Warning: Failed to delete photo '{relative_path}': {e}")
    return False


def get_profile_photo_abs_path(relative_path: str | None, roll_number: str | None = None) -> str:
    """
    Get full absolute path for a student's profile photo.
    Falls back to data/known_faces or default avatar if not set / missing.
    """
    ensure_upload_dirs()
    
    if relative_path:
        full_p = BASE_DIR / relative_path
        if full_p.exists():
            return str(full_p)
            
    # Check known_faces fallback
    if roll_number:
        known_faces_dir = BASE_DIR / "data" / "known_faces"
        for ext in (".jpg", ".jpeg", ".png"):
            p = known_faces_dir / f"{roll_number}{ext}"
            if p.exists():
                return str(p)
                
    return str(DEFAULT_AVATAR_PATH)
