"""
Time tracking router.
Handles time entry management, timer controls, and time reporting.
"""

from typing import Annotated, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.infrastructure.auth import get_current_user_id
from app.application.use_cases.time_entry import (
    CreateTimeEntryUseCase,
    UpdateTimeEntryUseCase,
    GetTimeEntryUseCase,
    ListTimeEntriesUseCase,
    DeleteTimeEntryUseCase,
    StartTimerUseCase,
    StopTimerUseCase,
    GetActiveTimerUseCase
)
from app.application.dto.time_entry import (
    CreateTimeEntryRequest,
    UpdateTimeEntryRequest,
    TimeEntryResponse,
    TimeEntryListResponse,
    StartTimerRequest,
    TimerResponse
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.time_entry_repository import SQLAlchemyTimeEntryRepository
from app.domain.models.base import EntityNotFoundError, ValidationError, BusinessRuleViolation


router = APIRouter()


def get_time_entry_repository(session=Depends(get_db_session)):
    """Dependency to get time entry repository."""
    return SQLAlchemyTimeEntryRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TimeEntryResponse)
async def create_time_entry(
    request: CreateTimeEntryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Create a new time entry.
    
    - **task_id**: Task ID to log time for (optional if project_id provided)
    - **project_id**: Project ID to log time for (required)
    - **description**: Description of work performed
    - **start_time**: Start timestamp (ISO format)
    - **end_time**: End timestamp (ISO format, optional for timer-based entries)
    - **duration_minutes**: Duration in minutes (optional, calculated from start/end if not provided)
    - **is_billable**: Whether this time is billable
    - **hourly_rate**: Override hourly rate for this entry
    - **tags**: List of tags for categorization
    """
    try:
        use_case = CreateTimeEntryUseCase(repository)
        time_entry = await use_case.execute(user_id, request)
        return TimeEntryResponse.from_domain(time_entry)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=TimeEntryListResponse)
async def list_time_entries(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)],
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    is_billable: Optional[bool] = Query(None, description="Filter by billable status"),
    limit: int = Query(50, ge=1, le=100, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip")
):
    """
    List time entries for the authenticated user.
    
    - **project_id**: Filter by specific project
    - **task_id**: Filter by specific task
    - **start_date**: Filter entries from this date
    - **end_date**: Filter entries to this date
    - **is_billable**: Filter by billable status
    - **limit**: Maximum number of entries to return (1-100, default 50)
    - **offset**: Number of entries to skip for pagination
    """
    try:
        use_case = ListTimeEntriesUseCase(repository)
        
        if project_id:
            entries = await use_case.list_by_project(project_id, start_date, end_date, limit, offset)
            total = await use_case.count_by_project(project_id, start_date, end_date)
        elif task_id:
            entries = await use_case.list_by_task(task_id, limit, offset)
            total = await use_case.count_by_task(task_id)
        else:
            entries = await use_case.execute(user_id, start_date, end_date, is_billable, limit, offset)
            total = await use_case.get_total_count(user_id, start_date, end_date, is_billable)
        
        return TimeEntryListResponse(
            time_entries=[TimeEntryResponse.from_domain(entry) for entry in entries],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{time_entry_id}", response_model=TimeEntryResponse)
async def get_time_entry(
    time_entry_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Get a specific time entry by ID.
    
    - **time_entry_id**: Time entry ID to retrieve
    """
    try:
        use_case = GetTimeEntryUseCase(repository)
        time_entry = await use_case.execute(user_id, time_entry_id)
        return TimeEntryResponse.from_domain(time_entry)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time entry with id {time_entry_id} not found"
        )


@router.put("/{time_entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    time_entry_id: int,
    request: UpdateTimeEntryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Update an existing time entry.
    
    - **time_entry_id**: Time entry ID to update
    - **description**: Updated description
    - **start_time**: Updated start time
    - **end_time**: Updated end time
    - **duration_minutes**: Updated duration
    - **is_billable**: Updated billable status
    - **hourly_rate**: Updated hourly rate
    - **tags**: Updated tags list
    """
    try:
        use_case = UpdateTimeEntryUseCase(repository)
        time_entry = await use_case.execute(user_id, time_entry_id, request)
        return TimeEntryResponse.from_domain(time_entry)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time entry with id {time_entry_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{time_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    time_entry_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Delete a time entry.
    
    - **time_entry_id**: Time entry ID to delete
    """
    try:
        use_case = DeleteTimeEntryUseCase(repository)
        await use_case.execute(user_id, time_entry_id)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time entry with id {time_entry_id} not found"
        )


@router.post("/timer/start", status_code=status.HTTP_201_CREATED, response_model=TimerResponse)
async def start_timer(
    request: StartTimerRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Start a new timer for time tracking.
    
    - **task_id**: Task ID to track time for (optional if project_id provided)
    - **project_id**: Project ID to track time for (required)
    - **description**: Description of work being performed
    - **is_billable**: Whether this time should be billable
    """
    try:
        use_case = StartTimerUseCase(repository)
        timer = await use_case.execute(user_id, request)
        return TimerResponse.from_domain(timer)
        
    except BusinessRuleViolation as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/timer/stop", response_model=TimeEntryResponse)
async def stop_timer(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Stop the currently active timer and create a time entry.
    """
    try:
        use_case = StopTimerUseCase(repository)
        time_entry = await use_case.execute(user_id)
        return TimeEntryResponse.from_domain(time_entry)
        
    except BusinessRuleViolation as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/timer/active", response_model=TimerResponse)
async def get_active_timer(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)]
):
    """
    Get the currently active timer for the user.
    """
    try:
        use_case = GetActiveTimerUseCase(repository)
        timer = await use_case.execute(user_id)
        return TimerResponse.from_domain(timer)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active timer found"
        )


@router.get("/reports/summary")
async def get_time_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTimeEntryRepository, Depends(get_time_entry_repository)],
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    start_date: Optional[datetime] = Query(None, description="Summary from date"),
    end_date: Optional[datetime] = Query(None, description="Summary to date"),
    group_by: str = Query("day", description="Group by: day, week, month, project, task")
):
    """
    Get time tracking summary and reports.
    
    - **project_id**: Filter by specific project
    - **start_date**: Summary from this date
    - **end_date**: Summary to this date
    - **group_by**: How to group the data (day, week, month, project, task)
    """
    try:
        use_case = ListTimeEntriesUseCase(repository)
        
        # TODO: Implement proper reporting logic
        # This would require additional use cases for generating reports
        return {
            "user_id": user_id,
            "filters": {
                "project_id": project_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "group_by": group_by
            },
            "summary": {
                "total_hours": 0,
                "billable_hours": 0,
                "total_earnings": 0,
                "entries_count": 0
            },
            "message": "Time reporting not yet fully implemented"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
