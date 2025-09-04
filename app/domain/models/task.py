"""
Task domain model.
Represents a task within a project with time tracking and status management.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict
from enum import Enum

from app.domain.models.base import (
    BaseEntity,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent,
    TimeRange
)


class TaskStatus(str, Enum):
    """Task status for Kanban-style workflow."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Task types."""
    FEATURE = "feature"
    BUG = "bug"
    ENHANCEMENT = "enhancement"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    RESEARCH = "research"
    MEETING = "meeting"
    OTHER = "other"


# Domain Events

class TaskCreatedEvent(DomainEvent):
    """Event raised when a new task is created."""
    
    def __init__(self, task_id: int, title: str, project_id: int, assigned_to: Optional[str]):
        super().__init__()
        self.task_id = task_id
        self.title = title
        self.project_id = project_id
        self.assigned_to = assigned_to
    
    @property
    def event_name(self) -> str:
        return "task.created"


class TaskStatusChangedEvent(DomainEvent):
    """Event raised when task status changes."""
    
    def __init__(self, task_id: int, old_status: TaskStatus, new_status: TaskStatus, changed_by: str):
        super().__init__()
        self.task_id = task_id
        self.old_status = old_status
        self.new_status = new_status
        self.changed_by = changed_by
    
    @property
    def event_name(self) -> str:
        return "task.status.changed"


class TaskAssignedEvent(DomainEvent):
    """Event raised when task is assigned to a user."""
    
    def __init__(self, task_id: int, assigned_to: str, assigned_by: str):
        super().__init__()
        self.task_id = task_id
        self.assigned_to = assigned_to
        self.assigned_by = assigned_by
    
    @property
    def event_name(self) -> str:
        return "task.assigned"


class TaskCompletedEvent(DomainEvent):
    """Event raised when task is completed."""
    
    def __init__(self, task_id: int, completed_by: str, total_time_spent: float):
        super().__init__()
        self.task_id = task_id
        self.completed_by = completed_by
        self.total_time_spent = total_time_spent
    
    @property
    def event_name(self) -> str:
        return "task.completed"


@dataclass
class TaskComment:
    """Task comment."""
    
    author_id: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "author_id": self.author_id,
            "content": self.content,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class TaskAttachment:
    """Task attachment."""
    
    filename: str
    file_url: str
    file_size: int
    content_type: str
    uploaded_by: str
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat()
        }


