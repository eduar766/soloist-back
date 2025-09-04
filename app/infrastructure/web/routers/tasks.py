"""
Task management router.
Handles CRUD operations for task resources within projects.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.infrastructure.auth import get_current_user_id
from app.application.use_cases.task import (
    CreateTaskUseCase,
    UpdateTaskUseCase,
    GetTaskUseCase,
    ListTasksUseCase,
    MoveTaskUseCase,
    AssignTaskUseCase,
    CommentTaskUseCase
)
from app.application.dto.task import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskResponse,
    TaskListResponse,
    MoveTaskRequest,
    AssignTaskRequest,
    CommentTaskRequest
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.task_repository import SQLAlchemyTaskRepository
from app.domain.models.base import EntityNotFoundError, ValidationError, BusinessRuleViolation


router = APIRouter()


def get_task_repository(session=Depends(get_db_session)):
    """Dependency to get task repository."""
    return SQLAlchemyTaskRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Create a new task within a project.
    
    - **project_id**: Project ID (required)
    - **title**: Task title (required)
    - **description**: Task description
    - **priority**: Task priority (low, medium, high, urgent)
    - **assignee_id**: User ID to assign the task to
    - **due_date**: Due date for the task
    - **estimated_hours**: Estimated hours to complete
    - **tags**: List of tags
    - **is_billable**: Whether time tracked on this task is billable
    """
    try:
        use_case = CreateTaskUseCase(repository)
        task = await use_case.execute(user_id, request)
        return TaskResponse.from_domain(task)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)],
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue: bool = Query(False, description="Show only overdue tasks"),
    limit: int = Query(50, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip")
):
    """
    List tasks accessible to the authenticated user.
    
    - **project_id**: Filter by specific project
    - **assignee_id**: Filter by assigned user
    - **status**: Filter by task status (todo, in_progress, completed)
    - **priority**: Filter by priority level
    - **overdue**: Show only overdue tasks
    - **limit**: Maximum number of tasks to return (1-100, default 50)
    - **offset**: Number of tasks to skip for pagination
    """
    try:
        use_case = ListTasksUseCase(repository)
        
        if project_id:
            tasks = await use_case.list_by_project(project_id, limit, offset)
            total = await use_case.count_by_project(project_id)
        elif assignee_id:
            tasks = await use_case.list_by_assignee(assignee_id, limit)
            total = len(tasks)  # Simplified
        elif overdue:
            tasks = await use_case.list_overdue(assignee_id)
            total = len(tasks)
        elif status:
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="project_id is required when filtering by status"
                )
            tasks = await use_case.list_by_status(project_id, status)
            total = len(tasks)
        else:
            tasks = await use_case.execute(user_id, limit, offset)
            total = await use_case.get_total_count(user_id)
        
        return TaskListResponse(
            tasks=[TaskResponse.from_domain(task) for task in tasks],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Get a specific task by ID.
    
    - **task_id**: Task ID to retrieve
    """
    try:
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        return TaskResponse.from_domain(task)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: UpdateTaskRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Update an existing task.
    
    - **task_id**: Task ID to update
    - **title**: Updated task title
    - **description**: Updated description
    - **priority**: Updated priority
    - **due_date**: Updated due date
    - **estimated_hours**: Updated estimated hours
    - **tags**: Updated tags list
    - **is_billable**: Updated billable status
    """
    try:
        use_case = UpdateTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id, request)
        return TaskResponse.from_domain(task)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Delete a task.
    
    - **task_id**: Task ID to delete
    """
    try:
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        
        # Delete the task
        repository.delete(task_id)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )


@router.put("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: int,
    request: MoveTaskRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Move task to different status/state.
    
    - **task_id**: Task ID to move
    - **status**: New status (todo, in_progress, completed)
    - **position**: Optional new position within the status column
    """
    try:
        use_case = MoveTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id, request)
        return TaskResponse.from_domain(task)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: int,
    request: AssignTaskRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Assign task to a user.
    
    - **task_id**: Task ID to assign
    - **assignee_id**: User ID to assign the task to (null to unassign)
    """
    try:
        use_case = AssignTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id, request)
        return TaskResponse.from_domain(task)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    task_id: int,
    request: CommentTaskRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Add a comment to a task.
    
    - **task_id**: Task ID to comment on
    - **comment**: Comment text
    """
    try:
        use_case = CommentTaskUseCase(repository)
        comment = await use_case.execute(user_id, task_id, request)
        
        return {
            "id": comment.id,
            "task_id": task_id,
            "comment": comment.comment,
            "author_id": comment.author_id,
            "created_at": comment.created_at.isoformat()
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{task_id}/comments")
async def get_task_comments(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Get all comments for a task.
    
    - **task_id**: Task ID
    """
    try:
        # First verify task exists and user has access
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        
        # TODO: Implement comment retrieval
        # This would require the task comment repository/table
        return {
            "task_id": task_id,
            "comments": [],  # Placeholder
            "message": "Comment listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )


@router.get("/{task_id}/time-entries")
async def get_task_time_entries(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Get all time entries for a task.
    
    - **task_id**: Task ID
    """
    try:
        # First verify task exists and user has access
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        
        # TODO: Implement time entry retrieval
        # This would require the time entry repository
        return {
            "task_id": task_id,
            "time_entries": [],  # Placeholder
            "message": "Time entry listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )


@router.post("/{task_id}/attachments")
async def add_task_attachment(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Add an attachment to a task.
    
    - **task_id**: Task ID
    """
    try:
        # First verify task exists and user has access
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        
        # TODO: Implement file upload and attachment creation
        # This would require Supabase Storage integration
        return {
            "task_id": task_id,
            "message": "File attachment not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )


@router.get("/{task_id}/attachments")
async def get_task_attachments(
    task_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyTaskRepository, Depends(get_task_repository)]
):
    """
    Get all attachments for a task.
    
    - **task_id**: Task ID
    """
    try:
        # First verify task exists and user has access
        use_case = GetTaskUseCase(repository)
        task = await use_case.execute(user_id, task_id)
        
        # TODO: Implement attachment retrieval
        # This would require the task attachment repository/table
        return {
            "task_id": task_id,
            "attachments": [],  # Placeholder
            "message": "Attachment listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )