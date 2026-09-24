import os
import sys
import io
import zipfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.config import STORAGE_DIR, DB_PATH
from app.database import init_db, get_db

client = TestClient(app)

def setup_module(module):
    """Ensure database schema is cleanly initialized before running tests."""
    import shutil
    init_db()
    if STORAGE_DIR.exists():
        for item in STORAGE_DIR.iterdir():
            if item.is_dir() and item.name.startswith("VISA-"):
                shutil.rmtree(item, ignore_errors=True)
    with get_db() as conn:
        conn.execute("DELETE FROM documents;")
        conn.execute("DELETE FROM internal_notes;")
        conn.execute("DELETE FROM notifications;")
        conn.execute("DELETE FROM audit_logs;")
        conn.execute("DELETE FROM clients;")

def test_01_public_form_renders():
    """Verify that public client intake form loads successfully."""
    response = client.get("/upload-documents")
    assert response.status_code == 200
    assert "Submit Your Visa & Passport Documents" in response.text
    assert "Passport (Bio-Data & Address)" in response.text
    assert "Aadhaar Card" in response.text
    assert "Privacy Notice & Client Consent" in response.text

def test_02_client_one_submission_creates_record_and_isolated_storage():
    """
    Test submission for Client 1 (John Doe):
    - Should receive unique Client ID like VISA-2026-0001
    - Files should be saved strictly into data/secure_storage/VISA-2026-0001/
    - Should automatically generate notifications and audit log
    """
    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy passport pdf file content")
    dummy_aadhaar = io.BytesIO(b"%PDF-1.4 dummy aadhaar pdf file content")
    dummy_photo = io.BytesIO(b"\xff\xd8\xff\xe0 dummy jpeg photo bytes")
    dummy_sup1 = io.BytesIO(b"%PDF-1.4 dummy flight ticket supporting doc")
    dummy_sup2 = io.BytesIO(b"%PDF-1.4 dummy hotel booking supporting doc")

    files = [
        ("passport", ("John_Passport.pdf", dummy_pdf, "application/pdf")),
        ("aadhaar", ("John_Aadhaar.pdf", dummy_aadhaar, "application/pdf")),
        ("photo", ("John_Photo.jpg", dummy_photo, "image/jpeg")),
        ("supporting_docs", ("Flight_Ticket.pdf", dummy_sup1, "application/pdf")),
        ("supporting_docs", ("Hotel_Booking.pdf", dummy_sup2, "application/pdf")),
    ]

    data = {
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "mobile": "+91 9876543210",
        "dob": "1992-05-14",
        "address": "123 Elm Street, City Center, Mumbai 400001",
        "service": "Visa Application",
        "country": "United States",
        "reference_no": "US-2026-B1B2",
        "consent_given": "true"
    }

    response = client.post("/api/submit-documents", data=data, files=files)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    client_id = res_data["client_id"]
    assert client_id.startswith("VISA-2026-")
    assert res_data["uploaded_documents_count"] == 5

    # Verify physical file isolation
    client_dir = STORAGE_DIR / client_id
    assert client_dir.exists()
    assert client_dir.is_dir()

    saved_files = list(client_dir.glob("*"))
    assert len(saved_files) == 5

    # Verify database record
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["full_name"] == "John Doe"
        assert row["status"] == "New"

        # Verify documents in DB
        cursor.execute("SELECT * FROM documents WHERE client_id = ?", (client_id,))
        docs = cursor.fetchall()
        assert len(docs) == 5

        # Verify automated notifications created
        cursor.execute("SELECT * FROM notifications WHERE client_id = ?", (client_id,))
        notifs = cursor.fetchall()
        assert len(notifs) >= 2  # Client email + Admin alert

def test_03_client_two_submission_isolated_independently():
    """
    Test submission for Client 2 (Priya Sharma):
    - Should receive subsequent Client ID (e.g. VISA-2026-0002)
    - Must have distinct isolated folder and files that NEVER mix with Client 1
    """
    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy passport 2")
    dummy_aadhaar = io.BytesIO(b"%PDF-1.4 dummy aadhaar 2")
    dummy_bank = io.BytesIO(b"%PDF-1.4 dummy bank statement 2")

    files = [
        ("passport", ("Priya_Passport.pdf", dummy_pdf, "application/pdf")),
        ("aadhaar", ("Priya_Aadhaar.pdf", dummy_aadhaar, "application/pdf")),
        ("bank_docs", ("Priya_BankStatement.pdf", dummy_bank, "application/pdf")),
    ]

    data = {
        "full_name": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "mobile": "+91 9123456780",
        "dob": "1995-11-20",
        "address": "45 Park Avenue, Bangalore 560001",
        "service": "Passport Renewal",
        "country": "United Kingdom",
        "reference_no": "UK-REN-009",
        "consent_given": "true"
    }

    response = client.post("/api/submit-documents", data=data, files=files)
    assert response.status_code == 201
    res_data = response.json()
    client_id_2 = res_data["client_id"]
    assert client_id_2.startswith("VISA-2026-")

    # Check that Client 2 has their own folder
    client2_dir = STORAGE_DIR / client_id_2
    assert client2_dir.exists()
    assert len(list(client2_dir.glob("*"))) == 3

    # Critical Isolation Check: Check that Client 1's folder is unaffected
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM clients ORDER BY id ASC")
        rows = cursor.fetchall()
        client_id_1 = rows[0]["client_id"]
        assert client_id_1 != client_id_2

    client1_dir = STORAGE_DIR / client_id_1
    assert len(list(client1_dir.glob("*"))) == 5

