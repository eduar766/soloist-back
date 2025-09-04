"""
Time Entry DTOs for the application layer.
Data Transfer Objects for time tracking operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from pydantic import Field, validator
from enum import Enum

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin, TagsMixin, NotesMixin
)


class TimeEntryStatus(str, Enum):
    """Time entry status options."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVOICED = "invoiced"


class TimeEntryType(str, Enum):
    """Time entry type options."""
    REGULAR = "regular"
    OVERTIME = "overtime"
    BREAK = "break"
    MEETING = "meeting"
    ADMIN = "admin"


# Request DTOs
class StartTimerRequestDTO(RequestDTO):
    """DTO for starting a timer."""
    
    project_id: int = Field(description="Project ID")
    task_id: Optional[int] = Field(default=None, description="Task ID (optional)")
    description: Optional[str] = Field(default=None, max_length=500, description="Work description")
    tags: List[str] = Field(default_factory=list, max_items=10, description="Time entry tags")
    
    @validator('description')
    def validate_description(cls, v):
        """Validate description is provided."""
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class StopTimerRequestDTO(RequestDTO):
    """DTO for stopping a timer."""
    
    description: Optional[str] = Field(default=None, max_length=500, description="Final work description")
    tags: Optional[List[str]] = Field(default=None, max_items=10, description="Time entry tags")
    is_billable: bool = Field(default=True, description="Whether time is billable")


class CreateTimeEntryRequestDTO(CreateRequestDTO, TagsMixin, NotesMixin):
    """DTO for manual time entry creation."""
    
    project_id: int = Field(description="Project ID")
    task_id: Optional[int] = Field(default=None, description="Task ID (optional)")
    description: str = Field(min_length=1, max_length=500, description="Work description")
    
    # Time tracking
    start_time: datetime = Field(description="Start timestamp")
    end_time: Optional[datetime] = Field(default=None, description="End timestamp (if finished)")
    duration_minutes: Optional[int] = Field(default=None, ge=1, description="Duration in minutes")
    
    # Classification
    entry_type: TimeEntryType = Field(default=TimeEntryType.REGULAR, description="Entry type")
    is_billable: bool = Field(default=True, description="Whether time is billable")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Override hourly rate")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate end time is after start time."""
        if v and values.get('start_time') and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v
    
    @validator('duration_minutes')
    def validate_duration_consistency(cls, v, values):
        """Validate duration consistency with start/end times."""
        if v and values.get('start_time') and values.get('end_time'):
            calculated_minutes = int((values['end_time'] - values['start_time']).total_seconds() / 60)
            if abs(calculated_minutes - v) > 1:  # Allow 1 minute tolerance
                raise ValueError('Duration must match start/end time difference')
        return v


class UpdateTimeEntryRequestDTO(UpdateRequestDTO, TagsMixin, NotesMixin):
    """DTO for time entry update requests."""
    
    description: Optional[str] = Field(default=None, min_length=1, max_length=500, description="Work description")
    
    # Time tracking
    start_time: Optional[datetime] = Field(default=None, description="Start timestamp")
    end_time: Optional[datetime] = Field(default=None, description="End timestamp")
    duration_minutes: Optional[int] = Field(default=None, ge=1, description="Duration in minutes")
    
    # Classification
    entry_type: Optional[TimeEntryType] = Field(default=None, description="Entry type")
    is_billable: Optional[bool] = Field(default=None, description="Whether time is billable")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Override hourly rate")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate end time is after start time."""
        if v and values.get('start_time') and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class SubmitTimeEntryRequestDTO(RequestDTO):
    """DTO for submitting time entries for approval."""
    
    entry_ids: List[int] = Field(min_items=1, max_items=50, description="Time entry IDs to submit")
    comment: Optional[str] = Field(default=None, max_length=500, description="Submission comment")


