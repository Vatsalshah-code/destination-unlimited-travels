from typing import List, Optional
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.config import (
    SERVICES,
    DOCUMENT_CATEGORIES,
    BASE_DIR
)
from app.services.client_service import ClientService
from app.services.storage import SecureStorageService
from app.models import TrackStatusRequest

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

@router.get("/", response_class=RedirectResponse)
async def root_redirect():
    return RedirectResponse(url="/upload-documents", status_code=status.HTTP_302_FOUND)

@router.get("/upload-documents", response_class=HTMLResponse)
async def show_client_form(request: Request, ref: Optional[str] = None):
    """Public client-facing document upload page."""
    return templates.TemplateResponse(
        request=request,
        name="client_form.html",
        context={
            "services": SERVICES,
            "document_categories": DOCUMENT_CATEGORIES,
            "ref_param": ref or ""
        }
    )

@router.post("/api/submit-documents")
async def submit_documents(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    dob: str = Form(...),
    address: str = Form(...),
    service: str = Form(...),
    country: str = Form(...),
    reference_no: Optional[str] = Form(None),
    consent_given: bool = Form(...),
    # Document upload files
    passport: Optional[UploadFile] = File(None),
    aadhaar: Optional[UploadFile] = File(None),
    pan: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None),
    bank_docs: Optional[UploadFile] = File(None),
    previous_visa: Optional[UploadFile] = File(None),
    supporting_docs: List[UploadFile] = File(default=[])
):
    """
    Processes the public submission:
    - Validates consent and mandatory personal fields
    - Generates client-isolated storage
    - Saves and validates each uploaded document
    - Generates unique Client ID (e.g. VISA-2026-0001)
    - Triggers automated notifications
    """
    if not consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Privacy consent is mandatory to process identity and visa documents."
        )

    # Basic validations
    if not full_name.strip() or not email.strip() or not mobile.strip() or not country.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please fill in all required personal and service fields."
        )

    # Temporary client ID placeholder for storage initialization
    temp_client_id = ClientService.generate_next_client_id()
    
    # Process files
    uploaded_files_data = []

    # Map single file inputs
    single_uploads = [
        ("passport", passport),
        ("aadhaar", aadhaar),
        ("pan", pan),
        ("photo", photo),
        ("bank_docs", bank_docs),
        ("previous_visa", previous_visa)
    ]

    try:
        for cat_key, file_obj in single_uploads:
            if file_obj and file_obj.filename and file_obj.size and file_obj.size > 0:
                saved_doc = await SecureStorageService.validate_and_save_file(
                    client_id=temp_client_id,
                    category=cat_key,
                    upload_file=file_obj,
                    index=1
                )
                uploaded_files_data.append(saved_doc)

        # Supporting documents (multiple allowed)
        if supporting_docs:
            for idx, sup_file in enumerate(supporting_docs, start=1):
                if sup_file and sup_file.filename and sup_file.size and sup_file.size > 0:
                    saved_doc = await SecureStorageService.validate_and_save_file(
                        client_id=temp_client_id,
                        category="supporting_docs",
                        upload_file=sup_file,
                        index=idx
                    )
                    uploaded_files_data.append(saved_doc)

        # At least one document should be provided
        if not uploaded_files_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload at least one document (e.g. Passport, Aadhaar, Photo, or Supporting Document)."
            )

        client_ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "")

        form_dict = {
            "full_name": full_name,
            "email": email,
            "mobile": mobile,
            "dob": dob,
            "address": address,
            "service": service,
            "country": country,
            "reference_no": reference_no or "",
            "consent_given": consent_given
        }

        # Atomically save record
        client_record = await ClientService.create_client_submission(
            form_data=form_dict,
            uploaded_files_data=uploaded_files_data,
            ip_address=client_ip,
            user_agent=user_agent
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "client_id": client_record["client_id"],
                "message": "Your documents have been submitted successfully.",
                "redirect_url": f"/submission-success/{client_record['client_id']}",
                "uploaded_documents_count": len(uploaded_files_data)
            }
        )

    except HTTPException:
        # Clean up files if error occurred during process
        SecureStorageService.delete_client_files(temp_client_id)
        raise
    except Exception as e:
        SecureStorageService.delete_client_files(temp_client_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while saving your application: {str(e)}"
        )

@router.get("/submission-success/{client_id}", response_class=HTMLResponse)
async def show_submission_success(request: Request, client_id: str):
    """Success page showing unique Client ID and submission summary."""
    client = ClientService.get_client_full_details(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client record not found.")

    return templates.TemplateResponse(
        request=request,
        name="submission_success.html",
        context={"client": client}
    )

@router.get("/track", response_class=HTMLResponse)
async def show_track_page(request: Request):
    """Client self-service tracking page."""
    return templates.TemplateResponse(
        request=request,
        name="tracking.html",
        context={}
    )

@router.post("/api/track-status")
async def track_status_api(payload: TrackStatusRequest):
    """Allows clients to verify status with Client ID and Email/Mobile."""
    client = ClientService.get_client_full_details(payload.client_id.strip())
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found. Please verify your Client ID.")

    ident = payload.contact_identifier.strip().lower()
    if client["email"].lower() != ident and client["mobile"].replace(" ", "").replace("-", "") != ident.replace(" ", "").replace("-", ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contact details do not match the application record. Please provide registered email or mobile."
        )

    return {
        "success": True,
        "client_id": client["client_id"],
        "full_name": client["full_name"],
        "service": client["service"],
        "country": client["country"],
        "status": client["status"],
        "submitted_at": client["created_at"],
        "updated_at": client["updated_at"],
        "documents_count": len(client.get("documents", [])),
        "documents_summary": [
            {
                "category_label": d["category_label"],
                "original_filename": d["original_filename"],
                "upload_status": d["upload_status"],
                "file_size": d["file_size"],
                "uploaded_at": d["uploaded_at"]
            }
            for d in client.get("documents", [])
        ]
    }
