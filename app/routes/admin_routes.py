import csv
import io
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from app.config import (
    BASE_DIR,
    SERVICES,
    STATUSES,
    DOCUMENT_CATEGORIES,
    SESSION_COOKIE_NAME,
    SESSION_DURATION_HOURS
)
from app.database import get_db
from app.security import (
    verify_password,
    generate_session_token,
    get_current_admin
)
from app.services.client_service import ClientService
from app.services.storage import SecureStorageService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.models import (
    AdminLoginRequest,
    ClientStatusUpdateRequest,
    InternalNoteCreateRequest,
    ContactClientRequest
)

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# ==================== ADMIN AUTHENTICATION ====================

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login screen."""
    # Check if already logged in
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        from app.security import verify_session_token
        if verify_session_token(token):
            return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
            
    return templates.TemplateResponse(request=request, name="admin_login.html", context={})

@router.post("/api/admin/login")
async def admin_login_api(payload: AdminLoginRequest, response: Response):
    """Authenticates admin user and sets secure HTTP-only session cookie."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE email = ?", (payload.email.strip().lower(),))
        user = cursor.fetchone()
        
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = generate_session_token(user["id"], user["email"], user["role"])
    
    # Set cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=False # set to True in strict HTTPS production
    )

    AuditService.log(
        action="LOGIN_SUCCESS",
        actor_type="ADMIN",
        actor_identifier=user["email"],
        details="Staff member logged into admin portal."
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        },
        "redirect_url": "/admin/dashboard"
    }

@router.post("/api/admin/logout")
async def admin_logout_api(response: Response, current_admin: dict = Depends(get_current_admin)):
    """Logs out admin user and clears session cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    AuditService.log(
        action="LOGOUT",
        actor_type="ADMIN",
        actor_identifier=current_admin["email"],
        details="Staff logged out."
    )
    return {"success": True, "message": "Logged out successfully."}


# ==================== ADMIN DASHBOARD PAGES ====================

@router.get("/admin", response_class=RedirectResponse)
async def admin_redirect():
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Protected Staff Admin Dashboard."""
    # Check session cookie directly for template rendering
    token = request.cookies.get(SESSION_COOKIE_NAME)
    from app.security import verify_session_token
    admin_data = verify_session_token(token)
    if not admin_data:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    metrics = ClientService.get_dashboard_metrics()
    notifications = NotificationService.get_admin_notifications(unread_only=True, limit=10)

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "admin": admin_data,
            "metrics": metrics,
            "services": SERVICES,
            "statuses": STATUSES,
            "unread_notifications": notifications
        }
    )


# ==================== CLIENT MANAGEMENT APIS ====================

@router.get("/api/admin/clients")
async def get_clients_api(
    search: Optional[str] = None,
    service: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 25,
    current_admin: dict = Depends(get_current_admin)
):
    """Fetch paginated, filtered, searchable client table data."""
    result = ClientService.list_clients(
        search=search,
        service=service,
        status_filter=status,
        page=page,
        limit=limit
    )
    metrics = ClientService.get_dashboard_metrics()
    return {
        "success": True,
        **result,
        "metrics": metrics
    }

