"""
Supabase Storage service for managing file uploads and downloads.
Handles PDFs, logos, attachments and other file types.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urlparse

from supabase import Client
from app.config import settings
from app.domain.models.base import ValidationError


class StorageService:
    """Service for managing file storage using Supabase Storage."""
    
    def __init__(self, supabase_client: Client):
        """Initialize storage service with Supabase client."""
        self.client = supabase_client
        self.default_bucket = "documents"  # Default bucket for general files
        
        # Bucket configuration
        self.buckets = {
            "documents": "General documents (PDFs, reports)",
            "logos": "Company and client logos",
            "attachments": "Task and project attachments",
            "temp": "Temporary files with auto-cleanup"
        }
        
        # File type configurations
        self.max_file_sizes = {
            "image": 5 * 1024 * 1024,  # 5MB for images
            "document": 10 * 1024 * 1024,  # 10MB for documents
            "pdf": 20 * 1024 * 1024,  # 20MB for PDFs
        }
        
        self.allowed_types = {
            "image": ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"],
            "document": ["application/pdf", "text/plain", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            "pdf": ["application/pdf"]
        }
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        bucket: str = None,
        folder: str = None,
        user_id: str = None,
        content_type: str = None,
        make_public: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a file to Supabase Storage.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            bucket: Storage bucket name
            folder: Optional folder within bucket
            user_id: User ID for organizing files
            content_type: MIME type of the file
            make_public: Whether to make file publicly accessible
            
        Returns:
            Dict with upload result including file_path and public_url
        """
        bucket = bucket or self.default_bucket
        
        # Validate file
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
        
        self._validate_file(file_content, filename, content_type)
        
        # Generate unique file path
        file_path = self._generate_file_path(filename, folder, user_id)
        
        try:
            # Upload file to Supabase Storage
            response = self.client.storage.from_(bucket).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "cache-control": "public, max-age=3600",
                    "upsert": True  # Overwrite if exists
                }
            )
            
            if response.status_code not in [200, 201]:
                raise ValidationError(f"Upload failed: {response.json()}")
            
            # Get public URL if requested
            public_url = None
            if make_public:
                public_url = self.client.storage.from_(bucket).get_public_url(file_path)
            
            # Generate signed URL for private access (24 hours)
            signed_url = self.client.storage.from_(bucket).create_signed_url(
                path=file_path,
                expires_in=86400  # 24 hours
            )
            
            return {
                "success": True,
                "file_path": file_path,
                "bucket": bucket,
                "public_url": public_url,
                "signed_url": signed_url,
                "content_type": content_type,
                "file_size": len(file_content),
                "uploaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to upload file: {str(e)}")
    
    async def upload_pdf(
        self,
        pdf_path: str,
        filename: str = None,
        user_id: str = None,
        folder: str = "invoices"
    ) -> Dict[str, Any]:
        """
        Upload a PDF file from local path.
        
        Args:
            pdf_path: Local path to PDF file
            filename: Optional custom filename
            user_id: User ID for organization
            folder: Folder within documents bucket
            
        Returns:
            Upload result with URLs
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise ValidationError(f"PDF file not found: {pdf_path}")
        
        filename = filename or pdf_file.name
        
        # Read file content
        with open(pdf_file, 'rb') as f:
            content = f.read()
        
        return await self.upload_file(
            file_content=content,
            filename=filename,
            bucket="documents",
            folder=folder,
            user_id=user_id,
            content_type="application/pdf",
            make_public=False
        )
    
    async def upload_company_logo(
        self,
        image_content: bytes,
        filename: str,
        user_id: str,
        content_type: str = None
    ) -> Dict[str, Any]:
        """
        Upload a company logo image.
        
        Args:
            image_content: Image file content
            filename: Original filename
            user_id: User/company ID
            content_type: MIME type of the image
            
        Returns:
            Upload result with public URL
        """
        return await self.upload_file(
            file_content=image_content,
            filename=filename,
            bucket="logos",
            folder="companies",
            user_id=user_id,
            content_type=content_type,
            make_public=True
        )
    
    async def download_file(
        self,
        file_path: str,
        bucket: str = None
    ) -> bytes:
        """
        Download a file from storage.
        
        Args:
            file_path: Path to file in storage
            bucket: Storage bucket name
            
        Returns:
            File content as bytes
        """
        bucket = bucket or self.default_bucket
        
        try:
            response = self.client.storage.from_(bucket).download(file_path)
            return response
        except Exception as e:
            raise ValidationError(f"Failed to download file: {str(e)}")
    
    async def delete_file(
        self,
        file_path: str,
        bucket: str = None
    ) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to file in storage
            bucket: Storage bucket name
            
        Returns:
            True if successful
        """
        bucket = bucket or self.default_bucket
        
        try:
            response = self.client.storage.from_(bucket).remove([file_path])
            return response.status_code == 200
        except Exception as e:
            raise ValidationError(f"Failed to delete file: {str(e)}")
    
    async def list_files(
        self,
        folder: str = "",
        bucket: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in a folder.
        
        Args:
            folder: Folder path to list
            bucket: Storage bucket name
            limit: Maximum number of files to return
            
        Returns:
            List of file metadata
        """
        bucket = bucket or self.default_bucket
        
        try:
            response = self.client.storage.from_(bucket).list(
                path=folder,
                limit=limit,
                sort_by={"column": "created_at", "order": "desc"}
            )
            return response
        except Exception as e:
            raise ValidationError(f"Failed to list files: {str(e)}")
    
    async def get_file_info(
        self,
        file_path: str,
        bucket: str = None
    ) -> Dict[str, Any]:
        """
        Get file metadata.
        
        Args:
            file_path: Path to file in storage
            bucket: Storage bucket name
            
        Returns:
            File metadata
        """
        bucket = bucket or self.default_bucket
        
        try:
            # Get file info from list (Supabase doesn't have direct file info endpoint)
            folder = str(Path(file_path).parent)
            files = await self.list_files(folder, bucket)
            
            for file_info in files:
                if file_info.get("name") == Path(file_path).name:
                    return file_info
            
            raise ValidationError("File not found")
        except Exception as e:
            raise ValidationError(f"Failed to get file info: {str(e)}")
    
    async def create_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        bucket: str = None
    ) -> str:
        """
        Create a signed URL for private file access.
        
        Args:
            file_path: Path to file in storage
            expires_in: URL expiration time in seconds
            bucket: Storage bucket name
            
        Returns:
            Signed URL
        """
        bucket = bucket or self.default_bucket
        
        try:
            response = self.client.storage.from_(bucket).create_signed_url(
                path=file_path,
                expires_in=expires_in
            )
            return response["signedURL"]
        except Exception as e:
            raise ValidationError(f"Failed to create signed URL: {str(e)}")
    
    async def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified hours.
        
        Args:
            older_than_hours: Delete files older than this many hours
            
        Returns:
            Number of files deleted
        """
        try:
            files = await self.list_files("", "temp")
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            deleted_count = 0
            for file_info in files:
                file_time = datetime.fromisoformat(file_info["created_at"].replace("Z", "+00:00"))
                if file_time < cutoff_time:
                    await self.delete_file(file_info["name"], "temp")
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            print(f"Failed to cleanup temp files: {str(e)}")
            return 0
    
    def _validate_file(self, content: bytes, filename: str, content_type: str) -> None:
        """Validate file before upload."""
        if not content:
            raise ValidationError("File content is empty")
        
        # Check file size
        file_size = len(content)
        category = self._get_file_category(content_type)
        max_size = self.max_file_sizes.get(category, 5 * 1024 * 1024)
        
        if file_size > max_size:
            raise ValidationError(f"File too large. Maximum size: {max_size / 1024 / 1024:.1f}MB")
        
        # Check content type
        allowed_types = self.allowed_types.get(category, [])
        if content_type not in allowed_types:
            raise ValidationError(f"File type not allowed: {content_type}")
    
    def _get_file_category(self, content_type: str) -> str:
        """Get file category from content type."""
        if content_type.startswith("image/"):
            return "image"
        elif content_type == "application/pdf":
            return "pdf"
        else:
            return "document"
    
    def _generate_file_path(self, filename: str, folder: str = None, user_id: str = None) -> str:
        """Generate unique file path for storage."""
        # Clean filename
        safe_filename = self._sanitize_filename(filename)
        
        # Generate hash for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(f"{safe_filename}{timestamp}".encode()).hexdigest()[:8]
        
        # Construct path
        path_parts = []
        
        if folder:
            path_parts.append(folder)
        
        if user_id:
            path_parts.append(user_id)
        
        # Add date-based folder
        path_parts.append(datetime.now().strftime("%Y/%m"))
        
        # Add filename with hash
        name_without_ext = Path(safe_filename).stem
        extension = Path(safe_filename).suffix
        unique_filename = f"{name_without_ext}_{hash_part}{extension}"
        path_parts.append(unique_filename)
        
        return "/".join(path_parts)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove or replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        
        # Keep only safe characters
        safe_name = "".join(c if c in safe_chars else "_" for c in filename)
        
        # Ensure reasonable length
        if len(safe_name) > 200:
            name_part = Path(safe_name).stem[:180]
            ext_part = Path(safe_name).suffix
            safe_name = f"{name_part}{ext_part}"
        
        return safe_name


# Create singleton instance with lazy initialization
_storage_service = None

def get_storage_service() -> StorageService:
    """Get singleton storage service instance."""
    global _storage_service
    if _storage_service is None:
        from app.infrastructure.auth.supabase_client import get_supabase_client
        _storage_service = StorageService(get_supabase_client())
    return _storage_service