import sqlite3
from datetime import datetime
from contextlib import contextmanager
from app.config import (
    DB_PATH,
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_NAME
)
from app.security import hash_password

def get_db_connection():
    """Create a connection with sqlite3.Row factory for dictionary-like access."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables and seed default admin user."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Clients Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                mobile TEXT NOT NULL,
                dob TEXT NOT NULL,
                address TEXT NOT NULL,
                service TEXT NOT NULL,
                country TEXT NOT NULL,
                reference_no TEXT,
                status TEXT NOT NULL DEFAULT 'New',
                consent_given INTEGER NOT NULL DEFAULT 1,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Documents Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                category TEXT NOT NULL,
                category_label TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                sha256_checksum TEXT NOT NULL,
                upload_status TEXT NOT NULL DEFAULT 'Uploaded',
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients (client_id) ON DELETE CASCADE
            );
        """)

        # Admin Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Admin',
                created_at TEXT NOT NULL
            );
        """)

        # Internal Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS internal_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                author_name TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients (client_id) ON DELETE CASCADE
            );
        """)

        # Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                actor_type TEXT NOT NULL,
                actor_identifier TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Notifications Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_type TEXT NOT NULL,
                recipient_identifier TEXT NOT NULL,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                delivery_channel TEXT NOT NULL DEFAULT 'EMAIL',
                status TEXT NOT NULL DEFAULT 'SENT',
                created_at TEXT NOT NULL
            );
        """)

        # Indexes for fast lookup and filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_client_id ON clients (client_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status ON clients (status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_service ON clients (service);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_client_id ON documents (client_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_client_id ON audit_logs (client_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_client_id ON notifications (client_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications (is_read);")

        # Seed default admin user if not exists
        cursor.execute("SELECT id FROM admin_users WHERE email = ?", (DEFAULT_ADMIN_EMAIL,))
        existing_admin = cursor.fetchone()
        if not existing_admin:
            now_iso = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO admin_users (email, password_hash, name, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                DEFAULT_ADMIN_EMAIL,
                hash_password(DEFAULT_ADMIN_PASSWORD),
                DEFAULT_ADMIN_NAME,
                "SuperAdmin",
                now_iso
            ))
            print(f"[DB] Initialized default admin user: {DEFAULT_ADMIN_EMAIL}")
