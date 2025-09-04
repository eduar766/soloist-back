"""
Project domain model.
Represents a project for a client with team members, tasks and billing configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict
from enum import Enum
from decimal import Decimal

from app.domain.models.base import (
    AggregateRoot,
    Money,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class ProjectStatus(str, Enum):
    """Project status."""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ProjectType(str, Enum):
    """Project type."""
    FIXED_PRICE = "fixed_price"
    HOURLY = "hourly"
    RETAINER = "retainer"
    MILESTONE = "milestone"


class ProjectRole(str, Enum):
    """User role within a project."""
    OWNER = "owner"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class BillingType(str, Enum):
    """Billing type for project."""
    HOURLY = "hourly"
    FIXED = "fixed"
    MILESTONE = "milestone"
    RETAINER = "retainer"


# Domain Events

class ProjectCreatedEvent(DomainEvent):
    """Event raised when a new project is created."""
    
    def __init__(self, project_id: int, name: str, client_id: int, owner_id: str):
        super().__init__()
        self.project_id = project_id
        self.name = name
        self.client_id = client_id
        self.owner_id = owner_id
    
    @property
    def event_name(self) -> str:
        return "project.created"


class ProjectStatusChangedEvent(DomainEvent):
    """Event raised when project status changes."""
    
    def __init__(self, project_id: int, old_status: ProjectStatus, new_status: ProjectStatus):
        super().__init__()
        self.project_id = project_id
        self.old_status = old_status
        self.new_status = new_status
    
    @property
    def event_name(self) -> str:
        return "project.status.changed"


class ProjectMemberAddedEvent(DomainEvent):
    """Event raised when a member is added to a project."""
    
    def __init__(self, project_id: int, user_id: str, role: ProjectRole):
        super().__init__()
        self.project_id = project_id
        self.user_id = user_id
        self.role = role
    
    @property
    def event_name(self) -> str:
        return "project.member.added"


class ProjectCompletedEvent(DomainEvent):
    """Event raised when a project is completed."""
    
    def __init__(self, project_id: int, completion_date: datetime, final_budget_used: float):
        super().__init__()
        self.project_id = project_id
        self.completion_date = completion_date
        self.final_budget_used = final_budget_used
    
    @property
    def event_name(self) -> str:
        return "project.completed"


@dataclass
class ProjectMember:
    """Project team member."""
    
    user_id: str
    role: ProjectRole
    hourly_rate: Optional[float] = None
    added_at: datetime = field(default_factory=datetime.utcnow)
    added_by: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "hourly_rate": self.hourly_rate,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by
        }


@dataclass
class BillingConfiguration:
    """Project billing configuration."""
    
    billing_type: BillingType
    currency: str = "USD"
    
    # Hourly billing
    hourly_rate: Optional[float] = None
    
    # Fixed price billing
    fixed_price: Optional[float] = None
    
    # Milestone billing
    milestones: List[Dict] = field(default_factory=list)
    
    # Retainer billing
    retainer_amount: Optional[float] = None
    retainer_period: Optional[str] = None  # monthly, weekly, etc.
    
    # Budget and limits
    budget_limit: Optional[float] = None
    budget_alert_threshold: float = 0.8  # Alert at 80%
    
    def validate(self) -> None:
        """Validate billing configuration."""
        if self.billing_type == BillingType.HOURLY and not self.hourly_rate:
            raise ValidationError("Hourly rate is required for hourly billing", "hourly_rate")
        
        if self.billing_type == BillingType.FIXED and not self.fixed_price:
            raise ValidationError("Fixed price is required for fixed price billing", "fixed_price")
        
        if self.billing_type == BillingType.RETAINER and not self.retainer_amount:
            raise ValidationError("Retainer amount is required for retainer billing", "retainer_amount")
        
        if self.budget_alert_threshold and (self.budget_alert_threshold < 0 or self.budget_alert_threshold > 1):
            raise ValidationError("Budget alert threshold must be between 0 and 1", "budget_alert_threshold")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "billing_type": self.billing_type.value,
            "currency": self.currency,
            "hourly_rate": self.hourly_rate,
            "fixed_price": self.fixed_price,
            "milestones": self.milestones,
            "retainer_amount": self.retainer_amount,
            "retainer_period": self.retainer_period,
            "budget_limit": self.budget_limit,
            "budget_alert_threshold": self.budget_alert_threshold
        }


@dataclass
class Project(AggregateRoot):
    """
    Project aggregate root.
    Represents a project for a client with team members, tasks and billing.
    """
    
    # Required fields
    owner_id: str  # UUID of the freelancer who owns this project
    client_id: int
    name: str
    
    # Project details
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.HOURLY
    status: ProjectStatus = ProjectStatus.PLANNING
    
    # Dates
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    deadline: Optional[date] = None
    
    # Billing configuration
    billing: BillingConfiguration = field(default_factory=lambda: BillingConfiguration(BillingType.HOURLY))
    
    # Team and permissions
    members: List[ProjectMember] = field(default_factory=list)
    
    # Additional information
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    # Statistics (computed fields)
    total_tasks: int = 0
    completed_tasks: int = 0
    total_hours: float = 0
    total_cost: float = 0
    budget_used_percentage: float = 0
    
    # Visibility and sharing
    is_public: bool = False
    public_token: Optional[str] = None
    
    def __post_init__(self):
        """Initialize project after creation."""
        super().__post_init__()
        
        # Validate on creation
        self.validate()
        
        # Add owner as project member if not already present
        if not any(member.user_id == self.owner_id for member in self.members):
            self.members.append(ProjectMember(
                user_id=self.owner_id,
                role=ProjectRole.OWNER,
                hourly_rate=self.billing.hourly_rate
            ))
        
        # Add creation event if new
        if self.is_new:
            self.add_event(ProjectCreatedEvent(
                project_id=self.id or 0,
                name=self.name,
                client_id=self.client_id,
                owner_id=self.owner_id
            ))
    
    def validate(self) -> None:
        """Validate project state."""
        # Required fields
        if not self.owner_id:
            raise ValidationError("Owner ID is required", "owner_id")
        
        if not self.client_id:
            raise ValidationError("Client ID is required", "client_id")
        
        if not self.name:
            raise ValidationError("Project name is required", "name")
        
        if len(self.name) > 255:
            raise ValidationError("Project name too long (max 255 characters)", "name")
        
        # Validate dates
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date", "end_date")
        
        if self.deadline and self.start_date and self.deadline < self.start_date:
            raise ValidationError("Deadline cannot be before start date", "deadline")
        
        # Validate billing configuration
        self.billing.validate()
        
        # Validate description length
        if self.description and len(self.description) > 2000:
            raise ValidationError("Description too long (max 2000 characters)", "description")
        
        # Validate notes length
        if self.notes and len(self.notes) > 2000:
            raise ValidationError("Notes too long (max 2000 characters)", "notes")
        
        # Validate tags
        if len(self.tags) > 20:
            raise ValidationError("Too many tags (max 20)", "tags")
        
        for tag in self.tags:
            if len(tag) > 50:
                raise ValidationError(f"Tag '{tag}' too long (max 50 characters)", "tags")
    
    @property
    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE
    
    @property
    def is_completed(self) -> bool:
        """Check if project is completed."""
        return self.status == ProjectStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """Check if project is cancelled."""
        return self.status == ProjectStatus.CANCELLED
    
    @property
    def is_archived(self) -> bool:
        """Check if project is archived."""
        return self.status == ProjectStatus.ARCHIVED
    
    @property
    def can_track_time(self) -> bool:
        """Check if time can be tracked on this project."""
        return self.status in [ProjectStatus.PLANNING, ProjectStatus.ACTIVE]
    
    @property
    def progress_percentage(self) -> float:
        """Get project progress percentage based on completed tasks."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def is_over_budget(self) -> bool:
        """Check if project is over budget."""
        if not self.billing.budget_limit:
            return False
        return self.total_cost > self.billing.budget_limit
    
    @property
    def budget_alert_needed(self) -> bool:
        """Check if budget alert is needed."""
        if not self.billing.budget_limit:
            return False
        threshold = self.billing.budget_limit * self.billing.budget_alert_threshold
        return self.total_cost >= threshold and not self.is_over_budget
    
    def get_member(self, user_id: str) -> Optional[ProjectMember]:
        """Get project member by user ID."""
        return next((member for member in self.members if member.user_id == user_id), None)
    
    def user_has_role(self, user_id: str, required_role: ProjectRole) -> bool:
        """Check if user has the required role or higher."""
        member = self.get_member(user_id)
        if not member:
            return False
        
        # Role hierarchy
        role_hierarchy = {
            ProjectRole.VIEWER: 1,
            ProjectRole.CONTRIBUTOR: 2,
            ProjectRole.MANAGER: 3,
            ProjectRole.OWNER: 4
        }
        
        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)
    
    def update_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        deadline: Optional[date] = None,
        notes: Optional[str] = None
    ) -> None:
        """Update project information."""
        if self.is_archived:
            raise BusinessRuleViolation("Cannot update archived project")
        
        if name is not None:
            self.name = name
        
        if description is not None:
            self.description = description
        
        if start_date is not None:
            self.start_date = start_date
        
        if end_date is not None:
            self.end_date = end_date
        
        if deadline is not None:
            self.deadline = deadline
        
        if notes is not None:
            self.notes = notes
        
        self.validate()
        self.mark_as_updated()
        self.increment_version()
    
    def change_status(self, new_status: ProjectStatus, user_id: str) -> None:
        """Change project status."""
        if not self.user_has_role(user_id, ProjectRole.MANAGER):
            raise BusinessRuleViolation("Only managers or owners can change project status")
        
        if self.status == new_status:
            raise BusinessRuleViolation(f"Project is already {new_status.value}")
        
        # Business rules for status changes
        if self.status == ProjectStatus.ARCHIVED:
            raise BusinessRuleViolation("Cannot change status of archived project")
        
        if new_status == ProjectStatus.COMPLETED and self.total_tasks > 0 and self.completed_tasks < self.total_tasks:
            raise BusinessRuleViolation("Cannot complete project with pending tasks")
        
        old_status = self.status
        self.status = new_status
        
        # Set completion date if completing
        if new_status == ProjectStatus.COMPLETED:
            self.end_date = date.today()
            self.add_event(ProjectCompletedEvent(
                project_id=self.id or 0,
                completion_date=datetime.utcnow(),
                final_budget_used=self.total_cost
            ))
        
        self.mark_as_updated()
        self.increment_version()
        self.add_event(ProjectStatusChangedEvent(self.id or 0, old_status, new_status))
    
    def add_member(
        self,
        user_id: str,
        role: ProjectRole,
        hourly_rate: Optional[float] = None,
        added_by: Optional[str] = None
    ) -> None:
        """Add a member to the project."""
        if not added_by or not self.user_has_role(added_by, ProjectRole.MANAGER):
            raise BusinessRuleViolation("Only managers or owners can add members")
        
        if self.get_member(user_id):
            raise BusinessRuleViolation(f"User {user_id} is already a member of this project")
        
        # Cannot have multiple owners
        if role == ProjectRole.OWNER and any(member.role == ProjectRole.OWNER for member in self.members):
            raise BusinessRuleViolation("Project can only have one owner")
        
        member = ProjectMember(
            user_id=user_id,
            role=role,
            hourly_rate=hourly_rate,
            added_by=added_by
        )
        
        self.members.append(member)
        self.mark_as_updated()
        self.increment_version()
        self.add_event(ProjectMemberAddedEvent(self.id or 0, user_id, role))
    
    def remove_member(self, user_id: str, removed_by: str) -> None:
        """Remove a member from the project."""
        if not self.user_has_role(removed_by, ProjectRole.MANAGER):
            raise BusinessRuleViolation("Only managers or owners can remove members")
        
        member = self.get_member(user_id)
        if not member:
            raise BusinessRuleViolation(f"User {user_id} is not a member of this project")
        
        # Cannot remove the owner
        if member.role == ProjectRole.OWNER:
            raise BusinessRuleViolation("Cannot remove project owner")
        
        self.members = [m for m in self.members if m.user_id != user_id]
        self.mark_as_updated()
        self.increment_version()
    
    def update_member_role(self, user_id: str, new_role: ProjectRole, updated_by: str) -> None:
        """Update member role."""
        if not self.user_has_role(updated_by, ProjectRole.OWNER):
            raise BusinessRuleViolation("Only owners can update member roles")
        
        member = self.get_member(user_id)
        if not member:
            raise BusinessRuleViolation(f"User {user_id} is not a member of this project")
        
        # Cannot change owner role
        if member.role == ProjectRole.OWNER or new_role == ProjectRole.OWNER:
            raise BusinessRuleViolation("Cannot change owner role")
        
        member.role = new_role
        self.mark_as_updated()
        self.increment_version()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the project."""
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
        """Remove a tag from the project."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.mark_as_updated()
    
    def archive(self, user_id: str, reason: Optional[str] = None) -> None:
        """Archive the project."""
        if not self.user_has_role(user_id, ProjectRole.OWNER):
            raise BusinessRuleViolation("Only owners can archive projects")
        
        if self.status == ProjectStatus.ARCHIVED:
            raise BusinessRuleViolation("Project is already archived")
        
        if self.status == ProjectStatus.ACTIVE:
            raise BusinessRuleViolation("Cannot archive active project. Complete or cancel it first.")
        
        self.status = ProjectStatus.ARCHIVED
        self.mark_as_updated()
        self.increment_version()
    
    def calculate_budget_usage(self) -> Dict[str, float]:
        """Calculate budget usage statistics."""
        if not self.billing.budget_limit:
            return {
                "budget_limit": 0,
                "total_cost": self.total_cost,
                "remaining_budget": 0,
                "usage_percentage": 0
            }
        
        remaining = max(0, self.billing.budget_limit - self.total_cost)
        usage_percentage = min(100, (self.total_cost / self.billing.budget_limit) * 100)
        
        return {
            "budget_limit": self.billing.budget_limit,
            "total_cost": self.total_cost,
            "remaining_budget": remaining,
            "usage_percentage": usage_percentage
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["project_type"] = self.project_type.value
        data["status"] = self.status.value
        
        # Convert dates
        if self.start_date:
            data["start_date"] = self.start_date.isoformat()
        if self.end_date:
            data["end_date"] = self.end_date.isoformat()
        if self.deadline:
            data["deadline"] = self.deadline.isoformat()
        
        # Convert billing configuration
        data["billing"] = self.billing.to_dict()
        
        # Convert members
        data["members"] = [member.to_dict() for member in self.members]
        
        # Add computed values
        data["progress_percentage"] = self.progress_percentage
        data["budget_usage"] = self.calculate_budget_usage()
        
        return data