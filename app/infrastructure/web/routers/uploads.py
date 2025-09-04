"""
File upload router.
Handles file uploads for logos, avatars, attachments, and other assets.
"""

from typing import Annotated, List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, JSONResponse

from app.infrastructure.auth import get_current_user_id
from app.infrastructure.storage.storage_service import get_storage_service
from app.infrastructure.storage.bucket_manager import get_bucket_manager
from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
from app.infrastructure.repositories.task_repository import SQLAlchemyTaskRepository
from app.infrastructure.db.database import get_db_session
from app.domain.models.base import EntityNotFoundError, ValidationError
from pydantic import BaseModel


router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool
    file_path: str
    public_url: Optional[str] = None
    signed_url: Optional[str] = None
    file_size: int
    content_type: str
    uploaded_at: str
    message: str


@router.post("/client-logo/{client_id}")
async def upload_client_logo(
    client_id: int,
    file: UploadFile = File(...),
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Upload logo for a client.
    
    - **client_id**: Client ID to upload logo for
    - **file**: Logo image file (JPEG, PNG, GIF, WebP, SVG)
    """
    try:
        # Get client repository
        session = next(get_db_session())
        client_repo = SQLAlchemyClientRepository(session)
        
        # Verify client exists and user has access
        client = await client_repo.find_by_id(client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with id {client_id} not found"
            )
        
        if client.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this client"
            )
        
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file for logos bucket
        bucket_manager = get_bucket_manager()
        validation = bucket_manager.validate_file_for_bucket("logos", len(content), file.content_type)
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation["error"]
            )
        
        # Upload file
        storage_service = get_storage_service()
        result = await storage_service.upload_file(
            file_content=content,
            filename=f"client_{client_id}_{file.filename}",
            bucket="logos",
            folder="clients",
            user_id=user_id,
            content_type=file.content_type,
            make_public=True
        )
        
        # Update client with logo URL
        client.logo_url = result["public_url"]
        await client_repo.save(client)
        
        return UploadResponse(
            success=True,
            file_path=result["file_path"],
            public_url=result["public_url"],
            signed_url=result["signed_url"],
            file_size=result["file_size"],
            content_type=result["content_type"],
            uploaded_at=result["uploaded_at"],
            message=f"Logo uploaded successfully for client {client.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload logo: {str(e)}"
        )


@router.post("/user-avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Upload avatar for current user.
    
    - **file**: Avatar image file (JPEG, PNG, GIF, WebP)
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size (max 2MB for avatars)
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar file too large. Maximum size: 2MB"
            )
        
        # Upload file
        storage_service = get_storage_service()
        result = await storage_service.upload_file(
            file_content=content,
            filename=f"avatar_{file.filename}",
            bucket="avatars",
            folder="users",
            user_id=user_id,
            content_type=file.content_type,
            make_public=True
        )
        
        # TODO: Update user profile with avatar URL
        # This would require a user profile repository
        
        return UploadResponse(
            success=True,
            file_path=result["file_path"],
            public_url=result["public_url"],
            signed_url=result["signed_url"],
            file_size=result["file_size"],
            content_type=result["content_type"],
            uploaded_at=result["uploaded_at"],
            message="Avatar uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )


@router.post("/task-attachment/{task_id}")
async def upload_task_attachment(
    task_id: int,
    file: UploadFile = File(...),
    description: str = Form(None),
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Upload attachment for a task.
    
    - **task_id**: Task ID to attach file to
    - **file**: File to attach
    - **description**: Optional description of the attachment
    """
    try:
        # Get task repository
        session = next(get_db_session())
        task_repo = SQLAlchemyTaskRepository(session)
        
        # Verify task exists and user has access
        task = await task_repo.find_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )
        
        # TODO: Check if user has access to the task (through project membership)
        
        # Read file content
        content = await file.read()
        
        # Validate file for attachments bucket
        bucket_manager = get_bucket_manager()
        validation = bucket_manager.validate_file_for_bucket("attachments", len(content), file.content_type)
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation["error"]
            )
        
        # Upload file
        storage_service = get_storage_service()
        result = await storage_service.upload_file(
            file_content=content,
            filename=file.filename,
            bucket="attachments",
            folder=f"tasks/{task_id}",
            user_id=user_id,
            content_type=file.content_type,
            make_public=False
        )
        
        # TODO: Create task attachment record in database
        # This would require a task_attachments table and repository
        
        return UploadResponse(
            success=True,
            file_path=result["file_path"],
            public_url=result["public_url"],
            signed_url=result["signed_url"],
            file_size=result["file_size"],
            content_type=result["content_type"],
            uploaded_at=result["uploaded_at"],
            message=f"Attachment uploaded successfully for task {task_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        )


@router.get("/task-attachments/{task_id}")
async def list_task_attachments(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    List all attachments for a task.
    
    - **task_id**: Task ID to list attachments for
    """
    try:
        # Get task repository
        session = next(get_db_session())
        task_repo = SQLAlchemyTaskRepository(session)
        
        # Verify task exists and user has access
        task = await task_repo.find_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )
        
        # List files in task folder
        storage_service = get_storage_service()
        files = await storage_service.list_files(
            folder=f"tasks/{task_id}",
            bucket="attachments"
        )
        
        # Generate signed URLs for private files
        attachments = []
        for file_info in files:
            signed_url = await storage_service.create_signed_url(
                file_path=file_info["name"],
                bucket="attachments",
                expires_in=3600  # 1 hour
            )
            
            attachments.append({
                "id": file_info.get("id"),
                "name": file_info["name"],
                "size": file_info.get("metadata", {}).get("size", 0),
                "content_type": file_info.get("metadata", {}).get("mimetype"),
                "created_at": file_info.get("created_at"),
                "download_url": signed_url
            })
        
        return {
            "task_id": task_id,
            "attachments": attachments,
            "total": len(attachments)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list attachments: {str(e)}"
        )


@router.delete("/attachment/{bucket}/{file_path:path}")
async def delete_attachment(
    bucket: str,
    file_path: str,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Delete a file attachment.
    
    - **bucket**: Storage bucket name
    - **file_path**: Path to file in bucket
    """
    try:
        # Validate bucket
        bucket_manager = get_bucket_manager()
        if not bucket_manager.get_bucket_config(bucket):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bucket: {bucket}"
            )
        
        # Check if user owns the file (file path should contain user_id)
        if user_id not in file_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file"
            )
        
        # Delete file
        storage_service = get_storage_service()
        success = await storage_service.delete_file(file_path, bucket)
        
        if success:
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/download/{bucket}/{file_path:path}")
async def download_file(
    bucket: str,
    file_path: str,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Download a file from storage.
    
    - **bucket**: Storage bucket name
    - **file_path**: Path to file in bucket
    """
    try:
        # Validate bucket
        bucket_manager = get_bucket_manager()
        if not bucket_manager.get_bucket_config(bucket):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bucket: {bucket}"
            )
        
        # For private buckets, check if user owns the file
        bucket_config = bucket_manager.get_bucket_config(bucket)
        if not bucket_config["public"] and user_id not in file_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file"
            )
        
        # Get signed URL for download
        storage_service = get_storage_service()
        signed_url = await storage_service.create_signed_url(
            file_path=file_path,
            bucket=bucket,
            expires_in=300  # 5 minutes
        )
        
        return {"download_url": signed_url}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/storage-stats")
async def get_storage_statistics(
    user_id: Annotated[str, Depends(get_current_user_id)],
    bucket: Optional[str] = Query(None, description="Specific bucket to check")
):
    """
    Get storage usage statistics for current user.
    
    - **bucket**: Optional specific bucket to check
    """
    try:
        bucket_manager = get_bucket_manager()
        
        if bucket:
            # Get stats for specific bucket
            if not bucket_manager.get_bucket_config(bucket):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid bucket: {bucket}"
                )
            
            stats = await bucket_manager.get_bucket_usage(bucket)
            user_stats = stats.get("user_usage", {}).get(user_id, {"files": 0, "size": 0})
            
            return {
                "bucket": bucket,
                "user_files": user_stats["files"],
                "user_size": user_stats["size"],
                "user_size_mb": round(user_stats["size"] / (1024 * 1024), 2),
                "bucket_total": stats.get("total_files", 0),
                "bucket_size_mb": stats.get("total_size_mb", 0)
            }
        else:
            # Get stats for all buckets
            all_stats = {}
            total_user_files = 0
            total_user_size = 0
            
            for bucket_name in bucket_manager.list_bucket_configs().keys():
                stats = await bucket_manager.get_bucket_usage(bucket_name)
                user_stats = stats.get("user_usage", {}).get(user_id, {"files": 0, "size": 0})
                
                all_stats[bucket_name] = {
                    "files": user_stats["files"],
                    "size": user_stats["size"],
                    "size_mb": round(user_stats["size"] / (1024 * 1024), 2)
                }
                
                total_user_files += user_stats["files"]
                total_user_size += user_stats["size"]
            
            return {
                "total_files": total_user_files,
                "total_size": total_user_size,
                "total_size_mb": round(total_user_size / (1024 * 1024), 2),
                "by_bucket": all_stats
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}"
        )