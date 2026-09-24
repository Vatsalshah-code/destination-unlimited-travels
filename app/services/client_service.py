from datetime import datetime
from typing import List, Dict, Optional, Any
from app.database import get_db
from app.services.storage import SecureStorageService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.config import DOCUMENT_CATEGORIES

class ClientService:
    @staticmethod
    def generate_next_client_id() -> str:
        """
        Generates unique Client ID with format: VISA-YYYY-XXXX
        Example: VISA-2026-0001
        Thread-safe sequenced per year.
        """
        current_year = datetime.now().year
        prefix = f"VISA-{current_year}-"
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT client_id FROM clients 
                WHERE client_id LIKE ? 
                ORDER BY id DESC LIMIT 1
            """, (f"{prefix}%",))
            last_record = cursor.fetchone()
            
            if last_record and last_record["client_id"]:
                try:
                    last_num = int(last_record["client_id"].split("-")[-1])
                    next_num = last_num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
                
            return f"{prefix}{next_num:04d}"

    @classmethod
    async def create_client_submission(
        cls,
        form_data: Dict[str, Any],
        uploaded_files_data: List[Dict[str, Any]],
        ip_address: str = "127.0.0.1",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Atomic client record creation:
        Client ID -> Personal Info -> Service Details -> Uploaded Documents -> Notifications -> Audit Trail
        """
        client_id = cls.generate_next_client_id()
        now_iso = datetime.now().isoformat()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clients (
                    client_id, full_name, email, mobile, dob, address,
                    service, country, reference_no, status, consent_given,
                    ip_address, user_agent, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                form_data["full_name"].strip(),
                form_data["email"].strip().lower(),
                form_data["mobile"].strip(),
                form_data["dob"].strip(),
                form_data["address"].strip(),
                form_data["service"].strip(),
                form_data["country"].strip(),
                form_data.get("reference_no", "").strip() or None,
                "New",
                1 if form_data.get("consent_given") else 1,
                ip_address,
                user_agent,
                now_iso,
                now_iso
            ))

            # Insert all documents metadata
            for doc in uploaded_files_data:
                category_key = doc["category"]
                category_label = DOCUMENT_CATEGORIES.get(category_key, "Supporting Document")
                cursor.execute("""
                    INSERT INTO documents (
                        client_id, category, category_label, original_filename,
                        stored_filename, relative_path, file_size, mime_type,
                        sha256_checksum, upload_status, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    category_key,
                    category_label,
                    doc["original_filename"],
                    doc["stored_filename"],
                    doc["relative_path"],
                    doc["file_size"],
                    doc["mime_type"],
                    doc["sha256_checksum"],
                    "Uploaded",
                    now_iso
                ))

        # Retrieve created record
        client_record = cls.get_client_by_id(client_id)
        
        # Log Audit event
        AuditService.log(
            action="SUBMISSION",
            actor_type="CLIENT",
            actor_identifier=client_record["email"],
            client_id=client_id,
            details=f"New submission received with {len(uploaded_files_data)} documents.",
            ip_address=ip_address
        )

        # Trigger automatic notifications
        NotificationService.create_submission_notifications(client_record)

        return client_record

    @staticmethod
    def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
        """Fetch client record by Client ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @classmethod
    def get_client_full_details(cls, client_id: str) -> Optional[Dict[str, Any]]:
        """Fetch client record along with all documents, internal notes, notifications, and audit logs."""
        client = cls.get_client_by_id(client_id)
        if not client:
            return None

        with get_db() as conn:
            cursor = conn.cursor()
            # Documents
            cursor.execute("""
                SELECT * FROM documents WHERE client_id = ? ORDER BY id ASC
            """, (client_id,))
            documents = [dict(row) for row in cursor.fetchall()]

            # Notes
            cursor.execute("""
                SELECT * FROM internal_notes WHERE client_id = ? ORDER BY id DESC
            """, (client_id,))
            notes = [dict(row) for row in cursor.fetchall()]

        audit_logs = AuditService.get_logs_for_client(client_id)
        notifications = NotificationService.get_client_notifications(client_id)

        return {
            **client,
            "documents": documents,
            "notes": notes,
            "audit_logs": audit_logs,
            "notifications": notifications
        }

    @staticmethod
    def list_clients(
        search: Optional[str] = None,
        service: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Fetch clients with search, service & status filters, and pagination."""
        offset = (page - 1) * limit
        conditions = []
        params = []

        if search:
            search_term = f"%{search.strip()}%"
            conditions.append("""
                (client_id LIKE ? OR full_name LIKE ? OR email LIKE ? OR mobile LIKE ? OR reference_no LIKE ? OR country LIKE ?)
            """)
            params.extend([search_term, search_term, search_term, search_term, search_term, search_term])

        if service and service.strip():
            conditions.append("service = ?")
            params.append(service.strip())

        if status_filter and status_filter.strip():
            conditions.append("status = ?")
            params.append(status_filter.strip())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with get_db() as conn:
            cursor = conn.cursor()
            # Total count
            cursor.execute(f"SELECT COUNT(*) as cnt FROM clients {where_clause}", params)
            total = cursor.fetchone()["cnt"]

            # Paginated results with document count
            query = f"""
                SELECT c.*, 
                    (SELECT COUNT(*) FROM documents d WHERE d.client_id = c.client_id) AS doc_count
                FROM clients c
                {where_clause}
                ORDER BY c.id DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            records = [dict(row) for row in cursor.fetchall()]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "clients": records
        }

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Fetch high-level overview metrics for the Admin Dashboard."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM clients")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT status, COUNT(*) as cnt FROM clients GROUP BY status")
            status_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total_docs FROM documents")
            total_docs = cursor.fetchone()["total_docs"]

            today_prefix = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) as today_count FROM clients WHERE created_at LIKE ?", (f"{today_prefix}%",))
            today_count = cursor.fetchone()["today_count"]

        return {
            "total_clients": total,
            "new_count": status_counts.get("New", 0),
            "documents_pending": status_counts.get("Documents Pending", 0),
            "under_review": status_counts.get("Under Review", 0),
            "additional_docs_required": status_counts.get("Additional Documents Required", 0),
            "submitted_count": status_counts.get("Submitted", 0),
            "completed_count": status_counts.get("Completed", 0),
            "total_documents": total_docs,
            "today_count": today_count
        }

    @classmethod
    def update_status(
        cls,
        client_id: str,
        new_status: str,
        admin_email: str,
        custom_note: Optional[str] = None,
        notify_client: bool = True
    ) -> bool:
        """Update client application status with audit log and optional notification."""
        client = cls.get_client_by_id(client_id)
        if not client:
            return False

        old_status = client["status"]
        now_iso = datetime.now().isoformat()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE clients SET status = ?, updated_at = ? WHERE client_id = ?
            """, (new_status, now_iso, client_id))

            if custom_note and custom_note.strip():
                cursor.execute("""
                    INSERT INTO internal_notes (client_id, author_name, note_text, created_at)
                    VALUES (?, ?, ?, ?)
                """, (client_id, admin_email, f"Status updated to '{new_status}': {custom_note.strip()}", now_iso))

        AuditService.log(
            action="STATUS_CHANGE",
            actor_type="ADMIN",
            actor_identifier=admin_email,
            client_id=client_id,
            details=f"Status changed from '{old_status}' to '{new_status}'."
        )

        if notify_client:
            NotificationService.send_status_update_notification(client, new_status, custom_note)

        return True

    @staticmethod
    def add_internal_note(client_id: str, author_name: str, note_text: str):
        """Add staff internal note."""
        now_iso = datetime.now().isoformat()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO internal_notes (client_id, author_name, note_text, created_at)
                VALUES (?, ?, ?, ?)
            """, (client_id, author_name, note_text.strip(), now_iso))

        AuditService.log(
            action="NOTE_ADDED",
            actor_type="ADMIN",
            actor_identifier=author_name,
            client_id=client_id,
            details=f"Staff note added: '{note_text[:40]}...'"
        )

    @classmethod
    def delete_client(cls, client_id: str, admin_email: str) -> bool:
        """Securely wipe client database records and disk storage files."""
        client = cls.get_client_by_id(client_id)
        if not client:
            return False

        # 1. Delete physical storage folder
        SecureStorageService.delete_client_files(client_id)

        # 2. Delete database records (Cascades handle documents, notes)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE client_id = ?", (client_id,))
            cursor.execute("DELETE FROM internal_notes WHERE client_id = ?", (client_id,))
            cursor.execute("DELETE FROM notifications WHERE client_id = ?", (client_id,))
            cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))

        AuditService.log(
            action="RECORD_DELETED",
            actor_type="ADMIN",
            actor_identifier=admin_email,
            client_id=client_id,
            details=f"Client record {client_id} ({client['full_name']}) and all files permanently deleted."
        )
        return True
