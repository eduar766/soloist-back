"""
Project management router.
Handles CRUD operations for project resources and project member management.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.infrastructure.auth import get_current_user_id
from app.application.use_cases.project_use_cases import (
    CreateProjectUseCase,
    UpdateProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    ArchiveProjectUseCase,
    InviteProjectMemberUseCase,
    RemoveProjectMemberUseCase
)
from app.application.dto.project import (
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberRequest
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.project_repository import SQLAlchemyProjectRepository
from app.domain.models.base import EntityNotFoundError, ValidationError, BusinessRuleViolation


router = APIRouter()


def get_project_repository(session=Depends(get_db_session)):
    """Dependency to get project repository."""
    return SQLAlchemyProjectRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Create a new project.
    
    - **name**: Project name (required)
    - **client_id**: Associated client ID (required)
    - **description**: Project description
    - **billing_type**: How the project is billed (hourly, fixed, etc.)
    - **hourly_rate**: Hourly rate for hourly billing
    - **fixed_budget**: Total budget for fixed billing
    - **currency**: Project currency
    - **start_date**: Project start date
    - **end_date**: Project end date
    - **estimated_hours**: Estimated hours to completion
    - **notes**: Additional notes
    - **tags**: List of tags
    - **is_billable**: Whether time tracked is billable by default
    """
    try:
        use_case = CreateProjectUseCase(repository)
        project = await use_case.execute(user_id, request)
        return ProjectResponse.from_domain(project)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)],
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip"),
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    status: Optional[str] = Query(None, description="Filter by project status"),
    search: Optional[str] = Query(None, description="Search projects by name")
):
    """
    List projects for the authenticated user.
    
    - **limit**: Maximum number of projects to return (1-100, default 50)
    - **offset**: Number of projects to skip for pagination
    - **client_id**: Filter by specific client
    - **status**: Filter by project status (active, completed, archived)
    - **search**: Search projects by name
    """
    try:
        use_case = ListProjectsUseCase(repository)
        
        if client_id:
            projects = await use_case.list_by_client(client_id, limit)
            total = len(projects)  # Simplified
        elif search:
            projects = await use_case.search_by_name(user_id, search, limit)
            total = len(projects)
        elif status:
            projects = await use_case.list_by_status(user_id, status)
            total = len(projects)
        else:
            projects = await use_case.execute(user_id, limit, offset)
            total = await use_case.get_total_count(user_id)
        
        return ProjectListResponse(
            projects=[ProjectResponse.from_domain(project) for project in projects],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Get a specific project by ID.
    
    - **project_id**: Project ID to retrieve
    """
    try:
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        return ProjectResponse.from_domain(project)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Update an existing project.
    
    - **project_id**: Project ID to update
    - **name**: Updated project name
    - **description**: Updated description
    - **billing_type**: Updated billing type
    - **hourly_rate**: Updated hourly rate
    - **fixed_budget**: Updated fixed budget
    - **currency**: Updated currency
    - **start_date**: Updated start date
    - **end_date**: Updated end date
    - **estimated_hours**: Updated estimated hours
    - **notes**: Updated notes
    - **tags**: Updated tags list
    - **is_billable**: Updated billable status
    """
    try:
        use_case = UpdateProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id, request)
        return ProjectResponse.from_domain(project)
        
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


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)],
    reason: Optional[str] = Query(None, description="Reason for archiving")
):
    """
    Archive (soft delete) a project.
    
    - **project_id**: Project ID to archive
    - **reason**: Optional reason for archiving
    """
    try:
        use_case = ArchiveProjectUseCase(repository)
        await use_case.execute(user_id, project_id, reason)
        
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


@router.post("/{project_id}/complete", response_model=ProjectResponse)
async def complete_project(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Mark a project as completed.
    
    - **project_id**: Project ID to complete
    """
    try:
        # Get the project first
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # Complete it
        project.complete()
        
        # Save changes
        repository.save(project)
        
        return ProjectResponse.from_domain(project)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{project_id}/reactivate", response_model=ProjectResponse)
async def reactivate_project(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Reactivate a completed or archived project.
    
    - **project_id**: Project ID to reactivate
    """
    try:
        # Get the project first
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # Reactivate it
        project.reactivate()
        
        # Save changes
        repository.save(project)
        
        return ProjectResponse.from_domain(project)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_project_member(
    project_id: int,
    request: ProjectMemberRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Invite a member to a project.
    
    - **project_id**: Project ID
    - **email**: Email of user to invite
    - **role**: Role to assign (member, admin)
    """
    try:
        use_case = InviteProjectMemberUseCase(repository)
        await use_case.execute(user_id, project_id, request)
        
        return {"message": f"Invitation sent to {request.email}"}
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{project_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    member_user_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Remove a member from a project.
    
    - **project_id**: Project ID
    - **member_user_id**: ID of user to remove
    """
    try:
        use_case = RemoveProjectMemberUseCase(repository)
        await use_case.execute(user_id, project_id, member_user_id)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or member not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{project_id}/members")
async def get_project_members(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Get all members of a project.
    
    - **project_id**: Project ID
    """
    try:
        # First verify project exists and user has access
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # TODO: Implement member retrieval
        # This would require the project member repository/table
        return {
            "project_id": project_id,
            "members": [],  # Placeholder
            "message": "Member listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )


@router.get("/{project_id}/tasks")
async def get_project_tasks(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)],
    status: Optional[str] = Query(None, description="Filter by task status"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee")
):
    """
    Get all tasks for a project.
    
    - **project_id**: Project ID
    - **status**: Filter by task status
    - **assignee_id**: Filter by assigned user
    """
    try:
        # First verify project exists and user has access
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # TODO: Implement task retrieval
        # This would require the task repository
        return {
            "project_id": project_id,
            "tasks": [],  # Placeholder
            "filters": {
                "status": status,
                "assignee_id": assignee_id
            },
            "message": "Task listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )


@router.get("/{project_id}/time-entries")
async def get_project_time_entries(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Get all time entries for a project.
    
    - **project_id**: Project ID
    """
    try:
        # First verify project exists and user has access
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # TODO: Implement time entry retrieval
        # This would require the time entry repository
        return {
            "project_id": project_id,
            "time_entries": [],  # Placeholder
            "message": "Time entry listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )


@router.get("/{project_id}/invoices")
async def get_project_invoices(
    project_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyProjectRepository, Depends(get_project_repository)]
):
    """
    Get all invoices for a project.
    
    - **project_id**: Project ID
    """
    try:
        # First verify project exists and user has access
        use_case = GetProjectUseCase(repository)
        project = await use_case.execute(user_id, project_id)
        
        # TODO: Implement invoice retrieval
        # This would require the invoice repository
        return {
            "project_id": project_id,
            "invoices": [],  # Placeholder
            "message": "Invoice listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )