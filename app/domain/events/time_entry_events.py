"""
Domain events related to time tracking.
Events for time entries and reporting.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, date

from .base import DomainEvent



class TimeEntryCreated(DomainEvent):
    """Event fired when a new time entry is created."""
    
    time_entry_id: int
    user_id: str
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    duration_minutes: int = 0
    description: Optional[str] = None
    entry_date: Optional[date] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "time_entry_id": self.time_entry_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "duration_minutes": self.duration_minutes,
            "description": self.description,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None
        }



class WeeklyTimeReport(DomainEvent):
    """Event fired for weekly time tracking reports."""
    
    user_id: str
    week_start: date
    week_end: date
    total_hours: float
    billable_hours: float
    projects_worked: List[Dict[str, Any]]
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "total_hours": self.total_hours,
            "billable_hours": self.billable_hours,
            "projects_worked": self.projects_worked
        }



class MonthlyTimeReport(DomainEvent):
    """Event fired for monthly time tracking reports."""
    
    user_id: str
    month_start: date
    month_end: date
    total_hours: float
    billable_hours: float
    total_earnings: Optional[float] = None
    currency: str = "USD"
    projects_summary: Optional[List[Dict[str, Any]]] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "month_start": self.month_start.isoformat(),
            "month_end": self.month_end.isoformat(),
            "total_hours": self.total_hours,
            "billable_hours": self.billable_hours,
            "total_earnings": self.total_earnings,
            "currency": self.currency,
            "projects_summary": self.projects_summary
        }



class TimeEntryApproved(DomainEvent):
    """Event fired when a time entry is approved by client."""
    
    time_entry_id: int
    user_id: str
    client_id: int
    project_id: int
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "time_entry_id": self.time_entry_id,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None
        }



class LongTimeEntryDetected(DomainEvent):
    """Event fired when unusually long time entries are detected."""
    
    time_entry_id: int
    user_id: str
    project_id: Optional[int] = None
    duration_hours: float = 0
    threshold_hours: float = 8
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "time_entry_id": self.time_entry_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "duration_hours": self.duration_hours,
            "threshold_hours": self.threshold_hours
        }