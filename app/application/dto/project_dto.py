"""
Project DTOs for the application layer.
Data Transfer Objects for project-related operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import Field, validator
from enum import Enum

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin, TagsMixin, NotesMixin
)


class ProjectStatus(str, Enum):
    """Project status options."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ProjectMemberRole(str, Enum):
    """Project member role options."""
    OWNER = "owner"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class BillingType(str, Enum):
    """Project billing type options."""
    HOURLY = "hourly"
    FIXED = "fixed"
    RETAINER = "retainer"
    NON_BILLABLE = "non_billable"


# Nested DTOs
class ProjectMemberRequestDTO(RequestDTO):
    """DTO for project member in requests."""
    
    user_id: str = Field(description="User ID")
    role: ProjectMemberRole = Field(description="Member role")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Member hourly rate")


class ProjectMemberResponseDTO(ResponseDTO):
    """DTO for project member in responses."""
    
    user_id: str = Field(description="User ID")
    user_name: Optional[str] = Field(default=None, description="User full name")
    user_email: Optional[str] = Field(default=None, description="User email")
    user_avatar: Optional[str] = Field(default=None, description="User avatar URL")
    role: ProjectMemberRole = Field(description="Member role")
    hourly_rate: Optional[float] = Field(default=None, description="Member hourly rate")
    joined_at: datetime = Field(description="When member joined project")


class ProjectBudgetResponseDTO(ResponseDTO):
    """DTO for project budget information."""
    
    total_budget: Optional[float] = Field(default=None, description="Total project budget")
    spent_amount: float = Field(description="Amount spent so far")
    remaining_budget: Optional[float] = Field(default=None, description="Remaining budget")
    budget_utilization: Optional[float] = Field(default=None, description="Budget utilization percentage")
    estimated_completion_cost: Optional[float] = Field(default=None, description="Estimated total cost")


class ProjectTimeStatsDTO(ResponseDTO):
    """DTO for project time statistics."""
    
    total_hours: float = Field(description="Total hours logged")
    billable_hours: float = Field(description="Total billable hours")
    non_billable_hours: float = Field(description="Total non-billable hours")
    hours_this_week: float = Field(description="Hours logged this week")
    hours_this_month: float = Field(description="Hours logged this month")
    estimated_remaining_hours: Optional[float] = Field(default=None, description="Estimated remaining hours")