@dataclass
class Task(BaseEntity):
    """
    Task entity.
    Represents a task within a project with time tracking and status management.
    """
    
    # Required fields
    project_id: int
    title: str
    created_by: str
    
    # Task details
    description: Optional[str] = None
    task_type: TaskType = TaskType.OTHER
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Assignment
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # Dates and time
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    
    # Estimation and tracking
    estimated_hours: Optional[float] = None
    actual_hours: float = 0
    billable: bool = True
    
    # Organization
    tags: List[str] = field(default_factory=list)
    board_position: int = 0  # For Kanban ordering
    
    # Relationships
    parent_task_id: Optional[int] = None
    subtasks: List[int] = field(default_factory=list)
    
    # Collaboration
    comments: List[TaskComment] = field(default_factory=list)
    attachments: List[TaskAttachment] = field(default_factory=list)
    watchers: List[str] = field(default_factory=list)  # User IDs watching this task
    
    # Status tracking
    status_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize task after creation."""
        super().__post_init__()
        
        # Validate on creation
        self.validate()
        
        # Add creator as watcher
        if self.created_by not in self.watchers:
            self.watchers.append(self.created_by)
        
        # Add creation event if new
        if self.is_new:
            self.add_event(TaskCreatedEvent(
                task_id=self.id or 0,
                title=self.title,
                project_id=self.project_id,
                assigned_to=self.assigned_to
            ))
    
    def validate(self) -> None:
        """Validate task state."""
        # Required fields
        if not self.project_id:
            raise ValidationError("Project ID is required", "project_id")
        
        if not self.title:
            raise ValidationError("Task title is required", "title")
        
        if len(self.title) > 255:
            raise ValidationError("Task title too long (max 255 characters)", "title")
        
        if not self.created_by:
            raise ValidationError("Created by is required", "created_by")
        
        # Validate description length
        if self.description and len(self.description) > 5000:
            raise ValidationError("Description too long (max 5000 characters)", "description")
        
        # Validate estimated hours
        if self.estimated_hours is not None and self.estimated_hours < 0:
            raise ValidationError("Estimated hours cannot be negative", "estimated_hours")
        
        if self.estimated_hours is not None and self.estimated_hours > 1000:
            raise ValidationError("Estimated hours too high (max 1000 hours)", "estimated_hours")
        
        # Validate actual hours
        if self.actual_hours < 0:
            raise ValidationError("Actual hours cannot be negative", "actual_hours")
        
        # Validate dates
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError("Due date cannot be before start date", "due_date")
        
        # Validate tags
        if len(self.tags) > 20:
            raise ValidationError("Too many tags (max 20)", "tags")
        
        for tag in self.tags:
            if len(tag) > 50:
                raise ValidationError(f"Tag '{tag}' too long (max 50 characters)", "tags")
        
        # Validate board position
        if self.board_position < 0:
            raise ValidationError("Board position cannot be negative", "board_position")
        
        # Business rule: completed tasks must have completed_at timestamp
        if self.status == TaskStatus.DONE and not self.completed_at:
            self.completed_at = datetime.utcnow()
        
        # Business rule: if assigned, must have assigned_at timestamp
        if self.assigned_to and not self.assigned_at:
            self.assigned_at = datetime.utcnow()
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.DONE
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.is_completed:
            return False
        return date.today() > self.due_date
    
    @property
    def is_assigned(self) -> bool:
        """Check if task is assigned to someone."""
        return self.assigned_to is not None
    
    @property
    def has_subtasks(self) -> bool:
        """Check if task has subtasks."""
        return len(self.subtasks) > 0
    
    @property
    def is_subtask(self) -> bool:
        """Check if this is a subtask."""
        return self.parent_task_id is not None
    
    @property
    def completion_percentage(self) -> float:
        """Get task completion percentage based on time spent vs estimated."""
        if not self.estimated_hours or self.estimated_hours == 0:
            return 100.0 if self.is_completed else 0.0
        
        percentage = (self.actual_hours / self.estimated_hours) * 100
        return min(100.0, percentage)
    
    @property
    def time_remaining(self) -> Optional[float]:
        """Get estimated time remaining."""
        if not self.estimated_hours:
            return None
        return max(0, self.estimated_hours - self.actual_hours)
    
    @property
    def is_over_estimate(self) -> bool:
        """Check if task is over time estimate."""
        if not self.estimated_hours:
            return False
        return self.actual_hours > self.estimated_hours
    
    def change_status(self, new_status: TaskStatus, changed_by: str, note: Optional[str] = None) -> None:
        """Change task status."""
        if self.status == new_status:
            raise BusinessRuleViolation(f"Task is already {new_status.value}")
        
        # Business rules for status changes
        if self.status == TaskStatus.CANCELLED:
            raise BusinessRuleViolation("Cannot change status of cancelled task")
        
        # Record status change in history
        status_change = {
            "from_status": self.status.value,
            "to_status": new_status.value,
            "changed_by": changed_by,
            "changed_at": datetime.utcnow().isoformat(),
            "note": note
        }
        self.status_history.append(status_change)
        
        old_status = self.status
        self.status = new_status
        
        # Set timestamps based on status
        if new_status == TaskStatus.DONE:
            self.completed_at = datetime.utcnow()
            self.add_event(TaskCompletedEvent(
                task_id=self.id or 0,
                completed_by=changed_by,
                total_time_spent=self.actual_hours
            ))
        elif old_status == TaskStatus.DONE and new_status != TaskStatus.DONE:
            # Reopening a completed task
            self.completed_at = None
        
        self.mark_as_updated()
        self.add_event(TaskStatusChangedEvent(self.id or 0, old_status, new_status, changed_by))
    
    def assign_to(self, user_id: str, assigned_by: str) -> None:
        """Assign task to a user."""
        if self.assigned_to == user_id:
            raise BusinessRuleViolation(f"Task is already assigned to {user_id}")
        
        self.assigned_to = user_id
        self.assigned_at = datetime.utcnow()
        
        # Add assignee as watcher
        if user_id not in self.watchers:
            self.watchers.append(user_id)
        
        self.mark_as_updated()
        self.add_event(TaskAssignedEvent(self.id or 0, user_id, assigned_by))
    
    def unassign(self) -> None:
        """Remove assignment from task."""
        if not self.assigned_to:
            raise BusinessRuleViolation("Task is not assigned to anyone")
        
        self.assigned_to = None
        self.assigned_at = None
        self.mark_as_updated()
    
    def update_info(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        due_date: Optional[date] = None,
        estimated_hours: Optional[float] = None
    ) -> None:
        """Update task information."""
        if title is not None:
            self.title = title
        
        if description is not None:
            self.description = description
        
        if task_type is not None:
            self.task_type = task_type
        
        if priority is not None:
            self.priority = priority
        
        if due_date is not None:
            self.due_date = due_date
        
        if estimated_hours is not None:
            self.estimated_hours = estimated_hours
        
        self.validate()
        self.mark_as_updated()
    
    def add_time(self, hours: float) -> None:
        """Add time spent on task."""
        if hours < 0:
            raise ValidationError("Hours cannot be negative", "hours")
        
        if hours > 24:
            raise ValidationError("Cannot add more than 24 hours at once", "hours")
        
        self.actual_hours += hours
        self.mark_as_updated()
    
    def set_time(self, hours: float) -> None:
        """Set total time spent on task."""
        if hours < 0:
            raise ValidationError("Hours cannot be negative", "hours")
        
        self.actual_hours = hours
        self.mark_as_updated()
    
    def add_comment(self, author_id: str, content: str) -> None:
        """Add a comment to the task."""
        if not content.strip():
            raise ValidationError("Comment content cannot be empty", "content")
        
        if len(content) > 2000:
            raise ValidationError("Comment too long (max 2000 characters)", "content")
        
        comment = TaskComment(author_id=author_id, content=content.strip())
        self.comments.append(comment)
        
        # Add commenter as watcher
        if author_id not in self.watchers:
            self.watchers.append(author_id)
        
        self.mark_as_updated()
    
    def add_attachment(
        self,
        filename: str,
        file_url: str,
        file_size: int,
        content_type: str,
        uploaded_by: str
    ) -> None:
        """Add an attachment to the task."""
        if not filename:
            raise ValidationError("Filename is required", "filename")
        
        if not file_url:
            raise ValidationError("File URL is required", "file_url")
        
        if file_size < 0:
            raise ValidationError("File size cannot be negative", "file_size")
        
        # Limit file size to 50MB
        max_size = 50 * 1024 * 1024
        if file_size > max_size:
            raise ValidationError(f"File too large (max {max_size} bytes)", "file_size")
        
        attachment = TaskAttachment(
            filename=filename,
            file_url=file_url,
            file_size=file_size,
            content_type=content_type,
            uploaded_by=uploaded_by
        )
        
        self.attachments.append(attachment)
        
        # Add uploader as watcher
        if uploaded_by not in self.watchers:
            self.watchers.append(uploaded_by)
        
        self.mark_as_updated()
    
    def add_watcher(self, user_id: str) -> None:
        """Add a user to watch this task."""
        if user_id not in self.watchers:
            self.watchers.append(user_id)
            self.mark_as_updated()
    
    def remove_watcher(self, user_id: str) -> None:
        """Remove a user from watching this task."""
        if user_id in self.watchers:
            self.watchers.remove(user_id)
            self.mark_as_updated()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task."""
        if not tag:
            raise ValidationError("Tag cannot be empty", "tag")
        
        if len(tag) > 50:
            raise ValidationError("Tag too long (max 50 characters)", "tag")
        
        if tag not in self.tags:
            if len(self.tags) >= 20:
                raise BusinessRuleViolation("Cannot add more than 20 tags")
            
            self.tags.append(tag)
            self.mark_as_updated()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.mark_as_updated()
    
    def update_board_position(self, new_position: int) -> None:
        """Update task position on the kanban board."""
        if new_position < 0:
            raise ValidationError("Board position cannot be negative", "board_position")
        
        self.board_position = new_position
        self.mark_as_updated()
    
    def add_subtask(self, subtask_id: int) -> None:
        """Add a subtask to this task."""
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)
            self.mark_as_updated()
    
    def remove_subtask(self, subtask_id: int) -> None:
        """Remove a subtask from this task."""
        if subtask_id in self.subtasks:
            self.subtasks.remove(subtask_id)
            self.mark_as_updated()
    
    def can_be_completed(self) -> bool:
        """Check if task can be marked as completed."""
        # Add any business rules for completion
        # For example, all subtasks must be completed
        return True  # Simplified for now
    
    def get_time_breakdown(self) -> Dict[str, float]:
        """Get time breakdown for the task."""
        return {
            "estimated_hours": self.estimated_hours or 0,
            "actual_hours": self.actual_hours,
            "remaining_hours": self.time_remaining or 0,
            "completion_percentage": self.completion_percentage,
            "is_over_estimate": self.is_over_estimate
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["task_type"] = self.task_type.value
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        
        # Convert dates
        if self.due_date:
            data["due_date"] = self.due_date.isoformat()
        if self.start_date:
            data["start_date"] = self.start_date.isoformat()
        if self.assigned_at:
            data["assigned_at"] = self.assigned_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        
        # Convert nested objects
        data["comments"] = [comment.to_dict() for comment in self.comments]
        data["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        
        # Add computed properties
        data["is_completed"] = self.is_completed
        data["is_overdue"] = self.is_overdue
        data["is_assigned"] = self.is_assigned
        data["completion_percentage"] = self.completion_percentage
        data["time_breakdown"] = self.get_time_breakdown()
        
        return data