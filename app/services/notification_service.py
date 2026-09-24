from datetime import datetime
from typing import List, Dict, Optional
from app.database import get_db
from app.services.audit_service import AuditService

class NotificationService:
    @staticmethod
    def create_submission_notifications(client: Dict):
        """
        Creates automated notifications:
        1. Confirmation notice to the client.
        2. Alert notice to the admin staff.
        Includes Client ID in both.
        """
        client_id = client["client_id"]
        client_name = client["full_name"]
        client_email = client["email"]
        service_name = client["service"]
        country = client["country"]
        now_iso = datetime.now().isoformat()
        
        # 1. Official Client Confirmation Notice (Applicant-facing)
        client_title = f"Document Submission Confirmed - Application Ref: {client_id}"
        client_message = (
            f"Dear {client_name},\n\n"
            f"Thank you for submitting your visa/passport documents to our secure documentation center. "
            f"Your submission has been safely received, assigned a unique reference, and placed into your "
            f"private encrypted file vault.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"APPLICATION RECEIPT SUMMARY\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Client Reference ID : {client_id}\n"
            f"• Service Requested   : {service_name}\n"
            f"• Destination Country : {country}\n"
            f"• Submission Time     : {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
            f"• Initial Status       : Received & In Queue\n\n"
            f"WHAT HAPPENS NEXT?\n"
            f"1. Document Verification: An assigned case officer will verify your passport scan, "
            f"   identification documents, and financial records within 24-48 business hours.\n"
            f"2. Status Notification: You will receive real-time email updates if any additional "
            f"   clarification is required or when your dossier is submitted to the embassy.\n"
            f"3. Self-Service Tracking: You can check your live application status anytime at:\n"
            f"   http://127.0.0.1:8000/track (using your Client ID: {client_id})\n\n"
            f"Need assistance? Contact our client desk at support@visaflow.com.\n\n"
            f"Warm regards,\n"
            f"Client Services Division\n"
            f"Visa & Passport Documentation Center"
        )
        
        # 2. Urgent Staff Operational Alert (Admin / Case Officer facing)
        admin_title = f"🚨 [NEW INTAKE] Action Required: {client_name} ({client_id})"
        admin_message = (
            f"INTERNAL CASE OFFICER DISPATCH\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"A new client intake has been submitted and awaits document verification.\n\n"
            f"APPLICANT DOSSIER:\n"
            f"• Client ID    : {client_id}\n"
            f"• Applicant    : {client_name}\n"
            f"• Contact      : {client['mobile']} | {client_email}\n"
            f"• DOB          : {client.get('dob', 'N/A')}\n"
            f"• Service      : {service_name}\n"
            f"• Destination  : {country}\n"
            f"• Agency Ref   : {client.get('reference_no') or 'None'}\n\n"
            f"ACTION REQUIRED:\n"
            f"1. Open Admin Dashboard: http://127.0.0.1:8000/admin/dashboard\n"
            f"2. Inspect uploaded Passport bio page, Aadhaar/ID, and bank statements.\n"
            f"3. Update application status to 'Under Review' or 'Additional Documents Required'.\n"
            f"4. Download embassy submission ZIP bundle once verified."
        )
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Insert Client confirmation
            cursor.execute("""
                INSERT INTO notifications (
                    recipient_type, recipient_identifier, client_id,
                    title, message, is_read, delivery_channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "CLIENT", client_email, client_id,
                client_title, client_message, 0, "EMAIL", "SENT", now_iso
            ))
            
            # Insert Admin notification
            cursor.execute("""
                INSERT INTO notifications (
                    recipient_type, recipient_identifier, client_id,
                    title, message, is_read, delivery_channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "ADMIN", "staff@visaflow.com", client_id,
                admin_title, admin_message, 0, "IN_APP_ALERT", "UNREAD", now_iso
            ))

        AuditService.log(
            action="NOTIFICATION_SENT",
            actor_type="SYSTEM",
            actor_identifier="SystemMailer",
            client_id=client_id,
            details=f"Automated submission notifications created for Client ({client_email}) and Admin."
        )

    @staticmethod
    def send_status_update_notification(client: Dict, new_status: str, custom_message: Optional[str] = None):
        """Dispatches an email update to the client when their status changes."""
        client_id = client["client_id"]
        client_name = client["full_name"]
        client_email = client["email"]
        now_iso = datetime.now().isoformat()
        
        title = f"Application Status Update - {client_id}: {new_status}"
        body = (
            f"Dear {client_name},\n\n"
            f"The status of your application ({client_id}) has been updated to:\n"
            f"★ {new_status} ★\n\n"
        )
        if custom_message:
            body += f"Staff Note for you:\n\"{custom_message}\"\n\n"
            
        body += (
            f"If additional documents or actions are needed, please respond promptly or reach out to our team.\n\n"
            f"Best regards,\n"
            f"Visa & Passport Documentation Team"
        )

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (
                    recipient_type, recipient_identifier, client_id,
                    title, message, is_read, delivery_channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "CLIENT", client_email, client_id,
                title, body, 0, "EMAIL", "SENT", now_iso
            ))

        AuditService.log(
            action="STATUS_NOTIFICATION_SENT",
            actor_type="SYSTEM",
            actor_identifier="Admin",
            client_id=client_id,
            details=f"Status notification ({new_status}) sent to {client_email}"
        )

    @staticmethod
    def get_admin_notifications(unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """Fetch notifications directed to the admin staff."""
        with get_db() as conn:
            cursor = conn.cursor()
            if unread_only:
                cursor.execute("""
                    SELECT * FROM notifications
                    WHERE recipient_type = 'ADMIN' AND is_read = 0
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT * FROM notifications
                    WHERE recipient_type = 'ADMIN'
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_client_notifications(client_id: str) -> List[Dict]:
        """Fetch all notifications sent to a specific client."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notifications
                WHERE client_id = ?
                ORDER BY id DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def mark_all_admin_read():
        with get_db() as conn:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE recipient_type = 'ADMIN'")

    @staticmethod
    def mark_one_admin_read(notification_id: int):
        with get_db() as conn:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
