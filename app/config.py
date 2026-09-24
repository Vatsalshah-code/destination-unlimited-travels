import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Secure private storage directory - isolated from web root!
STORAGE_DIR = BASE_DIR / "data" / "secure_storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Database file location
DB_PATH = BASE_DIR / "data" / "visa_system.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Security
SECRET_KEY = os.environ.get("VISA_SECRET_KEY", "visa-secure-system-token-key-2026-vfs-global")
SESSION_COOKIE_NAME = "visa_admin_session"
SESSION_DURATION_HOURS = 24

# File upload restrictions
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
MAX_TOTAL_UPLOAD_SIZE = 60 * 1024 * 1024  # 60 MB total request
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp"
}

# Service types
SERVICES = [
    "Passport Application",
    "Passport Renewal",
    "Visa Application",
    "Visa Renewal",
    "Other"
]

# Application statuses
STATUSES = [
    "New",
    "Documents Pending",
    "Under Review",
    "Additional Documents Required",
    "Submitted",
    "Completed"
]

# Document categories
DOCUMENT_CATEGORIES = {
    "passport": "Passport",
    "aadhaar": "Aadhaar Card",
    "pan": "PAN Card",
    "photo": "Photograph",
    "bank_docs": "Bank Documents",
    "previous_visa": "Previous Visa",
    "supporting_docs": "Supporting Documents"
}

# Default Admin User
DEFAULT_ADMIN_EMAIL = "admin@chintan.com"
DEFAULT_ADMIN_PASSWORD = "Chintan@123"
DEFAULT_ADMIN_NAME = "Destination Unlimited Travels Admin"
