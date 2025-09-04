"""
Sharing and export router.
Handles sharing of projects, tasks, reports, and exports.
"""

from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
import io

from app.infrastructure.auth import get_current_user_id
from app.application.use_cases.share import (
    CreateShareUseCase,
    GetShareUseCase,
    ListSharesUseCase,
    RevokeShareUseCase,
    AccessSharedContentUseCase
)
from app.application.use_cases.export import (
    ExportProjectDataUseCase,
    ExportTimeEntriesUseCase,
    ExportInvoicesUseCase,
    ExportTasksUseCase
)
from app.application.dto.share import (
    CreateShareRequest,
    ShareResponse,
    ShareListResponse,
    SharedContentResponse
)
from app.application.dto.export import (
    ExportRequest,
    ExportResponse
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.share_repository import SQLAlchemyShareRepository
from app.domain.models.base import EntityNotFoundError, ValidationError, BusinessRuleViolation


router = APIRouter()


def get_share_repository(session=Depends(get_db_session)):
    """Dependency to get share repository."""
    return SQLAlchemyShareRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ShareResponse)
async def create_share(
    request: CreateShareRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)]
):
    """
    Create a shareable link for a resource.
    
    - **resource_type**: Type of resource to share (project, task, invoice, report)
    - **resource_id**: ID of the resource to share
    - **access_type**: Access level (view, edit)
    - **expires_at**: Optional expiration date
    - **password**: Optional password protection
    - **description**: Optional description of what's being shared
    - **allow_comments**: Whether to allow comments on shared content
    - **allow_downloads**: Whether to allow downloads
    """
    try:
        use_case = CreateShareUseCase(repository)
        share = await use_case.execute(user_id, request)
        return ShareResponse.from_domain(share)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=ShareListResponse)
async def list_shares(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)],
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[int] = Query(None, description="Filter by resource ID"),
    active_only: bool = Query(True, description="Show only active shares"),
    limit: int = Query(50, ge=1, le=100, description="Number of shares to return"),
    offset: int = Query(0, ge=0, description="Number of shares to skip")
):
    """
    List shares created by the authenticated user.
    
    - **resource_type**: Filter by resource type (project, task, invoice, report)
    - **resource_id**: Filter by specific resource ID
    - **active_only**: Show only active (non-expired, non-revoked) shares
    - **limit**: Maximum number of shares to return (1-100, default 50)
    - **offset**: Number of shares to skip for pagination
    """
    try:
        use_case = ListSharesUseCase(repository)
        
        if resource_type and resource_id:
            shares = await use_case.list_by_resource(user_id, resource_type, resource_id)
            total = len(shares)
        elif resource_type:
            shares = await use_case.list_by_type(user_id, resource_type, limit, offset)
            total = await use_case.count_by_type(user_id, resource_type)
        else:
            shares = await use_case.execute(user_id, active_only, limit, offset)
            total = await use_case.get_total_count(user_id, active_only)
        
        return ShareListResponse(
            shares=[ShareResponse.from_domain(share) for share in shares],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{share_id}", response_model=ShareResponse)
async def get_share(
    share_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)]
):
    """
    Get details of a specific share.
    
    - **share_id**: Share ID to retrieve
    """
    try:
        use_case = GetShareUseCase(repository)
        share = await use_case.execute(user_id, share_id)
        return ShareResponse.from_domain(share)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Share with id {share_id} not found"
        )


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    share_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)]
):
    """
    Revoke a share (disable access).
    
    - **share_id**: Share ID to revoke
    """
    try:
        use_case = RevokeShareUseCase(repository)
        await use_case.execute(user_id, share_id)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Share with id {share_id} not found"
        )


@router.get("/public/{token}", response_model=SharedContentResponse)
async def access_shared_content(
    token: str,
    password: Optional[str] = Query(None, description="Password if share is protected"),
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)]
):
    """
    Access shared content via public token (no authentication required).
    
    - **token**: Share token
    - **password**: Password if share is password protected
    """
    try:
        use_case = AccessSharedContentUseCase(repository)
        content = await use_case.execute(token, password)
        return SharedContentResponse.from_domain(content)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared content not found or expired"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/export/project/{project_id}")
