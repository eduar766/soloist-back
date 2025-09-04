"""
Storage administration router.
Handles storage management, cleanup operations, and usage monitoring.
"""

from typing import Annotated, Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from datetime import datetime

from app.infrastructure.auth import get_current_user_id
from app.infrastructure.storage.bucket_manager import get_bucket_manager
from app.infrastructure.storage.cleanup_service import get_cleanup_service, CleanupRule
from app.domain.models.base import ValidationError
from pydantic import BaseModel


router = APIRouter()


class CleanupRuleRequest(BaseModel):
    """Request model for creating cleanup rules."""
    bucket: str
    folder_pattern: str
    max_age_days: int
    max_files_per_user: Optional[int] = None
    file_pattern: Optional[str] = None
    description: str


@router.get("/buckets")
async def list_storage_buckets(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    List all storage buckets and their configurations.
    """
    try:
        bucket_manager = get_bucket_manager()
        bucket_configs = bucket_manager.list_bucket_configs()
        
        return {
            "buckets": bucket_configs,
            "total_buckets": len(bucket_configs)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list buckets: {str(e)}"
        )


@router.post("/initialize-buckets")
async def initialize_storage_buckets(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Initialize all required storage buckets with proper policies.
    This should be run once during setup.
    """
    try:
        bucket_manager = get_bucket_manager()
        result = await bucket_manager.initialize_buckets()
        
        return {
            "message": "Bucket initialization completed",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize buckets: {str(e)}"
        )


@router.get("/usage/{bucket}")
async def get_bucket_usage(
    bucket: str,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get usage statistics for a specific bucket.
    
    - **bucket**: Bucket name to get usage for
    """
    try:
        bucket_manager = get_bucket_manager()
        
        # Validate bucket exists
        if not bucket_manager.get_bucket_config(bucket):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket}' not found"
            )
        
        usage_stats = await bucket_manager.get_bucket_usage(bucket)
        
        # Get user-specific stats
        user_stats = usage_stats.get("user_usage", {}).get(user_id, {
            "files": 0,
            "size": 0
        })
        
        return {
            "bucket": bucket,
            "user_stats": {
                "files": user_stats["files"],
                "size_bytes": user_stats["size"],
                "size_mb": round(user_stats["size"] / (1024 * 1024), 2)
            },
            "bucket_stats": {
                "total_files": usage_stats.get("total_files", 0),
                "total_size_mb": usage_stats.get("total_size_mb", 0),
                "unique_users": len(usage_stats.get("user_usage", {}))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bucket usage: {str(e)}"
        )


@router.get("/usage")
async def get_all_buckets_usage(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get usage statistics for all buckets.
    """
    try:
        bucket_manager = get_bucket_manager()
        bucket_configs = bucket_manager.list_bucket_configs()
        
        all_usage = {}
        total_user_files = 0
        total_user_size = 0
        
        for bucket_name in bucket_configs.keys():
            try:
                usage_stats = await bucket_manager.get_bucket_usage(bucket_name)
                user_stats = usage_stats.get("user_usage", {}).get(user_id, {
                    "files": 0,
                    "size": 0
                })
                
                all_usage[bucket_name] = {
                    "user_files": user_stats["files"],
                    "user_size_bytes": user_stats["size"],
                    "user_size_mb": round(user_stats["size"] / (1024 * 1024), 2),
                    "bucket_total_files": usage_stats.get("total_files", 0),
                    "bucket_total_size_mb": usage_stats.get("total_size_mb", 0)
                }
                
                total_user_files += user_stats["files"]
                total_user_size += user_stats["size"]
                
            except Exception as e:
                all_usage[bucket_name] = {"error": str(e)}
        
        return {
            "user_totals": {
                "files": total_user_files,
                "size_bytes": total_user_size,
                "size_mb": round(total_user_size / (1024 * 1024), 2)
            },
            "by_bucket": all_usage
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage statistics: {str(e)}"
        )


@router.post("/cleanup")
async def run_storage_cleanup(
    user_id: Annotated[str, Depends(get_current_user_id)],
    dry_run: bool = Query(True, description="If true, only show what would be deleted"),
    bucket: Optional[str] = Query(None, description="Run cleanup only for specific bucket"),
    rule_filter: Optional[str] = Query(None, description="Run only rules containing this text")
):
    """
    Run storage cleanup operations.
    
    - **dry_run**: If true, only show what would be deleted without actually deleting
    - **bucket**: Optional bucket name to limit cleanup to
    - **rule_filter**: Optional filter to run only specific cleanup rules
    """
    try:
        cleanup_service = get_cleanup_service()
        
        result = await cleanup_service.run_cleanup(
            dry_run=dry_run,
            specific_bucket=bucket,
            specific_rule=rule_filter
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run cleanup: {str(e)}"
        )


@router.get("/cleanup-suggestions")
async def get_cleanup_suggestions(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get personalized cleanup suggestions for current user.
    """
    try:
        cleanup_service = get_cleanup_service()
        suggestions = await cleanup_service.get_cleanup_suggestions(user_id)
        
        return suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cleanup suggestions: {str(e)}"
        )


@router.get("/cleanup-rules")
async def list_cleanup_rules(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    List all cleanup rules currently configured.
    """
    try:
        cleanup_service = get_cleanup_service()
        rules = cleanup_service.list_cleanup_rules()
        
        return {
            "cleanup_rules": rules,
            "total_rules": len(rules)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cleanup rules: {str(e)}"
        )


@router.post("/cleanup-rules")
async def add_cleanup_rule(
    rule_request: CleanupRuleRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Add a custom cleanup rule.
    
    - **bucket**: Bucket name to apply rule to
    - **folder_pattern**: Pattern for folder matching (supports *)
    - **max_age_days**: Maximum age of files in days before cleanup
    - **max_files_per_user**: Optional maximum files per user to keep
    - **file_pattern**: Optional pattern for filename matching
    - **description**: Description of the rule
    """
    try:
        # Validate bucket exists
        bucket_manager = get_bucket_manager()
        if not bucket_manager.get_bucket_config(rule_request.bucket):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bucket: {rule_request.bucket}"
            )
        
        # Create cleanup rule
        cleanup_rule = CleanupRule(
            bucket=rule_request.bucket,
            folder_pattern=rule_request.folder_pattern,
            max_age_days=rule_request.max_age_days,
            max_files_per_user=rule_request.max_files_per_user,
            file_pattern=rule_request.file_pattern,
            description=rule_request.description
        )
        
        cleanup_service = get_cleanup_service()
        cleanup_service.add_cleanup_rule(cleanup_rule)
        
        return {
            "message": "Cleanup rule added successfully",
            "rule": cleanup_rule.__dict__
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add cleanup rule: {str(e)}"
        )


@router.post("/cleanup-bucket/{bucket}")
async def cleanup_specific_bucket(
    bucket: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    older_than_days: int = Query(7, description="Delete files older than N days"),
    dry_run: bool = Query(True, description="If true, only show what would be deleted")
):
    """
    Run cleanup for a specific bucket with custom parameters.
    
    - **bucket**: Bucket name to clean up
    - **older_than_days**: Delete files older than this many days
    - **dry_run**: If true, only show what would be deleted
    """
    try:
        bucket_manager = get_bucket_manager()
        
        # Validate bucket exists
        if not bucket_manager.get_bucket_config(bucket):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket}' not found"
            )
        
        result = await bucket_manager.cleanup_bucket(
            bucket_name=bucket,
            older_than_days=older_than_days,
            dry_run=dry_run
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup bucket: {str(e)}"
        )


@router.get("/health")
async def storage_health_check(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Check storage system health and connectivity.
    """
    try:
        bucket_manager = get_bucket_manager()
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "buckets": {},
            "issues": []
        }
        
        # Check each bucket
        for bucket_name, config in bucket_manager.list_bucket_configs().items():
            try:
                # Try to list files to test connectivity
                from app.infrastructure.storage.storage_service import get_storage_service
                storage_service = get_storage_service()
                
                files = await storage_service.list_files(bucket=bucket_name, limit=1)
                
                health_status["buckets"][bucket_name] = {
                    "status": "healthy",
                    "accessible": True,
                    "config": config
                }
                
            except Exception as e:
                health_status["buckets"][bucket_name] = {
                    "status": "unhealthy",
                    "accessible": False,
                    "error": str(e)
                }
                health_status["issues"].append(f"Bucket {bucket_name}: {str(e)}")
        
        # Overall status
        unhealthy_buckets = [
            name for name, info in health_status["buckets"].items()
            if info["status"] == "unhealthy"
        ]
        
        if unhealthy_buckets:
            health_status["status"] = "degraded"
            health_status["unhealthy_buckets"] = unhealthy_buckets
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }