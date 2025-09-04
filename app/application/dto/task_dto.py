"""
Task DTOs for the application layer.
Data Transfer Objects for task-related operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import Field, validator
from enum import Enum

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin, TagsMixin, NotesMixin
)


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task status options."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


# Nested DTOs
class TaskAttachmentRequestDTO(RequestDTO):
    """DTO for task attachment in requests."""
    
    filename: str = Field(max_length=255, description="Attachment filename")
    file_url: str = Field(max_length=500, description="Attachment file URL")
    file_size: Optional[int] = Field(default=None, ge=0, description="File size in bytes")
    mime_type: Optional[str] = Field(default=None, max_length=100, description="MIME type")


class TaskAttachmentResponseDTO(ResponseDTO):
    """DTO for task attachment in responses."""
    
    filename: str = Field(description="Attachment filename")
    file_url: str = Field(description="Attachment file URL")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    uploaded_by: str = Field(description="User ID who uploaded the file")
    uploaded_by_name: Optional[str] = Field(default=None, description="Name of user who uploaded")
    uploaded_at: datetime = Field(description="Upload timestamp")


class TaskCommentRequestDTO(RequestDTO):
    """DTO for task comment in requests."""
    
    content: str = Field(min_length=1, max_length=2000, description="Comment content")


class TaskCommentResponseDTO(ResponseDTO):
    """DTO for task comment in responses."""
    
    content: str = Field(description="Comment content")
    author_id: str = Field(description="Comment author user ID")
    author_name: Optional[str] = Field(default=None, description="Author name")
    author_avatar: Optional[str] = Field(default=None, description="Author avatar URL")
    created_at: datetime = Field(description="Comment creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Comment update timestamp")
    is_edited: bool = Field(description="Whether comment was edited")


class TaskTimeStatsDTO(ResponseDTO):
    """DTO for task time statistics."""
    
    total_logged_hours: float = Field(description="Total hours logged")
    estimated_hours: Optional[float] = Field(default=None, description="Estimated hours")
    remaining_hours: Optional[float] = Field(default=None, description="Estimated remaining hours")
    time_efficiency: Optional[float] = Field(default=None, description="Time efficiency percentage")
    last_time_entry: Optional[datetime] = Field(default=None, description="Last time entry timestamp")


# Request DTOs
class CreateTaskRequestDTO(CreateRequestDTO, TagsMixin, NotesMixin):
    """DTO for task creation requests."""
    
    project_id: int = Field(description="Project ID")
    title: str = Field(min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(default=None, max_length=2000, description="Task description")
    
    # Assignment and priority
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    
    # Timeline
    due_date: Optional[date] = Field(default=None, description="Task due date")
    estimated_hours: Optional[float] = Field(default=None, ge=0, description="Estimated hours")
    
    # Organization
    parent_task_id: Optional[int] = Field(default=None, description="Parent task ID")
    depends_on_task_ids: Optional[List[int]] = Field(default=None, description="Task dependencies")
    
    # Initial attachments
    attachments: Optional[List[TaskAttachmentRequestDTO]] = Field(default=None, description="Initial attachments")


class UpdateTaskRequestDTO(UpdateRequestDTO, TagsMixin, NotesMixin):
    """DTO for task update requests."""
    
    title: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(default=None, max_length=2000, description="Task description")
    
    # Assignment and priority
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    priority: Optional[TaskPriority] = Field(default=None, description="Task priority")
    status: Optional[TaskStatus] = Field(default=None, description="Task status")
    
    # Timeline
    due_date: Optional[date] = Field(default=None, description="Task due date")
    estimated_hours: Optional[float] = Field(default=None, ge=0, description="Estimated hours")
    
    # Organization
    parent_task_id: Optional[int] = Field(default=None, description="Parent task ID")
    depends_on_task_ids: Optional[List[int]] = Field(default=None, description="Task dependencies")


class UpdateTaskStatusRequestDTO(RequestDTO):
    """DTO for updating task status."""
    
    status: TaskStatus = Field(description="New task status")
    comment: Optional[str] = Field(default=None, max_length=500, description="Status change comment")


class AssignTaskRequestDTO(RequestDTO):
    """DTO for assigning task to user."""
    
    assignee_id: str = Field(description="User ID to assign task to")
    comment: Optional[str] = Field(default=None, max_length=500, description="Assignment comment")


class MoveTaskRequestDTO(RequestDTO):
    """DTO for moving task to different status/state."""
    
    new_status: TaskStatus = Field(description="New task status")
    new_position: Optional[int] = Field(default=None, description="New position in status column")
    comment: Optional[str] = Field(default=None, max_length=500, description="Move comment")


class ListTasksRequestDTO(FilterRequestDTO, TagsMixin):
    """DTO for listing tasks with filters."""
    
    project_id: Optional[int] = Field(default=None, description="Filter by project ID")
    status: Optional[TaskStatus] = Field(default=None, description="Filter by task status")
    priority: Optional[TaskPriority] = Field(default=None, description="Filter by priority")
    assignee_id: Optional[str] = Field(default=None, description="Filter by assignee")
    is_overdue: Optional[bool] = Field(default=None, description="Filter overdue tasks")
    has_time_entries: Optional[bool] = Field(default=None, description="Filter tasks with time entries")
    parent_task_id: Optional[int] = Field(default=None, description="Filter by parent task")
    is_subtask: Optional[bool] = Field(default=None, description="Filter subtasks only")


class SearchTasksRequestDTO(ListTasksRequestDTO):
    """DTO for searching tasks."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")