class ApproveTimeEntryRequestDTO(RequestDTO):
    """DTO for approving time entries."""
    
    entry_ids: List[int] = Field(min_items=1, max_items=50, description="Time entry IDs to approve")
    comment: Optional[str] = Field(default=None, max_length=500, description="Approval comment")


class RejectTimeEntryRequestDTO(RequestDTO):
    """DTO for rejecting time entries."""
    
    entry_ids: List[int] = Field(min_items=1, max_items=50, description="Time entry IDs to reject")
    reason: str = Field(min_length=1, max_length=500, description="Rejection reason")


class ListTimeEntriesRequestDTO(FilterRequestDTO, TagsMixin):
    """DTO for listing time entries with filters."""
    
    project_id: Optional[int] = Field(default=None, description="Filter by project ID")
    task_id: Optional[int] = Field(default=None, description="Filter by task ID")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    client_id: Optional[int] = Field(default=None, description="Filter by client ID")
    status: Optional[TimeEntryStatus] = Field(default=None, description="Filter by status")
    entry_type: Optional[TimeEntryType] = Field(default=None, description="Filter by entry type")
    is_billable: Optional[bool] = Field(default=None, description="Filter by billable status")
    is_running: Optional[bool] = Field(default=None, description="Filter running timers")
    
    # Time range filters
    worked_date_from: Optional[date] = Field(default=None, description="Filter entries from date")
    worked_date_to: Optional[date] = Field(default=None, description="Filter entries to date")
    
    @validator('worked_date_to')
    def validate_worked_date_range(cls, v, values):
        """Validate date range."""
        if v and values.get('worked_date_from') and v < values['worked_date_from']:
            raise ValueError('worked_date_to must be after worked_date_from')
        return v


