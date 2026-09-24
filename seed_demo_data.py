"""
Seed sample records to provide an immediate interactive demo experience
with realistic applicant data and mock document files.
"""
import io
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import init_db, get_db
from app.config import STORAGE_DIR
from app.services.storage import SecureStorageService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

def create_sample_pdf(title: str) -> bytes:
    return f"""%PDF-1.4
% Sample PDF Document for Visa & Passport System
% Title: {title}
% Timestamp: {datetime.now().isoformat()}
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 50 >>
stream
BT
/F1 24 Tf
100 700 Td
({title}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000060 00000 n 
0000000109 00000 n 
0000000168 00000 n 
0000000251 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
350
%%EOF""".encode("utf-8")

def create_sample_jpeg() -> bytes:
    # Minimal 1x1 valid JPEG bytes
    return bytes.fromhex(
        "ffd8ffe000104a46494600010101004800480000ffdb004300080606070605080707070909"
        "080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c3032"
        "3434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f00000105010101"
        "01010100000000000000000102030405060708090a0bffda0008010100003f007f00ffd9"
    )

def seed():
    init_db()
    print("[SEED] Initializing seed data...")

    demo_clients = [
        {
            "client_id": "VISA-2026-0001",
            "full_name": "Aarav Patel",
            "email": "aarav.patel@example.com",
            "mobile": "+91 98250 12345",
            "dob": "1991-03-15",
            "address": "B-402, Shivalik Residency, Satellite Road, Ahmedabad, Gujarat 380015",
            "service": "Visa Application",
            "country": "United States",
            "reference_no": "US-B1B2-2026",
            "status": "Under Review",
            "created_offset": 3,
            "docs": [
                ("passport", "Passport", "Aarav_Passport_Front_Back.pdf", create_sample_pdf("Aarav Patel - Passport Scan"), "application/pdf"),
                ("aadhaar", "Aadhaar Card", "Aarav_eAadhaar_Verified.pdf", create_sample_pdf("Aarav Patel - Aadhaar Card"), "application/pdf"),
                ("pan", "PAN Card", "Aarav_PAN_Card.pdf", create_sample_pdf("Aarav Patel - PAN Card"), "application/pdf"),
                ("photo", "Photograph", "Aarav_Photo_WhiteBg.jpg", create_sample_jpeg(), "image/jpeg"),
                ("bank_docs", "Bank Documents", "HDFC_Bank_Statement_6M.pdf", create_sample_pdf("HDFC Bank 6 Months Statement"), "application/pdf"),
                ("previous_visa", "Previous Visa", "Old_UK_Tourist_Visa.pdf", create_sample_pdf("Previous UK Tourist Visa"), "application/pdf"),
                ("supporting_docs", "Supporting Documents", "Conference_Invitation_Letter.pdf", create_sample_pdf("Tech Conference USA Invitation"), "application/pdf")
            ],
            "notes": [
                ("admin@visaflow.com", "DS-160 confirmation checked. Financial solvency verified ($15,000 equivalent)."),
                ("admin@visaflow.com", "Application moved to Under Review. Slot booking scheduled for VFS Mumbai.")
            ]
        },
        {
            "client_id": "VISA-2026-0002",
            "full_name": "Sneha Roy",
            "email": "sneha.roy@example.com",
            "mobile": "+91 98301 87654",
            "dob": "1994-08-22",
            "address": "12/4 Southern Avenue, Ballygunge, Kolkata, West Bengal 700029",
            "service": "Passport Renewal",
            "country": "United Kingdom",
            "reference_no": "TATKAAL-771",
            "status": "Submitted",
            "created_offset": 2,
            "docs": [
                ("passport", "Passport", "Sneha_Old_Passport_All_Pages.pdf", create_sample_pdf("Sneha Roy - Expired Passport"), "application/pdf"),
                ("aadhaar", "Aadhaar Card", "Sneha_Aadhaar_Card.pdf", create_sample_pdf("Sneha Roy - Aadhaar"), "application/pdf"),
                ("photo", "Photograph", "Sneha_Passport_Photo.jpg", create_sample_jpeg(), "image/jpeg"),
                ("supporting_docs", "Supporting Documents", "Electricity_Bill_Address_Proof.pdf", create_sample_pdf("Residential Address Proof - Electricity Bill"), "application/pdf")
            ],
            "notes": [
                ("admin@visaflow.com", "Police verification documents pre-checked."),
                ("admin@visaflow.com", "Tatkaal renewal dispatched to Regional Passport Office (RPO).")
            ]
        },
        {
            "client_id": "VISA-2026-0003",
            "full_name": "Rohan Mehra",
            "email": "rohan.mehra@example.com",
            "mobile": "+91 98110 44332",
            "dob": "1997-12-05",
            "address": "Flat 301, Silver Crest, Defense Colony, New Delhi 110024",
            "service": "Visa Application",
            "country": "France (Schengen)",
            "reference_no": "SCHEN-FR-991",
            "status": "Additional Documents Required",
            "created_offset": 1,
            "docs": [
                ("passport", "Passport", "Rohan_Passport_Scan.pdf", create_sample_pdf("Rohan Mehra Passport"), "application/pdf"),
                ("aadhaar", "Aadhaar Card", "Rohan_Aadhaar.pdf", create_sample_pdf("Rohan Mehra Aadhaar"), "application/pdf"),
                ("bank_docs", "Bank Documents", "ICICI_Statement.pdf", create_sample_pdf("ICICI Bank Statement 3M"), "application/pdf")
            ],
            "notes": [
                ("admin@visaflow.com", "Travel Insurance certificate missing 30,000 EUR coverage clause."),
                ("admin@visaflow.com", "Contacted applicant via email requesting updated Schengen Travel Insurance policy.")
            ]
        },
        {
            "client_id": "VISA-2026-0004",
            "full_name": "Meera Krishnan",
            "email": "meera.k@example.com",
            "mobile": "+91 94440 55667",
            "dob": "1988-06-30",
            "address": "84 Anna Salai, Guindy, Chennai, Tamil Nadu 600032",
            "service": "Visa Renewal",
            "country": "Canada",
            "reference_no": "CAN-V10-2026",
            "status": "Completed",
            "created_offset": 0,
            "docs": [
                ("passport", "Passport", "Meera_Passport_Bio.pdf", create_sample_pdf("Meera Krishnan Passport"), "application/pdf"),
                ("aadhaar", "Aadhaar Card", "Meera_Aadhaar.pdf", create_sample_pdf("Meera Krishnan Aadhaar"), "application/pdf"),
                ("photo", "Photograph", "Meera_Canada_Spec_Photo.jpg", create_sample_jpeg(), "image/jpeg"),
                ("previous_visa", "Previous Visa", "Previous_Canada_Visitor_Visa.pdf", create_sample_pdf("Expired 10-Yr Canadian Visa"), "application/pdf"),
                ("bank_docs", "Bank Documents", "SBI_Salary_Account_6M.pdf", create_sample_pdf("State Bank of India 6M Statement"), "application/pdf"),
                ("supporting_docs", "Supporting Documents", "Employment_Proof_TCS.pdf", create_sample_pdf("Employment Verification Letter"), "application/pdf")
            ],
            "notes": [
                ("admin@visaflow.com", "Biometrics completed at VFS Global Chennai."),
                ("admin@visaflow.com", "Passport stamped with 10-year multiple-entry visa. Dispatched to client via Bluedart courier.")
            ]
        }
    ]

    with get_db() as conn:
        cursor = conn.cursor()
        for c in demo_clients:
            cursor.execute("SELECT id FROM clients WHERE client_id = ?", (c["client_id"],))
            if cursor.fetchone():
                continue

            created_time = (datetime.now() - timedelta(days=c["created_offset"], hours=2)).isoformat()
            cursor.execute("""
                INSERT INTO clients (
                    client_id, full_name, email, mobile, dob, address,
                    service, country, reference_no, status, consent_given,
                    ip_address, user_agent, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '127.0.0.1', 'Mozilla/5.0 Demo Browser', ?, ?)
            """, (
                c["client_id"], c["full_name"], c["email"], c["mobile"], c["dob"],
                c["address"], c["service"], c["country"], c["reference_no"], c["status"],
                created_time, created_time
            ))

            # Create dedicated isolated folder
            client_dir = SecureStorageService.get_client_directory(c["client_id"])

            for (cat_key, cat_label, orig_name, file_bytes, mime) in c["docs"]:
                stored_name = f"{cat_key}_{orig_name}"
                file_path = client_dir / stored_name
                with open(file_path, "wb") as f:
                    f.write(file_bytes)

                import hashlib
                sha = hashlib.sha256(file_bytes).hexdigest()

                cursor.execute("""
                    INSERT INTO documents (
                        client_id, category, category_label, original_filename,
                        stored_filename, relative_path, file_size, mime_type,
                        sha256_checksum, upload_status, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Uploaded', ?)
                """, (
                    c["client_id"], cat_key, cat_label, orig_name,
                    stored_name, f"{c['client_id']}/{stored_name}",
                    len(file_bytes), mime, sha, created_time
                ))

            # Notes
            for (author, note) in c["notes"]:
                cursor.execute("""
                    INSERT INTO internal_notes (client_id, author_name, note_text, created_at)
                    VALUES (?, ?, ?, ?)
                """, (c["client_id"], author, note, created_time))

            # Audit log
            cursor.execute("""
                INSERT INTO audit_logs (
                    client_id, actor_type, actor_identifier, action, details, ip_address, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                c["client_id"], "CLIENT", c["email"], "SUBMISSION",
                f"Demo submission with {len(c['docs'])} documents.", "127.0.0.1", created_time
            ))

            # Notifications
            cursor.execute("""
                INSERT INTO notifications (
                    recipient_type, recipient_identifier, client_id, title, message, is_read, delivery_channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 0, 'EMAIL', 'SENT', ?)
            """, (
                "CLIENT", c["email"], c["client_id"],
                f"Document Submission Confirmed - Application {c['client_id']}",
                f"Your visa/passport application documents have been received successfully.", created_time
            ))
            cursor.execute("""
                INSERT INTO notifications (
                    recipient_type, recipient_identifier, client_id, title, message, is_read, delivery_channel, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 0, 'IN_APP_ALERT', 'UNREAD', ?)
            """, (
                "ADMIN", "staff@visaflow.com", c["client_id"],
                f"New Submission: {c['full_name']} ({c['client_id']})",
                f"New application received from {c['full_name']}.", created_time
            ))

            print(f"  + Seeded client {c['client_id']} ({c['full_name']}) with {len(c['docs'])} documents")

    print("[SEED] Successfully populated demo records!")

if __name__ == "__main__":
    seed()
