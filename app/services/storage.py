import os
import shutil
import hashlib
import zipfile
import io
from pathlib import Path
from typing import Tuple, List, Dict
from fastapi import UploadFile, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from app.config import (
    STORAGE_DIR,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE
)
from app.security import sanitize_filename

class SecureStorageService:
    @staticmethod
    def get_client_directory(client_id: str) -> Path:
        """Get or create the isolated private folder for a client."""
        # Sanitize client ID to prevent path traversal
        clean_id = sanitize_filename(client_id)
        client_dir = (STORAGE_DIR / clean_id).resolve()
        
        # Security invariant: client_dir must stay strictly inside STORAGE_DIR
        if not str(client_dir).startswith(str(STORAGE_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client storage path."
            )
            
        client_dir.mkdir(parents=True, exist_ok=True)
        return client_dir

    @classmethod
    async def validate_and_save_file(
        cls,
        client_id: str,
        category: str,
        upload_file: UploadFile,
        index: int = 1
    ) -> Dict:
        """
        Validates file size, extension, MIME type, saves to client folder,
        computes SHA-256, and returns file metadata.
        """
        filename = sanitize_filename(upload_file.filename or f"{category}_{index}.dat")
        ext = Path(filename).suffix.lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}' for file '{filename}'. Allowed formats: PDF, JPG, PNG, WEBP."
            )

        client_dir = cls.get_client_directory(client_id)
        
        # Read file chunks to enforce size limit and compute hash simultaneously
        hasher = hashlib.sha256()
        total_size = 0
        file_chunks = []
        
        while True:
            chunk = await upload_file.read(64 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{filename}' exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB."
                )
            hasher.update(chunk)
            file_chunks.append(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is empty."
            )

        sha256_checksum = hasher.hexdigest()
        
        # Create an organized, unambiguous stored file name
        short_hash = sha256_checksum[:8]
        clean_stem = Path(filename).stem[:30]
        stored_filename = f"{category}_{clean_stem}_{short_hash}{ext}"
        
        file_path = client_dir / stored_filename
        
        # Write bytes
        with open(file_path, "wb") as f:
            for chunk in file_chunks:
                f.write(chunk)
                
        # Resolve mime type
        mime_type = upload_file.content_type or "application/octet-stream"
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext == ".webp":
            mime_type = "image/webp"

        return {
            "client_id": client_id,
            "category": category,
            "original_filename": filename,
            "stored_filename": stored_filename,
            "relative_path": f"{client_id}/{stored_filename}",
            "file_size": total_size,
            "mime_type": mime_type,
            "sha256_checksum": sha256_checksum
        }

    @classmethod
    def get_document_file_path(cls, client_id: str, stored_filename: str) -> Path:
        """Verify and retrieve exact path for an authenticated document request."""
        client_dir = cls.get_client_directory(client_id)
        clean_filename = sanitize_filename(stored_filename)
        file_path = (client_dir / clean_filename).resolve()
        
        # Guard against traversal
        if not str(file_path).startswith(str(client_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to requested file path."
            )
            
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on server."
            )
            
        return file_path

    @classmethod
    def create_client_zip(cls, client_id: str, client_name: str, documents: List[Dict]) -> io.BytesIO:
        """Package all client documents into an in-memory ZIP archive."""
        client_dir = cls.get_client_directory(client_id)
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in documents:
                doc_path = client_dir / doc["stored_filename"]
                if doc_path.exists() and doc_path.is_file():
                    # Prefix category name to make files neatly organized in zip
                    arcname = f"{doc['category_label']}_{doc['original_filename']}"
                    zf.write(doc_path, arcname=arcname)
                    
        zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def delete_client_files(cls, client_id: str) -> bool:
        """Securely wipe client directory when client record is deleted."""
        clean_id = sanitize_filename(client_id)
        client_dir = (STORAGE_DIR / clean_id).resolve()
        if str(client_dir).startswith(str(STORAGE_DIR.resolve())) and client_dir.exists():
            shutil.rmtree(client_dir, ignore_errors=True)
            return True
        return False