@router.get("/api/admin/clients/{client_id}")
async def get_client_detail_api(
    client_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Fetch full client profile with documents, internal notes, notifications, and audit log."""
    client = ClientService.get_client_full_details(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    return {"success": True, "client": client}

@router.patch("/api/admin/clients/{client_id}/status")
async def update_client_status_api(
    client_id: str,
    payload: ClientStatusUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Updates client application status and records internal notes and notifications."""
    if payload.status not in STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status '{payload.status}'.")

    success = ClientService.update_status(
        client_id=client_id,
        new_status=payload.status,
        admin_email=current_admin["email"],
        custom_note=payload.custom_note,
        notify_client=payload.notify_client
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client record not found.")

    return {"success": True, "message": f"Status updated to '{payload.status}' successfully."}

@router.post("/api/admin/clients/{client_id}/notes")
async def add_internal_note_api(
    client_id: str,
    payload: InternalNoteCreateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Adds staff internal note to client record."""
    client = ClientService.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    ClientService.add_internal_note(
        client_id=client_id,
        author_name=current_admin["email"],
        note_text=payload.note_text
    )

    return {"success": True, "message": "Internal note added."}

@router.delete("/api/admin/clients/{client_id}")
async def delete_client_api(
    client_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Permanently deletes client record and wipes all private files from disk."""
    success = ClientService.delete_client(client_id, admin_email=current_admin["email"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    return {"success": True, "message": f"Client record {client_id} and all files deleted permanently."}


# ==================== SECURE DOCUMENT RETRIEVAL ====================

@router.get("/api/admin/clients/{client_id}/documents/{doc_id}/view")
async def view_document_api(
    client_id: str,
    doc_id: int,
    request: Request,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Secure inline document preview stream for staff.
    Protected from direct/public URL access.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ? AND client_id = ?", (doc_id, client_id))
        doc = cursor.fetchone()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    file_path = SecureStorageService.get_document_file_path(client_id, doc["stored_filename"])

    AuditService.log(
        action="DOCUMENT_VIEW",
        actor_type="ADMIN",
        actor_identifier=current_admin["email"],
        client_id=client_id,
        details=f"Viewed document: {doc['category_label']} ({doc['original_filename']})"
    )

    # Return inline preview with security headers
    return FileResponse(
        path=file_path,
        media_type=doc["mime_type"],
        filename=doc["original_filename"],
        content_disposition_type="inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache, no-store, must-revalidate"
        }
    )

@router.get("/api/admin/clients/{client_id}/documents/{doc_id}/download")
async def download_document_api(
    client_id: str,
    doc_id: int,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Secure attachment download stream for staff with original filename.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ? AND client_id = ?", (doc_id, client_id))
        doc = cursor.fetchone()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    file_path = SecureStorageService.get_document_file_path(client_id, doc["stored_filename"])

    AuditService.log(
        action="DOCUMENT_DOWNLOAD",
        actor_type="ADMIN",
        actor_identifier=current_admin["email"],
        client_id=client_id,
        details=f"Downloaded document: {doc['category_label']} ({doc['original_filename']})"
    )

    return FileResponse(
        path=file_path,
        media_type=doc["mime_type"],
        filename=doc["original_filename"],
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache, no-store, must-revalidate"
        }
    )

@router.get("/api/admin/clients/{client_id}/download-all-zip")
async def download_all_documents_zip_api(
    client_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Packages all client documents into a single organized ZIP archive
    for embassy filing or offline review.
    """
    client = ClientService.get_client_full_details(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    if not client.get("documents"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents available to bundle.")

    zip_stream = SecureStorageService.create_client_zip(
        client_id=client_id,
        client_name=client["full_name"],
        documents=client["documents"]
    )

    AuditService.log(
        action="BATCH_DOWNLOAD",
        actor_type="ADMIN",
        actor_identifier=current_admin["email"],
        client_id=client_id,
        details=f"Bundled and downloaded all {len(client['documents'])} documents as ZIP."
    )

    zip_filename = f"{client_id}_{client['full_name'].replace(' ', '_')}_Documents.zip"

    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{zip_filename}\"",
            "Cache-Control": "no-cache"
        }
    )


# ==================== NOTIFICATIONS & AUDIT ====================

@router.get("/api/admin/notifications")
async def get_admin_notifications_api(
    unread_only: bool = False,
    current_admin: dict = Depends(get_current_admin)
):
    """Fetch notifications for the admin panel bell drawer."""
    notifs = NotificationService.get_admin_notifications(unread_only=unread_only)
    return {"success": True, "notifications": notifs}

@router.post("/api/admin/notifications/mark-read")
async def mark_notifications_read_api(
    current_admin: dict = Depends(get_current_admin)
):
    """Mark all admin notifications as read."""
    NotificationService.mark_all_admin_read()
    return {"success": True, "message": "All notifications marked as read."}

@router.post("/api/admin/contact-client/{client_id}")
async def contact_client_api(
    client_id: str,
    payload: ContactClientRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Dispatches a direct email communication or log entry to the client."""
    client = ClientService.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    NotificationService.send_status_update_notification(
        client=client,
        new_status=client["status"],
        custom_message=payload.message
    )

    ClientService.add_internal_note(
        client_id=client_id,
        author_name=current_admin["email"],
        note_text=f"Direct message sent to client: \"{payload.subject}\" - {payload.message[:100]}..."
    )

    return {"success": True, "message": f"Message sent to {client['email']}."}

@router.get("/api/admin/audit-logs")
async def get_audit_logs_api(
    limit: int = 100,
    current_admin: dict = Depends(get_current_admin)
):
    """Fetch compliance and security audit logs."""
    logs = AuditService.get_all_logs(limit=limit)
    return {"success": True, "audit_logs": logs}

@router.get("/api/admin/export-csv")
async def export_clients_csv(
    current_admin: dict = Depends(get_current_admin)
):
    """Export all client records as CSV for reporting and compliance."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.client_id, c.full_name, c.email, c.mobile, c.dob,
                   c.address, c.service, c.country, c.reference_no, c.status,
                   c.created_at, c.updated_at,
                   (SELECT COUNT(*) FROM documents d WHERE d.client_id = c.client_id) as doc_count
            FROM clients c
            ORDER BY c.id DESC
        """)
        rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Client ID", "Full Name", "Email", "Mobile", "DOB",
        "Address", "Service", "Country", "Reference No", "Status",
        "Submitted At", "Last Updated", "Documents Count"
    ])

    for row in rows:
        writer.writerow([
            row["client_id"], row["full_name"], row["email"], row["mobile"], row["dob"],
            row["address"], row["service"], row["country"], row["reference_no"] or "", row["status"],
            row["created_at"], row["updated_at"], row["doc_count"]
        ])

    output.seek(0)

    AuditService.log(
        action="EXPORT_CSV",
        actor_type="ADMIN",
        actor_identifier=current_admin["email"],
        details="Admin exported full client records CSV."
    )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=\"Visa_Clients_Export.csv\"",
            "Cache-Control": "no-cache"
        }
    )