async def export_project_data(
    project_id: int,
    request: ExportRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Export complete project data.
    
    - **project_id**: Project ID to export
    - **format**: Export format (json, csv, xlsx, pdf)
    - **include_tasks**: Include tasks data
    - **include_time_entries**: Include time tracking data
    - **include_invoices**: Include invoice data
    - **date_range**: Optional date range filter
    """
    try:
        use_case = ExportProjectDataUseCase()
        export_data = await use_case.execute(user_id, project_id, request)
        
        if request.format == "json":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=project_{project_id}.json"}
            )
        elif request.format == "csv":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=project_{project_id}.csv"}
            )
        elif request.format == "xlsx":
            return FileResponse(
                path=export_data.file_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"project_{project_id}.xlsx"
            )
        elif request.format == "pdf":
            return FileResponse(
                path=export_data.file_path,
                media_type="application/pdf",
                filename=f"project_{project_id}.pdf"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )
            
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/export/time-entries")
async def export_time_entries(
    request: ExportRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Optional[int] = Query(None, description="Filter by project"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter")
):
    """
    Export time entries data.
    
    - **format**: Export format (json, csv, xlsx)
    - **project_id**: Optional project filter
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    """
    try:
        use_case = ExportTimeEntriesUseCase()
        export_data = await use_case.execute(
            user_id, request, project_id, start_date, end_date
        )
        
        if request.format == "json":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=time_entries.json"}
            )
        elif request.format == "csv":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=time_entries.csv"}
            )
        elif request.format == "xlsx":
            return FileResponse(
                path=export_data.file_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename="time_entries.xlsx"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/export/tasks")
async def export_tasks(
    request: ExportRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Optional[int] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by task status")
):
    """
    Export tasks data.
    
    - **format**: Export format (json, csv, xlsx)
    - **project_id**: Optional project filter
    - **status**: Optional status filter
    """
    try:
        use_case = ExportTasksUseCase()
        export_data = await use_case.execute(user_id, request, project_id, status)
        
        if request.format == "json":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=tasks.json"}
            )
        elif request.format == "csv":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=tasks.csv"}
            )
        elif request.format == "xlsx":
            return FileResponse(
                path=export_data.file_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename="tasks.xlsx"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/export/invoices")
async def export_invoices(
    request: ExportRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    client_id: Optional[int] = Query(None, description="Filter by client"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter")
):
    """
    Export invoices data.
    
    - **format**: Export format (json, csv, xlsx)
    - **client_id**: Optional client filter
    - **status**: Optional status filter
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    """
    try:
        use_case = ExportInvoicesUseCase()
        export_data = await use_case.execute(
            user_id, request, client_id, status, start_date, end_date
        )
        
        if request.format == "json":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=invoices.json"}
            )
        elif request.format == "csv":
            return StreamingResponse(
                io.StringIO(export_data.content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=invoices.csv"}
            )
        elif request.format == "xlsx":
            return FileResponse(
                path=export_data.file_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename="invoices.xlsx"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/analytics/usage")
async def get_share_analytics(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyShareRepository, Depends(get_share_repository)],
    start_date: Optional[datetime] = Query(None, description="Analytics from date"),
    end_date: Optional[datetime] = Query(None, description="Analytics to date")
):
    """
    Get sharing and export analytics.
    
    - **start_date**: Analytics from this date
    - **end_date**: Analytics to this date
    """
    try:
        # TODO: Implement proper analytics logic
        # This would require additional use cases for analytics
        return {
            "user_id": user_id,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "shares": {
                "total_created": 0,
                "total_accessed": 0,
                "active_shares": 0,
                "expired_shares": 0,
                "most_shared_resource_type": None
            },
            "exports": {
                "total_exports": 0,
                "popular_formats": [],
                "most_exported_resource_type": None
            },
            "message": "Analytics not yet fully implemented"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
