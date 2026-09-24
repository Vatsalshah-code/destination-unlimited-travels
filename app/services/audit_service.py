from datetime import datetime
from typing import List, Dict, Optional
from app.database import get_db

class AuditService:
    @staticmethod
    def log(
        action: str,
        actor_type: str,
        actor_identifier: str,
        client_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Append an audit record for security, compliance, and traceability."""
        now_iso = datetime.now().isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (
                    client_id, actor_type, actor_identifier,
                    action, details, ip_address, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                actor_type,
                actor_identifier,
                action,
                details or "",
                ip_address or "127.0.0.1",
                now_iso
            ))

    @staticmethod
    def get_logs_for_client(client_id: str) -> List[Dict]:
        """Fetch chronological audit trail for a specific client record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_logs
                WHERE client_id = ?
                ORDER BY id DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_logs(limit: int = 100) -> List[Dict]:
        """Fetch system-wide recent audit logs."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