def test_04_client_self_service_tracking():
    """Verify that clients can track status with Client ID and matching contact info."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id, email, mobile FROM clients WHERE full_name = 'John Doe'")
        c1 = cursor.fetchone()

    # Successful tracking
    res = client.post("/api/track-status", json={
        "client_id": c1["client_id"],
        "contact_identifier": c1["email"]
    })
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["client_id"] == c1["client_id"]
    assert res_json["status"] == "New"
    assert res_json["documents_count"] == 5

    # Tracking with mismatched identifier should be rejected
    bad_res = client.post("/api/track-status", json={
        "client_id": c1["client_id"],
        "contact_identifier": "wrong@email.com"
    })
    assert bad_res.status_code == 403

def test_05_admin_unauthorized_access_blocked():
    """Verify that sensitive documents cannot be accessed without authentication."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, client_id FROM documents LIMIT 1")
        doc = cursor.fetchone()

    # Unauthenticated attempt to view document
    res_view = client.get(f"/api/admin/clients/{doc['client_id']}/documents/{doc['id']}/view")
    assert res_view.status_code == 401

    # Unauthenticated attempt to fetch client list
    res_list = client.get("/api/admin/clients")
    assert res_list.status_code == 401

def test_06_admin_login_and_table_queries():
    """Test admin authentication, search, filtering, and metrics."""
    # Invalid password
    bad_login = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # Valid admin login
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch all clients
    res_clients = client.get("/api/admin/clients", headers=headers)
    assert res_clients.status_code == 200
    body = res_clients.json()
    assert body["total"] >= 2
    assert body["metrics"]["total_clients"] >= 2

    # Filter by service 'Passport Renewal'
    res_service = client.get("/api/admin/clients?service=Passport+Renewal", headers=headers)
    assert res_service.status_code == 200
    assert all(c["service"] == "Passport Renewal" for c in res_service.json()["clients"])

    # Search for 'Priya'
    res_search = client.get("/api/admin/clients?search=Priya", headers=headers)
    assert res_search.status_code == 200
    assert any("Priya" in c["full_name"] for c in res_search.json()["clients"])

def test_07_admin_document_view_and_download():
    """Test authorized viewing and downloading of documents."""
    # Login
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, client_id, original_filename FROM documents WHERE client_id LIKE 'VISA-%' LIMIT 1")
        doc = cursor.fetchone()

    # View document inline
    view_res = client.get(f"/api/admin/clients/{doc['client_id']}/documents/{doc['id']}/view", headers=headers)
    assert view_res.status_code == 200
    assert "inline" in view_res.headers.get("content-disposition", "")
    assert view_res.headers.get("x-content-type-options") == "nosniff"

    # Download document as attachment
    dl_res = client.get(f"/api/admin/clients/{doc['client_id']}/documents/{doc['id']}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "attachment" in dl_res.headers.get("content-disposition", "")

def test_08_admin_download_all_zip():
    """Test packaging all client documents into a ZIP archive."""
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM clients WHERE full_name = 'John Doe'")
        c1 = cursor.fetchone()

    zip_res = client.get(f"/api/admin/clients/{c1['client_id']}/download-all-zip", headers=headers)
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Read zip bytes and check count
    zip_bytes = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 5

def test_09_admin_status_update_and_notes():
    """Test updating application status and adding internal staff notes."""
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM clients WHERE full_name = 'John Doe'")
        c1 = cursor.fetchone()

    # Update status to 'Under Review'
    patch_res = client.patch(
        f"/api/admin/clients/{c1['client_id']}/status",
        headers=headers,
        json={"status": "Under Review", "custom_note": "Aadhaar verified. Reviewing photo dimensions."}
    )
    assert patch_res.status_code == 200

    # Add internal note
    note_res = client.post(
        f"/api/admin/clients/{c1['client_id']}/notes",
        headers=headers,
        json={"note_text": "Spoke to applicant regarding embassy appointment schedule."}
    )
    assert note_res.status_code == 200

    # Verify status changed and note recorded
    detail_res = client.get(f"/api/admin/clients/{c1['client_id']}", headers=headers)
    detail_data = detail_res.json()["client"]
    assert detail_data["status"] == "Under Review"
    assert len(detail_data["notes"]) >= 2
    assert any("Spoke to applicant" in n["note_text"] for n in detail_data["notes"])

def test_10_csv_export():
    """Test exporting all client records as CSV."""
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_res = client.get("/api/admin/export-csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    content = csv_res.text
    assert "Client ID,Full Name,Email,Mobile" in content
    assert "John Doe" in content
    assert "Priya Sharma" in content

def test_11_client_record_deletion_and_storage_wipe():
    """Test permanent deletion of client record and file purging."""
    login_res = client.post("/api/admin/login", json={
        "email": "admin@visaflow.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT client_id FROM clients WHERE full_name = 'Priya Sharma'")
        c2 = cursor.fetchone()

    client2_id = c2["client_id"]
    client2_dir = STORAGE_DIR / client2_id
    assert client2_dir.exists()

    # Delete client
    del_res = client.delete(f"/api/admin/clients/{client2_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify folder deleted from disk
    assert not client2_dir.exists()

    # Verify database record deleted
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client2_id,))
        assert cursor.fetchone() is None
        cursor.execute("SELECT * FROM documents WHERE client_id = ?", (client2_id,))
        assert len(cursor.fetchall()) == 0

    print("\n[SUCCESS] All 11 end-to-end integration tests completed and verified successfully!")