class SearchTimeEntriesRequestDTO(ListTimeEntriesRequestDTO):
    """DTO for searching time entries."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")


class TimeEntryReportRequestDTO(RequestDTO):
    """DTO for time entry reports."""
    
    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    project_ids: Optional[List[int]] = Field(default=None, description="Filter by project IDs")
    user_ids: Optional[List[str]] = Field(default=None, description="Filter by user IDs")
    client_ids: Optional[List[int]] = Field(default=None, description="Filter by client IDs")
    include_non_billable: bool = Field(default=True, description="Include non-billable time")
    group_by: str = Field(default="date", description="Group results by: date, project, user, client")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate that end date is after start date."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('group_by')
    def validate_group_by(cls, v):
        """Validate group_by options."""
        valid_options = ["date", "project", "user", "client", "task"]
        if v not in valid_options:
            raise ValueError(f'group_by must be one of: {", ".join(valid_options)}')
        return v


# Response DTOs
class RunningTimerResponseDTO(ResponseDTO):
    """DTO for currently running timer."""
    
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    client_name: str = Field(description="Client name")
    task_id: Optional[int] = Field(default=None, description="Task ID")
    task_title: Optional[str] = Field(default=None, description="Task title")
    description: Optional[str] = Field(default=None, description="Work description")
    start_time: datetime = Field(description="Timer start time")
    elapsed_minutes: int = Field(description="Minutes elapsed")
    tags: List[str] = Field(description="Time entry tags")


class TimeEntryResponseDTO(ResponseDTO, TimestampMixin, TagsMixin, NotesMixin):
    """DTO for time entry response."""
    
    user_id: str = Field(description="User ID")
    user_name: Optional[str] = Field(default=None, description="User name")
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    task_id: Optional[int] = Field(default=None, description="Task ID")
    task_title: Optional[str] = Field(default=None, description="Task title")
    
    # Content
    description: str = Field(description="Work description")
    
    # Time tracking
    start_time: datetime = Field(description="Start timestamp")
    end_time: Optional[datetime] = Field(default=None, description="End timestamp")
    duration_minutes: int = Field(description="Duration in minutes")
    worked_date: date = Field(description="Date when work was performed")
    
    # Classification
    entry_type: TimeEntryType = Field(description="Entry type")
    status: TimeEntryStatus = Field(description="Entry status")
    is_billable: bool = Field(description="Whether time is billable")
    hourly_rate: Optional[float] = Field(default=None, description="Hourly rate used")
    calculated_amount: Optional[float] = Field(default=None, description="Calculated amount")
    
    # Approval workflow
    submitted_at: Optional[datetime] = Field(default=None, description="Submission timestamp")
    approved_at: Optional[datetime] = Field(default=None, description="Approval timestamp")
    approved_by_id: Optional[str] = Field(default=None, description="Approver user ID")
    approved_by_name: Optional[str] = Field(default=None, description="Approver name")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason")
    
    # Invoice tracking
    invoice_id: Optional[int] = Field(default=None, description="Related invoice ID")
    invoiced_at: Optional[datetime] = Field(default=None, description="Invoice timestamp")
    
    # Computed fields
    is_running: bool = Field(description="Whether timer is still running")
    duration_display: str = Field(description="Human-readable duration")
    can_edit: bool = Field(description="Whether entry can be edited")
    can_delete: bool = Field(description="Whether entry can be deleted")


class TimeEntrySummaryResponseDTO(ResponseDTO):
    """DTO for time entry summary (used in lists)."""
    
    user_id: str = Field(description="User ID")
    user_name: Optional[str] = Field(default=None, description="User name")
    project_name: str = Field(description="Project name")
    client_name: str = Field(description="Client name")
    task_title: Optional[str] = Field(default=None, description="Task title")
    description: str = Field(description="Work description")
    worked_date: date = Field(description="Work date")
    duration_minutes: int = Field(description="Duration in minutes")
    duration_display: str = Field(description="Human-readable duration")
    entry_type: TimeEntryType = Field(description="Entry type")
    status: TimeEntryStatus = Field(description="Entry status")
    is_billable: bool = Field(description="Whether time is billable")
    calculated_amount: Optional[float] = Field(default=None, description="Calculated amount")
    is_running: bool = Field(description="Whether timer is still running")


class TimeEntryStatsResponseDTO(ResponseDTO):
    """DTO for time entry statistics."""
    
    total_entries: int = Field(description="Total number of entries")
    total_hours: float = Field(description="Total hours logged")
    billable_hours: float = Field(description="Total billable hours")
    non_billable_hours: float = Field(description="Total non-billable hours")
    
    # Status breakdown
    draft_entries: int = Field(description="Draft entries count")
    submitted_entries: int = Field(description="Submitted entries count")
    approved_entries: int = Field(description="Approved entries count")
    rejected_entries: int = Field(description="Rejected entries count")
    invoiced_entries: int = Field(description="Invoiced entries count")
    
    # Financial
    total_amount: float = Field(description="Total calculated amount")
    average_hourly_rate: Optional[float] = Field(default=None, description="Average hourly rate")
    
    # Time patterns
    most_productive_hours: List[int] = Field(description="Most productive hours of day")
    average_session_length: float = Field(description="Average session length in hours")
    
    period_start: date = Field(description="Statistics period start")
    period_end: date = Field(description="Statistics period end")


class TimeEntryReportResponseDTO(ResponseDTO):
    """DTO for time entry reports."""
    
    report_title: str = Field(description="Report title")
    report_period_start: date = Field(description="Report period start")
    report_period_end: date = Field(description="Report period end")
    generated_at: datetime = Field(description="Report generation time")
    
    # Summary
    total_hours: float = Field(description="Total hours in report")
    billable_hours: float = Field(description="Billable hours in report")
    non_billable_hours: float = Field(description="Non-billable hours in report")
    total_amount: float = Field(description="Total amount in report")
    
    # Grouped data
    grouped_data: List[Dict[str, Any]] = Field(description="Report data grouped by selected criteria")
    
    # Filters applied
    filters: Dict[str, Any] = Field(description="Filters applied to report")
    
    # Metadata
    entry_count: int = Field(description="Number of entries in report")
    unique_projects: int = Field(description="Number of unique projects")
    unique_users: int = Field(description="Number of unique users")


class DailyTimeStatsDTO(ResponseDTO):
    """DTO for daily time statistics."""
    
    date: date = Field(description="Date")
    total_hours: float = Field(description="Total hours for day")
    billable_hours: float = Field(description="Billable hours for day")
    non_billable_hours: float = Field(description="Non-billable hours for day")
    entry_count: int = Field(description="Number of entries for day")
    projects_worked: List[str] = Field(description="Projects worked on")
    running_timer: Optional[RunningTimerResponseDTO] = Field(default=None, description="Running timer if any")


# Bulk operation DTOs
class BulkUpdateTimeEntriesRequestDTO(RequestDTO):
    """DTO for bulk time entry updates."""
    
    entry_ids: List[int] = Field(min_items=1, max_items=100, description="Time entry IDs")
    is_billable: Optional[bool] = Field(default=None, description="New billable status")
    entry_type: Optional[TimeEntryType] = Field(default=None, description="New entry type")
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="New hourly rate")
    tags_to_add: Optional[List[str]] = Field(default=None, description="Tags to add")
    tags_to_remove: Optional[List[str]] = Field(default=None, description="Tags to remove")


class BulkDeleteTimeEntriesRequestDTO(RequestDTO):
    """DTO for bulk time entry deletion."""
    
    entry_ids: List[int] = Field(min_items=1, max_items=100, description="Time entry IDs to delete")
    reason: Optional[str] = Field(default=None, max_length=500, description="Deletion reason")


# Analytics DTOs
class TimeTrackingAnalyticsResponseDTO(ResponseDTO):
    """DTO for time tracking analytics."""
    
    user_id: Optional[str] = Field(default=None, description="User ID (if user-specific)")
    project_id: Optional[int] = Field(default=None, description="Project ID (if project-specific)")
    
    # Productivity metrics
    productivity_score: float = Field(description="Productivity score (0-100)")
    focus_score: float = Field(description="Focus score based on session lengths")
    consistency_score: float = Field(description="Consistency score")
    
    # Time patterns
    peak_productivity_hours: List[Dict[str, Any]] = Field(description="Peak productivity hours")
    work_pattern: Dict[str, Any] = Field(description="Work pattern analysis")
    
    # Efficiency metrics
    time_estimation_accuracy: float = Field(description="Time estimation accuracy percentage")
    project_switching_frequency: float = Field(description="How often switching between projects")
    
    # Trends
    productivity_trend: List[Dict[str, Any]] = Field(description="Productivity trend over time")
    hours_trend: List[Dict[str, Any]] = Field(description="Hours logged trend over time")
    
    analysis_period_start: date = Field(description="Analysis period start")
    analysis_period_end: date = Field(description="Analysis period end")
    last_calculated: datetime = Field(description="When analytics were calculated")


# Export DTOs
class ExportTimeEntriesRequestDTO(RequestDTO):
    """DTO for exporting time entries."""
    
    format: str = Field(description="Export format: csv, xlsx, pdf")
    start_date: date = Field(description="Export start date")
    end_date: date = Field(description="Export end date")
    project_ids: Optional[List[int]] = Field(default=None, description="Filter by project IDs")
    user_ids: Optional[List[str]] = Field(default=None, description="Filter by user IDs")
    include_non_billable: bool = Field(default=True, description="Include non-billable time")
    include_details: bool = Field(default=True, description="Include detailed information")
    group_by_project: bool = Field(default=False, description="Group entries by project")
    
    @validator('format')
    def validate_format(cls, v):
        """Validate export format."""
        valid_formats = ["csv", "xlsx", "pdf"]
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {", ".join(valid_formats)}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v