import hashlib
import hmac
import os
import re
import secrets
import time
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from app.config import SECRET_KEY, SESSION_DURATION_HOURS, SESSION_COOKIE_NAME

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    ).hex()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hashed_value: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, expected_hash = hashed_value.split("$", 1)
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False

def generate_session_token(user_id: int, email: str, role: str) -> str:
    """Generate a tamper-proof signed session token."""
    timestamp = int(time.time())
    payload = f"{user_id}:{email}:{role}:{timestamp}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}:{signature}"

def verify_session_token(token: str) -> Optional[dict]:
    """Validate token integrity, signature, and expiration."""
    if not token or ":" not in token:
        return None
    try:
        parts = token.split(":")
        if len(parts) != 5:
            return None
        user_id_str, email, role, ts_str, signature = parts
        payload = f"{user_id_str}:{email}:{role}:{ts_str}"
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        ts = int(ts_str)
        expiry = ts + (SESSION_DURATION_HOURS * 3600)
        if time.time() > expiry:
            return None
        
        return {
            "user_id": int(user_id_str),
            "email": email,
            "role": role,
            "created_at": ts
        }
    except Exception:
        return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and dangerous characters."""
    base = os.path.basename(filename)
    # Remove null bytes
    base = base.replace("\0", "")
    # Keep only safe alphanumeric, dash, underscore, dot
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)
    # Prevent hidden files
    clean = clean.lstrip(".")
    if not clean:
        clean = "document"
    return clean

async def get_current_admin(request: Request) -> dict:
    """FastAPI dependency to protect admin endpoints."""
    # Check session cookie or Authorization header
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    admin_data = verify_session_token(token)
    if not admin_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin_data
