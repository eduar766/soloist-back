"""
User domain model.
Represents a system user with authentication and profile information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from app.domain.models.base import (
    AggregateRoot, 
    Email, 
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class UserRole(str, Enum):
    """System-wide user roles."""
    ADMIN = "admin"
    FREELANCER = "freelancer"
    CLIENT = "client"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


# Domain Events

class UserCreatedEvent(DomainEvent):
    """Event raised when a new user is created."""
    
    def __init__(self, user_id: str, email: str, full_name: str):
        super().__init__()
        self.user_id = user_id
        self.email = email
        self.full_name = full_name
    
    @property
    def event_name(self) -> str:
        return "user.created"


class UserProfileUpdatedEvent(DomainEvent):
    """Event raised when user profile is updated."""
    
    def __init__(self, user_id: str, changes: dict):
        super().__init__()
        self.user_id = user_id
        self.changes = changes
    
    @property
    def event_name(self) -> str:
        return "user.profile.updated"


class UserDeactivatedEvent(DomainEvent):
    """Event raised when user is deactivated."""
    
    def __init__(self, user_id: str, reason: Optional[str] = None):
        super().__init__()
        self.user_id = user_id
        self.reason = reason
    
    @property
    def event_name(self) -> str:
        return "user.deactivated"


@dataclass
class UserPreferences:
    """User preferences and settings."""
    
    locale: str = "es-CL"
    timezone: str = "America/Santiago"
    currency: str = "USD"
    date_format: str = "DD/MM/YYYY"
    time_format: str = "24h"
    notifications_enabled: bool = True
    email_notifications: bool = True
    weekly_summary: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "locale": self.locale,
            "timezone": self.timezone,
            "currency": self.currency,
            "date_format": self.date_format,
            "time_format": self.time_format,
            "notifications_enabled": self.notifications_enabled,
            "email_notifications": self.email_notifications,
            "weekly_summary": self.weekly_summary
        }


@dataclass
class User(AggregateRoot):
    """
    User aggregate root.
    Represents a system user with authentication and profile information.
    """
    
    # Required fields (using None as default but will be set in __post_init__)
    user_id: Optional[str] = None  # UUID from Supabase Auth
    email: Optional[Email] = None
    
    # Profile fields
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    bio: Optional[str] = None
    
    # System fields
    role: UserRole = UserRole.FREELANCER
    status: UserStatus = UserStatus.ACTIVE
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Authentication fields
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    
    # Billing fields (for freelancers)
    default_hourly_rate: Optional[float] = None
    default_currency: str = "USD"
    tax_id: Optional[str] = None
    billing_address: Optional[str] = None
    
    # Statistics (computed fields)
    total_projects: int = 0
    total_clients: int = 0
    total_hours_tracked: float = 0
    total_revenue: float = 0
    
    def __post_init__(self):
        """Initialize user after creation."""
        super().__post_init__()
        
        # Convert email string to Email value object if needed
        if isinstance(self.email, str):
            self.email = Email(self.email)
        
        # Validate on creation
        self.validate()
        
        # Add creation event if new
        if self.is_new:
            self.add_event(UserCreatedEvent(
                user_id=self.user_id,
                email=str(self.email),
                full_name=self.full_name or ""
            ))
    
    def validate(self) -> None:
        """Validate user state."""
        # Email is required and validated by value object
        if not self.user_id:
            raise ValidationError("User ID is required", "user_id")
        
        # Validate full name length if provided
        if self.full_name and len(self.full_name) > 255:
            raise ValidationError("Full name too long (max 255 characters)", "full_name")
        
        # Validate phone format if provided
        if self.phone:
            if len(self.phone) > 20:
                raise ValidationError("Phone number too long (max 20 characters)", "phone")
            # Basic phone validation (digits, spaces, +, -, parentheses)
            import re
            if not re.match(r'^[\d\s\+\-\(\)]+$', self.phone):
                raise ValidationError("Invalid phone number format", "phone")
        
        # Validate hourly rate if provided
        if self.default_hourly_rate is not None and self.default_hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative", "default_hourly_rate")
        
        # Validate avatar URL if provided
        if self.avatar_url and len(self.avatar_url) > 500:
            raise ValidationError("Avatar URL too long (max 500 characters)", "avatar_url")
    
    @property
    def display_name(self) -> str:
        """Get display name (full name or email)."""
        return self.full_name or self.email.local
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_freelancer(self) -> bool:
        """Check if user is a freelancer."""
        return self.role == UserRole.FREELANCER
    
    @property
    def is_client(self) -> bool:
        """Check if user is a client."""
        return self.role == UserRole.CLIENT
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def can_track_time(self) -> bool:
        """Check if user can track time."""
        return self.is_active and self.is_freelancer
    
    @property
    def can_create_invoices(self) -> bool:
        """Check if user can create invoices."""
        return self.is_active and self.is_freelancer
    
    def update_profile(
        self,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        position: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> None:
        """Update user profile information."""
        if not self.is_active:
            raise BusinessRuleViolation("Cannot update profile of inactive user")
        
        changes = {}
        
        if full_name is not None and full_name != self.full_name:
            self.full_name = full_name
            changes["full_name"] = full_name
        
        if phone is not None and phone != self.phone:
            self.phone = phone
            changes["phone"] = phone
        
        if company is not None and company != self.company:
            self.company = company
            changes["company"] = company
        
        if position is not None and position != self.position:
            self.position = position
            changes["position"] = position
        
        if bio is not None and bio != self.bio:
            self.bio = bio
            changes["bio"] = bio
        
        if avatar_url is not None and avatar_url != self.avatar_url:
            self.avatar_url = avatar_url
            changes["avatar_url"] = avatar_url
        
        if changes:
            self.validate()
            self.mark_as_updated()
            self.increment_version()
            self.add_event(UserProfileUpdatedEvent(self.user_id, changes))
    
    def update_billing_info(
        self,
        hourly_rate: Optional[float] = None,
        currency: Optional[str] = None,
        tax_id: Optional[str] = None,
        billing_address: Optional[str] = None
    ) -> None:
        """Update billing information."""
        if not self.is_freelancer:
            raise BusinessRuleViolation("Only freelancers can have billing information")
        
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise ValidationError("Hourly rate cannot be negative", "hourly_rate")
            self.default_hourly_rate = hourly_rate
        
        if currency is not None:
            self.default_currency = currency
        
        if tax_id is not None:
            self.tax_id = tax_id
        
        if billing_address is not None:
            self.billing_address = billing_address
        
        self.mark_as_updated()
        self.increment_version()
    
    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user preferences."""
        self.preferences = preferences
        self.mark_as_updated()
        self.increment_version()
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        if self.email_verified:
            raise BusinessRuleViolation("Email is already verified")
        
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.mark_as_updated()
        self.increment_version()
    
    def record_sign_in(self) -> None:
        """Record user sign in."""
        self.last_sign_in_at = datetime.utcnow()
        self.mark_as_updated()
    
    def deactivate(self, reason: Optional[str] = None) -> None:
        """Deactivate user account."""
        if self.status == UserStatus.DELETED:
            raise BusinessRuleViolation("Cannot deactivate deleted user")
        
        self.status = UserStatus.INACTIVE
        self.mark_as_updated()
        self.increment_version()
        self.add_event(UserDeactivatedEvent(self.user_id, reason))
    
    def reactivate(self) -> None:
        """Reactivate user account."""
        if self.status == UserStatus.DELETED:
            raise BusinessRuleViolation("Cannot reactivate deleted user")
        
        if self.status == UserStatus.ACTIVE:
            raise BusinessRuleViolation("User is already active")
        
        self.status = UserStatus.ACTIVE
        self.mark_as_updated()
        self.increment_version()
    
    def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend user account."""
        if self.status == UserStatus.DELETED:
            raise BusinessRuleViolation("Cannot suspend deleted user")
        
        self.status = UserStatus.SUSPENDED
        self.mark_as_updated()
        self.increment_version()
    
    def soft_delete(self) -> None:
        """Soft delete user account."""
        if self.status == UserStatus.DELETED:
            raise BusinessRuleViolation("User is already deleted")
        
        self.status = UserStatus.DELETED
        self.mark_as_updated()
        self.increment_version()
    
    def can_access_project(self, project_id: int) -> bool:
        """
        Check if user can access a project.
        This is a placeholder - actual implementation would check project membership.
        """
        # TODO: Implement actual project access check
        return self.is_active
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values to strings
        data["role"] = self.role.value
        data["status"] = self.status.value
        
        # Convert Email value object to string
        data["email"] = str(self.email)
        
        # Add preferences as nested dict
        data["preferences"] = self.preferences.to_dict()
        
        return data