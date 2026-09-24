from datetime import datetime
from app.database import get_db, init_db
from app.security import hash_password

init_db()

with get_db() as conn:
    c = conn.cursor()
    c.execute("SELECT id FROM admin_users WHERE email = 'admin@chintan.com'")
    row = c.fetchone()
    pwd_hash = hash_password("Chintan@123")
    if row:
        c.execute("UPDATE admin_users SET password_hash = ?, name = 'Chintan' WHERE email = 'admin@chintan.com'", (pwd_hash,))
        print("Updated admin@chintan.com in database.")
    else:
        c.execute(
            "INSERT INTO admin_users (email, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin@chintan.com", pwd_hash, "Chintan", "SuperAdmin", datetime.now().isoformat())
        )
        print("Inserted admin@chintan.com into database.")
