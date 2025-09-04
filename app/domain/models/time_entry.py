"""
TimeEntry domain model.
Represents time tracking entries for tasks and projects.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any
from enum import Enum

from app.domain.models.base import (
    BaseEntity,
    TimeRange,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class TimeEntryStatus(str, Enum):
    """Time entry status."""
    RUNNING = "running"
    STOPPED = "stopped"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVOICED = "invoiced"


class TimeEntryType(str, Enum):
    """Time entry type."""
    MANUAL = "manual"
    TIMER = "timer"
    IMPORTED = "imported"
    AUTOMATIC = "automatic"


# Domain Events

class TimeEntryStartedEvent(DomainEvent):
    """Event raised when time tracking is started."""
    
    def __init__(self, entry_id: int, user_id: str, project_id: int, task_id: Optional[int]):
        super().__init__()
        self.entry_id = entry_id
        self.user_id = user_id
        self.project_id = project_id
        self.task_id = task_id
    
    @property
    def event_name(self) -> str:
        return "time_entry.started"


class TimeEntryStoppedEvent(DomainEvent):
    """Event raised when time tracking is stopped."""
    
    def __init__(self, entry_id: int, user_id: str, duration_hours: float):
        super().__init__()
        self.entry_id = entry_id
        self.user_id = user_id
        self.duration_hours = duration_hours
    
    @property
    def event_name(self) -> str:
        return "time_entry.stopped"


class TimeEntryApprovedEvent(DomainEvent):
    """Event raised when time entry is approved."""
    
    def __init__(self, entry_id: int, approved_by: str, approved_hours: float):
        super().__init__()
        self.entry_id = entry_id
        self.approved_by = approved_by
        self.approved_hours = approved_hours
    
    @property
    def event_name(self) -> str:
        return "time_entry.approved"


class TimeEntryInvoicedEvent(DomainEvent):
    """Event raised when time entry is included in an invoice."""
    
    def __init__(self, entry_id: int, invoice_id: int, billable_amount: float):
        super().__init__()
        self.entry_id = entry_id
        self.invoice_id = invoice_id
        self.billable_amount = billable_amount
    
    @property
    def event_name(self) -> str:
        return "time_entry.invoiced"


class TimeEntry(BaseEntity):
    """
    TimeEntry entity.
    Represents a time tracking entry for a task or project.
    """
    
    def __init__(
        self,
        user_id: str,
        project_id: int,
        task_id: Optional[int] = None,
        time_range: Optional[TimeRange] = None,
        duration_minutes: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Required fields
        self.user_id = user_id
        self.project_id = project_id
        
        # Optional task association
        self.task_id = task_id
        
        # Time tracking
        self.time_range = time_range
        self.duration_minutes = duration_minutes  # For manual entries
        
        # Entry details
        self.description = None
        self.entry_type = TimeEntryType.TIMER
        self.status = TimeEntryStatus.STOPPED
        
        # Billing information
        self.billable = True
        self.hourly_rate = None
        self.billable_amount = None
        
        # Date information
        self.date = date.today()
        
        # Approval workflow
        self.approved_by = None
        self.approved_at = None
        self.approved_duration = None  # Approved minutes
        self.rejection_reason = None
        
        # Invoice association
        self.invoice_id = None
        self.invoiced_at = None
        
        # Metadata
        self.tags = []
        self.notes = None
    
    def __post_init__(self):
        """Initialize time entry after creation."""
        super().__post_init__()
        
        # Set default time range if not provided
        if not self.time_range and self.entry_type == TimeEntryType.TIMER:
            # Create a stopped timer (start and end at current time)
            now = datetime.utcnow()
            self.time_range = TimeRange(start=now, end=now)
        
        # Validate on creation
        self.validate()
        
        # Calculate billable amount if not set
        if self.billable and self.hourly_rate and not self.billable_amount:
            self.billable_amount = self.calculate_billable_amount()
    
    def validate(self) -> None:
        """Validate time entry state."""
        # Required fields
        if not self.user_id:
            raise ValidationError("User ID is required", "user_id")
        
        if not self.project_id:
            raise ValidationError("Project ID is required", "project_id")
        
        # Validate duration
        if self.duration_minutes < 0:
            raise ValidationError("Duration cannot be negative", "duration_minutes")
        
        if self.duration_minutes > 24 * 60:  # 24 hours
            raise ValidationError("Duration cannot exceed 24 hours", "duration_minutes")
        
        # Validate time range for timer entries
        if self.entry_type == TimeEntryType.TIMER:
            if not self.time_range:
                raise ValidationError("Time range is required for timer entries", "time_range")
            
            # If stopped, calculate duration from time range
            if self.status == TimeEntryStatus.STOPPED and not self.time_range.is_open:
                calculated_minutes = self.time_range.duration_minutes or 0
                if self.duration_minutes == 0:
                    self.duration_minutes = calculated_minutes
        
        # Validate hourly rate
        if self.hourly_rate is not None and self.hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative", "hourly_rate")
        
        # Validate billable amount
        if self.billable_amount is not None and self.billable_amount < 0:
            raise ValidationError("Billable amount cannot be negative", "billable_amount")
        
        # Validate description length
        if self.description and len(self.description) > 1000:
            raise ValidationError("Description too long (max 1000 characters)", "description")
        
        # Validate notes length
        if self.notes and len(self.notes) > 2000:
            raise ValidationError("Notes too long (max 2000 characters)", "notes")
        
        # Validate tags
        if len(self.tags) > 10:
            raise ValidationError("Too many tags (max 10)", "tags")
        
        for tag in self.tags:
            if len(tag) > 50:
                raise ValidationError(f"Tag '{tag}' too long (max 50 characters)", "tags")
        
        # Business rules
        if self.status == TimeEntryStatus.APPROVED and not self.approved_by:
            raise ValidationError("Approved by is required for approved entries", "approved_by")
        
        if self.status == TimeEntryStatus.INVOICED and not self.invoice_id:
            raise ValidationError("Invoice ID is required for invoiced entries", "invoice_id")
        
        if self.approved_duration is not None and self.approved_duration < 0:
            raise ValidationError("Approved duration cannot be negative", "approved_duration")
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration_minutes / 60.0
    
    @property
    def effective_duration_minutes(self) -> int:
        """Get effective duration (approved if available, otherwise actual)."""
        return self.approved_duration or self.duration_minutes
    
    @property
    def effective_duration_hours(self) -> float:
        """Get effective duration in hours."""
        return self.effective_duration_minutes / 60.0
    
    @property
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self.status == TimeEntryStatus.RUNNING
    
    @property
    def is_billable(self) -> bool:
        """Check if entry is billable."""
        return self.billable and self.status not in [TimeEntryStatus.REJECTED]
    
    @property
    def is_invoiced(self) -> bool:
        """Check if entry has been invoiced."""
        return self.status == TimeEntryStatus.INVOICED
    
    @property
    def can_be_edited(self) -> bool:
        """Check if entry can be edited."""
        return self.status not in [TimeEntryStatus.INVOICED, TimeEntryStatus.APPROVED]
    
    @property
    def can_be_deleted(self) -> bool:
        """Check if entry can be deleted."""
        return self.status not in [TimeEntryStatus.INVOICED, TimeEntryStatus.RUNNING]
    
    def start_timer(self) -> None:
        """Start the timer."""
        if self.is_running:
            raise BusinessRuleViolation("Timer is already running")
        
        if self.is_invoiced:
            raise BusinessRuleViolation("Cannot start timer on invoiced entry")
        
        now = datetime.utcnow()
        self.time_range = TimeRange(start=now)
        self.status = TimeEntryStatus.RUNNING
        self.mark_as_updated()
        
        self.add_event(TimeEntryStartedEvent(
            entry_id=self.id or 0,
            user_id=self.user_id,
            project_id=self.project_id,
            task_id=self.task_id
        ))
    
    def stop_timer(self, end_time: Optional[datetime] = None) -> None:
        """Stop the timer."""
        if not self.is_running:
            raise BusinessRuleViolation("Timer is not running")
        
        if not self.time_range:
            raise BusinessRuleViolation("No active time range found")
        
        # Close the time range
        self.time_range = self.time_range.close(end_time)
        
        # Calculate duration
        self.duration_minutes = self.time_range.duration_minutes or 0
        
        # Update status
        self.status = TimeEntryStatus.STOPPED
        
        # Calculate billable amount
        if self.billable and self.hourly_rate:
            self.billable_amount = self.calculate_billable_amount()
        
        self.mark_as_updated()
        
        self.add_event(TimeEntryStoppedEvent(
            entry_id=self.id or 0,
            user_id=self.user_id,
            duration_hours=self.duration_hours
        ))
    
    def update_duration(self, minutes: int) -> None:
        """Update entry duration manually."""
        if not self.can_be_edited:
            raise BusinessRuleViolation("Cannot edit this time entry")
        
        if minutes < 0:
            raise ValidationError("Duration cannot be negative", "duration")
        
        if minutes > 24 * 60:  # 24 hours
            raise ValidationError("Duration cannot exceed 24 hours", "duration")
        
        self.duration_minutes = minutes
        
        # Recalculate billable amount
        if self.billable and self.hourly_rate:
            self.billable_amount = self.calculate_billable_amount()
        
        self.mark_as_updated()
    
    def update_info(
        self,
        description: Optional[str] = None,
        billable: Optional[bool] = None,
        hourly_rate: Optional[float] = None,
        notes: Optional[str] = None,
        date: Optional[date] = None
    ) -> None:
        """Update time entry information."""
        if not self.can_be_edited:
            raise BusinessRuleViolation("Cannot edit this time entry")
        
        if description is not None:
            self.description = description
        
        if billable is not None:
            self.billable = billable
        
        if hourly_rate is not None:
            self.hourly_rate = hourly_rate
        
        if notes is not None:
            self.notes = notes
        
        if date is not None:
            self.date = date
        
        # Recalculate billable amount if billing info changed
        if billable is not None or hourly_rate is not None:
            if self.billable and self.hourly_rate:
                self.billable_amount = self.calculate_billable_amount()
            else:
                self.billable_amount = None
        
        self.validate()
        self.mark_as_updated()
    
    def approve(self, approved_by: str, approved_minutes: Optional[int] = None) -> None:
        """Approve the time entry."""
        if self.status == TimeEntryStatus.APPROVED:
            raise BusinessRuleViolation("Time entry is already approved")
        
        if self.status == TimeEntryStatus.INVOICED:
            raise BusinessRuleViolation("Cannot approve invoiced time entry")
        
        if self.is_running:
            raise BusinessRuleViolation("Cannot approve running time entry")
        
        self.status = TimeEntryStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        self.approved_duration = approved_minutes or self.duration_minutes
        
        # Recalculate billable amount based on approved duration
        if self.billable and self.hourly_rate:
            approved_hours = self.approved_duration / 60.0
            self.billable_amount = approved_hours * self.hourly_rate
        
        self.mark_as_updated()
        
        self.add_event(TimeEntryApprovedEvent(
            entry_id=self.id or 0,
            approved_by=approved_by,
            approved_hours=self.effective_duration_hours
        ))
    
    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject the time entry."""
        if self.status == TimeEntryStatus.INVOICED:
            raise BusinessRuleViolation("Cannot reject invoiced time entry")
        
        if not reason.strip():
            raise ValidationError("Rejection reason is required", "reason")
        
        self.status = TimeEntryStatus.REJECTED
        self.rejection_reason = reason.strip()
        self.billable_amount = None  # No billing for rejected entries
        
        self.mark_as_updated()
    
    def mark_as_invoiced(self, invoice_id: int) -> None:
        """Mark entry as invoiced."""
        if self.status == TimeEntryStatus.INVOICED:
            raise BusinessRuleViolation("Time entry is already invoiced")
        
        if self.status == TimeEntryStatus.REJECTED:
            raise BusinessRuleViolation("Cannot invoice rejected time entry")
        
        if not self.is_billable:
            raise BusinessRuleViolation("Cannot invoice non-billable time entry")
        
        self.status = TimeEntryStatus.INVOICED
        self.invoice_id = invoice_id
        self.invoiced_at = datetime.utcnow()
        
        self.mark_as_updated()
        
        self.add_event(TimeEntryInvoicedEvent(
            entry_id=self.id or 0,
            invoice_id=invoice_id,
            billable_amount=self.billable_amount or 0
        ))
    
    def calculate_billable_amount(self) -> float:
        """Calculate billable amount based on duration and rate."""
        if not self.billable or not self.hourly_rate:
            return 0.0
        
        hours = self.effective_duration_hours
        return hours * self.hourly_rate
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the time entry."""
        if not tag:
            raise ValidationError("Tag cannot be empty", "tag")
        
        if len(tag) > 50:
            raise ValidationError("Tag too long (max 50 characters)", "tag")
        
        if tag not in self.tags:
            if len(self.tags) >= 10:
                raise BusinessRuleViolation("Cannot add more than 10 tags")
            
            self.tags.append(tag)
            self.mark_as_updated()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the time entry."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.mark_as_updated()
    
    def get_time_summary(self) -> Dict[str, Any]:
        """Get time summary information."""
        return {
            "duration_minutes": self.duration_minutes,
            "duration_hours": self.duration_hours,
            "effective_duration_minutes": self.effective_duration_minutes,
            "effective_duration_hours": self.effective_duration_hours,
            "billable": self.billable,
            "hourly_rate": self.hourly_rate,
            "billable_amount": self.billable_amount,
            "is_running": self.is_running,
            "is_invoiced": self.is_invoiced
        }
    
    def clone_for_date(self, new_date: date) -> 'TimeEntry':
        """Create a copy of this entry for a different date."""
        return TimeEntry(
            user_id=self.user_id,
            project_id=self.project_id,
            task_id=self.task_id,
            description=self.description,
            entry_type=TimeEntryType.MANUAL,
            billable=self.billable,
            hourly_rate=self.hourly_rate,
            date=new_date,
            tags=self.tags.copy(),
            notes=self.notes
        )
    
    @classmethod
    def create_manual_entry(
        cls,
        user_id: str,
        project_id: int,
        duration_minutes: int,
        description: Optional[str] = None,
        task_id: Optional[int] = None,
        billable: bool = True,
        hourly_rate: Optional[float] = None,
        date: Optional[date] = None
    ) -> 'TimeEntry':
        """Create a manual time entry."""
        return cls(
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            duration_minutes=duration_minutes,
            description=description,
            entry_type=TimeEntryType.MANUAL,
            status=TimeEntryStatus.STOPPED,
            billable=billable,
            hourly_rate=hourly_rate,
            date=date or date.today()
        )
    
    @classmethod
    def create_timer_entry(
        cls,
        user_id: str,
        project_id: int,
        task_id: Optional[int] = None,
        description: Optional[str] = None,
        hourly_rate: Optional[float] = None
    ) -> 'TimeEntry':
        """Create a timer-based time entry."""
        return cls(
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            description=description,
            entry_type=TimeEntryType.TIMER,
            status=TimeEntryStatus.STOPPED,
            hourly_rate=hourly_rate,
            date=date.today()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["entry_type"] = self.entry_type.value
        data["status"] = self.status.value
        
        # Convert date
        data["date"] = self.date.isoformat()
        
        # Convert time range
        if self.time_range:
            data["time_range"] = {
                "start": self.time_range.start.isoformat(),
                "end": self.time_range.end.isoformat() if self.time_range.end else None,
                "duration_hours": self.time_range.duration_hours,
                "is_open": self.time_range.is_open
            }
        
        # Convert optional datetime fields
        if self.approved_at:
            data["approved_at"] = self.approved_at.isoformat()
        if self.invoiced_at:
            data["invoiced_at"] = self.invoiced_at.isoformat()
        
        # Add computed properties
        data["duration_hours"] = self.duration_hours
        data["effective_duration_minutes"] = self.effective_duration_minutes
        data["effective_duration_hours"] = self.effective_duration_hours
        data["is_running"] = self.is_running
        data["is_billable"] = self.is_billable
        data["can_be_edited"] = self.can_be_edited
        data["time_summary"] = self.get_time_summary()
        
        return data