from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class ClientStatusUpdateRequest(BaseModel):
    status: str
    custom_note: Optional[str] = None
    notify_client: bool = True

class InternalNoteCreateRequest(BaseModel):
    note_text: str = Field(..., min_length=1, max_length=2000)

class ContactClientRequest(BaseModel):
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=5, max_length=4000)
    channel: str = Field(default="EMAIL")

class TrackStatusRequest(BaseModel):
    client_id: str
    contact_identifier: str  # Email or Mobile
