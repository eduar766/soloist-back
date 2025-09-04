"""
Domain events related to projects.
Events for project lifecycle and status changes.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base import DomainEvent


class ProjectCreated(DomainEvent):
    """Event fired when a new project is created."""
    
    def __init__(self,
                 project_id: int,
                 client_id: int,
                 user_id: str,
                 project_name: str,
                 project_type: Optional[str] = None,
                 budget: Optional[float] = None,
                 currency: str = "USD",
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id
        self.client_id = client_id
        self.user_id = user_id
        self.project_name = project_name
        self.project_type = project_type
        self.budget = budget
        self.currency = currency
        self.start_date = start_date
        self.end_date = end_date
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "budget": self.budget,
            "currency": self.currency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None
        }



class ProjectStatusChanged(DomainEvent):
    """Event fired when a project status changes."""
    
    project_id: int
    client_id: int
    user_id: str
    project_name: str
    old_status: str
    new_status: str
    status_reason: Optional[str] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "status_reason": self.status_reason
        }



class ProjectCompleted(DomainEvent):
    """Event fired when a project is completed."""
    
    project_id: int
    client_id: int
    user_id: str
    project_name: str
    completion_date: datetime
    total_hours: Optional[float] = None
    total_cost: Optional[float] = None
    currency: str = "USD"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "completion_date": self.completion_date.isoformat(),
            "total_hours": self.total_hours,
            "total_cost": self.total_cost,
            "currency": self.currency
        }



class ProjectMilestoneCompleted(DomainEvent):
    """Event fired when a project milestone is completed."""
    
    project_id: int
    client_id: int
    user_id: str
    project_name: str
    milestone_name: str
    milestone_description: Optional[str] = None
    completion_date: Optional[datetime] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "milestone_name": self.milestone_name,
            "milestone_description": self.milestone_description,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None
        }



class ProjectDeadlineApproaching(DomainEvent):
    """Event fired when a project deadline is approaching."""
    
    project_id: int
    client_id: int
    user_id: str
    project_name: str
    deadline: datetime
    days_remaining: int
    completion_percentage: Optional[float] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "deadline": self.deadline.isoformat(),
            "days_remaining": self.days_remaining,
            "completion_percentage": self.completion_percentage
        }



class ProjectBudgetExceeded(DomainEvent):
    """Event fired when project costs exceed the budget."""
    
    project_id: int
    client_id: int
    user_id: str
    project_name: str
    budget: float
    actual_cost: float
    currency: str
    overage_percentage: float
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "budget": self.budget,
            "actual_cost": self.actual_cost,
            "currency": self.currency,
            "overage_percentage": self.overage_percentage
        }