# Request DTOs
class CreateProjectRequestDTO(CreateRequestDTO, TagsMixin, NotesMixin):
    """DTO for project creation requests."""
    
    client_id: int = Field(description="Client ID")
    name: str = Field(min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Project description")
    
    # Billing configuration
    billing_type: BillingType = Field(description="Billing type")
    default_hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    fixed_budget: Optional[float] = Field(default=None, ge=0, description="Fixed budget amount")
    currency: str = Field(default="USD", max_length=3, description="Project currency")
    
    # Timeline
    start_date: Optional[date] = Field(default=None, description="Project start date")
    due_date: Optional[date] = Field(default=None, description="Project due date")
    estimated_hours: Optional[float] = Field(default=None, ge=0, description="Estimated hours")
    
    # Initial members
    members: Optional[List[ProjectMemberRequestDTO]] = Field(default=None, description="Initial project members")
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate that due date is after start date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('Due date must be after start date')
        return v
    
    @validator('fixed_budget')
    def validate_fixed_budget(cls, v, values):
        """Validate fixed budget is provided for fixed billing type."""
        billing_type = values.get('billing_type')
        if billing_type == BillingType.FIXED and not v:
            raise ValueError('Fixed budget is required for fixed billing projects')
        return v


class UpdateProjectRequestDTO(UpdateRequestDTO, TagsMixin, NotesMixin):
    """DTO for project update requests."""
    
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Project description")
    status: Optional[ProjectStatus] = Field(default=None, description="Project status")
    
    # Billing configuration
    billing_type: Optional[BillingType] = Field(default=None, description="Billing type")
    default_hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    fixed_budget: Optional[float] = Field(default=None, ge=0, description="Fixed budget amount")
    currency: Optional[str] = Field(default=None, max_length=3, description="Project currency")
    
    # Timeline
    start_date: Optional[date] = Field(default=None, description="Project start date")
    due_date: Optional[date] = Field(default=None, description="Project due date")
    estimated_hours: Optional[float] = Field(default=None, ge=0, description="Estimated hours")
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate that due date is after start date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('Due date must be after start date')
        return v


class UpdateProjectStatusRequestDTO(RequestDTO):
    """DTO for updating project status."""
    
    status: ProjectStatus = Field(description="New project status")
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for status change")


class AddProjectMemberRequestDTO(RequestDTO):
    """DTO for adding a member to project."""
    
    user_id: str = Field(description="User ID to add")
    role: ProjectMemberRole = Field(description="Member role")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Member hourly rate")


class UpdateProjectMemberRequestDTO(RequestDTO):
    """DTO for updating project member."""
    
    role: Optional[ProjectMemberRole] = Field(default=None, description="Member role")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Member hourly rate")


class ListProjectsRequestDTO(FilterRequestDTO, TagsMixin):
    """DTO for listing projects with filters."""
    
    client_id: Optional[int] = Field(default=None, description="Filter by client ID")
    status: Optional[ProjectStatus] = Field(default=None, description="Filter by project status")
    billing_type: Optional[BillingType] = Field(default=None, description="Filter by billing type")
    member_id: Optional[str] = Field(default=None, description="Filter by member user ID")
    is_overdue: Optional[bool] = Field(default=None, description="Filter overdue projects")
    is_over_budget: Optional[bool] = Field(default=None, description="Filter over-budget projects")
    has_time_entries: Optional[bool] = Field(default=None, description="Filter projects with time entries")


class SearchProjectsRequestDTO(ListProjectsRequestDTO):
    """DTO for searching projects."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")


class ProjectTimeRangeRequestDTO(RequestDTO):
    """DTO for project time-based reports."""
    
    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate that end date is after start date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v


# Response DTOs
class ProjectStatsResponseDTO(ResponseDTO):
    """DTO for project statistics."""
    
    total_tasks: int = Field(description="Total number of tasks")
    completed_tasks: int = Field(description="Number of completed tasks")
    pending_tasks: int = Field(description="Number of pending tasks")
    in_progress_tasks: int = Field(description="Number of in-progress tasks")
    
    time_stats: ProjectTimeStatsDTO = Field(description="Time tracking statistics")
    budget_stats: Optional[ProjectBudgetResponseDTO] = Field(default=None, description="Budget statistics")
    
    active_members: int = Field(description="Number of active members")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")


class ProjectResponseDTO(ResponseDTO, TimestampMixin, TagsMixin, NotesMixin):
    """DTO for project response."""
    
    owner_id: str = Field(description="Project owner user ID")
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    status: ProjectStatus = Field(description="Project status")
    
    # Billing configuration
    billing_type: BillingType = Field(description="Billing type")
    default_hourly_rate: Optional[float] = Field(default=None, description="Default hourly rate")
    fixed_budget: Optional[float] = Field(default=None, description="Fixed budget amount")
    currency: str = Field(description="Project currency")
    
    # Timeline
    start_date: Optional[date] = Field(default=None, description="Project start date")
    due_date: Optional[date] = Field(default=None, description="Project due date")
    estimated_hours: Optional[float] = Field(default=None, description="Estimated hours")
    completed_at: Optional[datetime] = Field(default=None, description="Project completion timestamp")
    
    # Members
    members: List[ProjectMemberResponseDTO] = Field(description="Project members")
    
    # Statistics
    stats: Optional[ProjectStatsResponseDTO] = Field(default=None, description="Project statistics")
    
    # Computed fields
    is_active: bool = Field(description="Whether project is active")
    is_overdue: bool = Field(description="Whether project is overdue")
    is_over_budget: bool = Field(description="Whether project is over budget")
    progress_percentage: Optional[float] = Field(default=None, description="Project progress percentage")
    days_remaining: Optional[int] = Field(default=None, description="Days remaining until due date")


class ProjectSummaryResponseDTO(ResponseDTO):
    """DTO for project summary (used in lists)."""
    
    owner_id: str = Field(description="Project owner user ID")
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    name: str = Field(description="Project name")
    status: ProjectStatus = Field(description="Project status")
    billing_type: BillingType = Field(description="Billing type")
    currency: str = Field(description="Project currency")
    
    # Timeline
    start_date: Optional[date] = Field(default=None, description="Project start date")
    due_date: Optional[date] = Field(default=None, description="Project due date")
    
    # Quick stats
    total_hours: float = Field(description="Total hours logged")
    total_tasks: int = Field(description="Total number of tasks")
    completed_tasks: int = Field(description="Number of completed tasks")
    active_members: int = Field(description="Number of active members")
    
    # Status indicators
    is_overdue: bool = Field(description="Whether project is overdue")
    is_over_budget: bool = Field(description="Whether project is over budget")
    progress_percentage: Optional[float] = Field(default=None, description="Project progress percentage")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")


class ProjectActivityResponseDTO(ResponseDTO):
    """DTO for project activity response."""
    
    date: datetime = Field(description="Activity date")
    activity_type: str = Field(description="Type of activity")
    description: str = Field(description="Activity description")
    user_id: str = Field(description="User who performed activity")
    user_name: Optional[str] = Field(default=None, description="User name")
    task_id: Optional[int] = Field(default=None, description="Related task ID")
    task_title: Optional[str] = Field(default=None, description="Related task title")
    hours: Optional[float] = Field(default=None, description="Hours if time-related activity")


class ProjectReportResponseDTO(ResponseDTO):
    """DTO for project reports."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    client_name: str = Field(description="Client name")
    report_period_start: date = Field(description="Report period start")
    report_period_end: date = Field(description="Report period end")
    
    # Time summary
    total_hours: float = Field(description="Total hours in period")
    billable_hours: float = Field(description="Billable hours in period")
    non_billable_hours: float = Field(description="Non-billable hours in period")
    
    # Member breakdown
    member_hours: List[Dict[str, Any]] = Field(description="Hours breakdown by member")
    
    # Task breakdown  
    task_hours: List[Dict[str, Any]] = Field(description="Hours breakdown by task")
    
    # Daily breakdown
    daily_hours: List[Dict[str, Any]] = Field(description="Daily hours breakdown")
    
    # Financial summary (if applicable)
    estimated_revenue: Optional[float] = Field(default=None, description="Estimated revenue for period")
    hourly_rate_avg: Optional[float] = Field(default=None, description="Average hourly rate")


# Bulk operation DTOs
class BulkUpdateProjectsRequestDTO(RequestDTO):
    """DTO for bulk project updates."""
    
    project_ids: List[int] = Field(min_items=1, max_items=100, description="List of project IDs")
    status: Optional[ProjectStatus] = Field(default=None, description="New status")
    tags_to_add: Optional[List[str]] = Field(default=None, description="Tags to add")
    tags_to_remove: Optional[List[str]] = Field(default=None, description="Tags to remove")


class ArchiveProjectRequestDTO(RequestDTO):
    """DTO for archiving a project."""
    
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for archiving")
    archive_time_entries: bool = Field(default=False, description="Whether to archive related time entries")


# Analytics DTOs
class ProjectAnalyticsResponseDTO(ResponseDTO):
    """DTO for project analytics."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    
    # Time metrics
    total_time_logged: float = Field(description="Total time logged (hours)")
    time_trend: List[Dict[str, Any]] = Field(description="Time logging trend over time")
    productivity_score: float = Field(description="Productivity score (0-100)")
    
    # Budget metrics
    budget_utilization: Optional[float] = Field(default=None, description="Budget utilization percentage")
    cost_trend: List[Dict[str, Any]] = Field(description="Cost trend over time")
    
    # Team metrics
    member_productivity: List[Dict[str, Any]] = Field(description="Productivity by team member")
    collaboration_score: float = Field(description="Team collaboration score")
    
    # Task metrics
    task_completion_rate: float = Field(description="Task completion rate percentage")
    average_task_duration: Optional[float] = Field(default=None, description="Average task duration in hours")
    
    # Timeline metrics
    schedule_performance: float = Field(description="Schedule performance index")
    estimated_completion_date: Optional[date] = Field(default=None, description="Estimated completion date")
    
    last_calculated: datetime = Field(description="When analytics were calculated")