class TaskTimeRangeRequestDTO(RequestDTO):
    """DTO for task time-based reports."""
    
    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate that end date is after start date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v


# Response DTOs
class TaskResponseDTO(ResponseDTO, TimestampMixin, TagsMixin, NotesMixin):
    """DTO for task response."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    status: TaskStatus = Field(description="Task status")
    priority: TaskPriority = Field(description="Task priority")
    
    # Assignment
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    assignee_name: Optional[str] = Field(default=None, description="Assignee name")
    assignee_avatar: Optional[str] = Field(default=None, description="Assignee avatar URL")
    created_by_id: str = Field(description="Creator user ID")
    created_by_name: Optional[str] = Field(default=None, description="Creator name")
    
    # Timeline
    due_date: Optional[date] = Field(default=None, description="Task due date")
    estimated_hours: Optional[float] = Field(default=None, description="Estimated hours")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    
    # Organization
    parent_task_id: Optional[int] = Field(default=None, description="Parent task ID")
    parent_task_title: Optional[str] = Field(default=None, description="Parent task title")
    subtasks: List["TaskSummaryResponseDTO"] = Field(default_factory=list, description="Subtasks")
    depends_on_task_ids: List[int] = Field(default_factory=list, description="Task dependencies")
    blocked_by_task_ids: List[int] = Field(default_factory=list, description="Tasks blocking this one")
    
    # Attachments and comments
    attachments: List[TaskAttachmentResponseDTO] = Field(default_factory=list, description="Task attachments")
    comments: List[TaskCommentResponseDTO] = Field(default_factory=list, description="Task comments")
    
    # Statistics
    time_stats: Optional[TaskTimeStatsDTO] = Field(default=None, description="Time tracking statistics")
    
    # Computed fields
    is_overdue: bool = Field(description="Whether task is overdue")
    is_completed: bool = Field(description="Whether task is completed")
    is_blocked: bool = Field(description="Whether task is blocked by dependencies")
    can_start: bool = Field(description="Whether task can be started (no blocking dependencies)")
    days_until_due: Optional[int] = Field(default=None, description="Days until due date")
    progress_percentage: Optional[float] = Field(default=None, description="Task progress percentage")


class TaskSummaryResponseDTO(ResponseDTO):
    """DTO for task summary (used in lists and subtasks)."""
    
    project_id: int = Field(description="Project ID")
    title: str = Field(description="Task title")
    status: TaskStatus = Field(description="Task status")
    priority: TaskPriority = Field(description="Task priority")
    
    # Assignment
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    assignee_name: Optional[str] = Field(default=None, description="Assignee name")
    
    # Timeline
    due_date: Optional[date] = Field(default=None, description="Task due date")
    estimated_hours: Optional[float] = Field(default=None, description="Estimated hours")
    
    # Quick stats
    total_logged_hours: float = Field(description="Total hours logged")
    comment_count: int = Field(description="Number of comments")
    attachment_count: int = Field(description="Number of attachments")
    subtask_count: int = Field(description="Number of subtasks")
    
    # Status indicators
    is_overdue: bool = Field(description="Whether task is overdue")
    is_blocked: bool = Field(description="Whether task is blocked")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")


class TaskActivityResponseDTO(ResponseDTO):
    """DTO for task activity response."""
    
    date: datetime = Field(description="Activity date")
    activity_type: str = Field(description="Type of activity")
    description: str = Field(description="Activity description")
    user_id: str = Field(description="User who performed activity")
    user_name: Optional[str] = Field(default=None, description="User name")
    old_value: Optional[str] = Field(default=None, description="Previous value (for changes)")
    new_value: Optional[str] = Field(default=None, description="New value (for changes)")
    hours: Optional[float] = Field(default=None, description="Hours if time-related activity")


class TaskBoardResponseDTO(ResponseDTO):
    """DTO for task board/kanban view."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    
    columns: Dict[str, List[TaskSummaryResponseDTO]] = Field(
        description="Tasks organized by status columns"
    )
    
    stats: Dict[str, int] = Field(description="Task count by status")
    
    members: List[Dict[str, Any]] = Field(description="Project members for assignment")
    
    last_updated: datetime = Field(description="Last board update timestamp")


class TaskReportResponseDTO(ResponseDTO):
    """DTO for task reports."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    report_period_start: date = Field(description="Report period start")
    report_period_end: date = Field(description="Report period end")
    
    # Task summary
    total_tasks: int = Field(description="Total tasks in period")
    completed_tasks: int = Field(description="Completed tasks in period")
    overdue_tasks: int = Field(description="Overdue tasks")
    
    # Time summary
    total_hours: float = Field(description="Total hours logged on tasks")
    estimated_hours: float = Field(description="Total estimated hours")
    time_efficiency: float = Field(description="Time efficiency percentage")
    
    # Member breakdown
    member_stats: List[Dict[str, Any]] = Field(description="Statistics by team member")
    
    # Priority breakdown
    priority_breakdown: Dict[str, int] = Field(description="Task count by priority")
    
    # Status breakdown
    status_breakdown: Dict[str, int] = Field(description="Task count by status")
    
    # Daily breakdown
    daily_completion: List[Dict[str, Any]] = Field(description="Daily task completion")


# Bulk operation DTOs
class BulkUpdateTasksRequestDTO(RequestDTO):
    """DTO for bulk task updates."""
    
    task_ids: List[int] = Field(min_items=1, max_items=100, description="List of task IDs")
    status: Optional[TaskStatus] = Field(default=None, description="New status")
    priority: Optional[TaskPriority] = Field(default=None, description="New priority")
    assignee_id: Optional[str] = Field(default=None, description="New assignee")
    due_date: Optional[date] = Field(default=None, description="New due date")
    tags_to_add: Optional[List[str]] = Field(default=None, description="Tags to add")
    tags_to_remove: Optional[List[str]] = Field(default=None, description="Tags to remove")


class BulkMoveTasksRequestDTO(RequestDTO):
    """DTO for bulk moving tasks."""
    
    task_ids: List[int] = Field(min_items=1, max_items=50, description="List of task IDs")
    new_status: TaskStatus = Field(description="New status for all tasks")
    comment: Optional[str] = Field(default=None, max_length=500, description="Move comment")


# Analytics DTOs
class TaskAnalyticsResponseDTO(ResponseDTO):
    """DTO for task analytics."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    
    # Completion metrics
    completion_rate: float = Field(description="Task completion rate percentage")
    average_completion_time: Optional[float] = Field(default=None, description="Average completion time in hours")
    completion_trend: List[Dict[str, Any]] = Field(description="Completion trend over time")
    
    # Time metrics
    time_accuracy: float = Field(description="Time estimation accuracy percentage")
    productivity_score: float = Field(description="Team productivity score")
    
    # Assignment metrics
    workload_distribution: List[Dict[str, Any]] = Field(description="Workload distribution by member")
    assignment_balance: float = Field(description="Assignment balance score")
    
    # Priority metrics
    priority_distribution: Dict[str, int] = Field(description="Task distribution by priority")
    urgent_task_handling: float = Field(description="Urgent task handling efficiency")
    
    # Dependency metrics
    dependency_complexity: float = Field(description="Task dependency complexity score")
    blocking_frequency: float = Field(description="How often tasks are blocked")
    
    last_calculated: datetime = Field(description="When analytics were calculated")


# Dependency management DTOs
class TaskDependencyRequestDTO(RequestDTO):
    """DTO for creating task dependencies."""
    
    dependent_task_id: int = Field(description="Task that depends on another")
    depends_on_task_id: int = Field(description="Task that is depended upon")
    dependency_type: str = Field(default="finish_to_start", description="Type of dependency")


class TaskDependencyResponseDTO(ResponseDTO):
    """DTO for task dependency response."""
    
    dependent_task_id: int = Field(description="Dependent task ID")
    dependent_task_title: str = Field(description="Dependent task title")
    depends_on_task_id: int = Field(description="Dependency task ID")
    depends_on_task_title: str = Field(description="Dependency task title")
    dependency_type: str = Field(description="Type of dependency")
    is_blocking: bool = Field(description="Whether dependency is currently blocking")
    created_at: datetime = Field(description="Dependency creation timestamp")