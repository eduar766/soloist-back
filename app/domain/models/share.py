"""
Share domain model.
Represents public sharing tokens for projects, time sheets, and invoices.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from enum import Enum
import secrets
import string

from app.domain.models.base import (
    BaseEntity,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class ShareableType(str, Enum):
    """Type of entity that can be shared."""
    PROJECT = "project"
    TIMESHEET = "timesheet"
    INVOICE = "invoice"
    REPORT = "report"
    TASK_BOARD = "task_board"


class ShareType(str, Enum):
    """Type of sharing."""
    PUBLIC = "public"
    PASSWORD_PROTECTED = "password_protected"
    LIMITED_TIME = "limited_time"
    VIEW_ONLY = "view_only"
    DOWNLOADABLE = "downloadable"


class ShareStatus(str, Enum):
    """Status of the share."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"
    REVOKED = "revoked"


# Domain Events

class ShareCreatedEvent(DomainEvent):
    """Event raised when a share is created."""
    
    def __init__(self, share_id: int, token: str, shareable_type: ShareableType, entity_id: int, created_by: str):
        super().__init__()
        self.share_id = share_id
        self.token = token
        self.shareable_type = shareable_type
        self.entity_id = entity_id
        self.created_by = created_by
    
    @property
    def event_name(self) -> str:
        return "share.created"


class ShareAccessedEvent(DomainEvent):
    """Event raised when a share is accessed."""
    
    def __init__(self, share_id: int, token: str, ip_address: Optional[str], user_agent: Optional[str]):
        super().__init__()
        self.share_id = share_id
        self.token = token
        self.ip_address = ip_address
        self.user_agent = user_agent
    
    @property
    def event_name(self) -> str:
        return "share.accessed"


class ShareRevokedEvent(DomainEvent):
    """Event raised when a share is revoked."""
    
    def __init__(self, share_id: int, token: str, revoked_by: str, reason: Optional[str]):
        super().__init__()
        self.share_id = share_id
        self.token = token
        self.revoked_by = revoked_by
        self.reason = reason
    
    @property
    def event_name(self) -> str:
        return "share.revoked"


@dataclass
class ShareAccess:
    """Record of share access."""
    
    accessed_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    location: Optional[str] = None  # Geolocation if available
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "accessed_at": self.accessed_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "referer": self.referer,
            "location": self.location
        }


@dataclass
class SharePermissions:
    """Share permissions configuration."""
    
    can_view: bool = True
    can_download: bool = False
    can_print: bool = False
    can_export: bool = False
    
    # Time restrictions
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Access restrictions
    max_views: Optional[int] = None
    allowed_ips: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    
    # Watermark and branding
    show_watermark: bool = True
    hide_sensitive_data: bool = False
    
    def validate(self) -> None:
        """Validate permissions."""
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time", "end_time")
        
        if self.max_views is not None and self.max_views < 1:
            raise ValidationError("Max views must be positive", "max_views")
        
        # Validate IP addresses
        for ip in self.allowed_ips:
            # Basic IP validation (simplified)
            if not ip or len(ip.split('.')) != 4:
                raise ValidationError(f"Invalid IP address: {ip}", "allowed_ips")
        
        # Validate domains
        for domain in self.allowed_domains:
            if not domain or '.' not in domain:
                raise ValidationError(f"Invalid domain: {domain}", "allowed_domains")
    
    def is_access_allowed_at(self, time: datetime) -> bool:
        """Check if access is allowed at given time."""
        if self.start_time and time < self.start_time:
            return False
        if self.end_time and time > self.end_time:
            return False
        return True
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.allowed_ips:
            return True
        return ip_address in self.allowed_ips
    
    def is_domain_allowed(self, referer: Optional[str]) -> bool:
        """Check if referer domain is allowed."""
        if not self.allowed_domains or not referer:
            return True if not self.allowed_domains else False
        
        try:
            from urllib.parse import urlparse
            domain = urlparse(referer).netloc
            return domain in self.allowed_domains
        except:
            return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "can_view": self.can_view,
            "can_download": self.can_download,
            "can_print": self.can_print,
            "can_export": self.can_export,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "max_views": self.max_views,
            "allowed_ips": self.allowed_ips,
            "allowed_domains": self.allowed_domains,
            "show_watermark": self.show_watermark,
            "hide_sensitive_data": self.hide_sensitive_data
        }


class Share(BaseEntity):
    """
    Share entity.
    Represents a public sharing token for projects, invoices, time sheets, etc.
    """
    
    def __init__(
        self,
        created_by: str,
        shareable_type: ShareableType,
        entity_id: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Required fields
        self.created_by = created_by  # User ID who created the share
        self.shareable_type = shareable_type
        self.entity_id = entity_id  # ID of the shared entity
        
        # Share configuration
        self.token = Share.generate_token()
        self.share_type = ShareType.PUBLIC
        self.status = ShareStatus.ACTIVE
        
        # Optional fields
        self.title = None
        self.description = None
        self.password = None  # For password-protected shares
        
        # Expiration
        self.expires_at = None
        
        # Permissions
        self.permissions = SharePermissions()
        
        # Usage tracking
        self.view_count = 0
        self.last_accessed_at = None
        self.access_log = []
        
        # Metadata
        self.custom_slug = None  # Custom URL slug instead of token
        self.tags = []
    
    def __post_init__(self):
        """Initialize share after creation."""
        super().__post_init__()
        
        # Validate on creation
        self.validate()
        
        # Add creation event if new
        if self.is_new:
            self.add_event(ShareCreatedEvent(
                share_id=self.id or 0,
                token=self.token,
                shareable_type=self.shareable_type,
                entity_id=self.entity_id,
                created_by=self.created_by
            ))
    
    def validate(self) -> None:
        """Validate share state."""
        # Required fields
        if not self.created_by:
            raise ValidationError("Created by is required", "created_by")
        
        if not self.entity_id:
            raise ValidationError("Entity ID is required", "entity_id")
        
        if not self.token:
            raise ValidationError("Token is required", "token")
        
        # Validate token format
        if len(self.token) < 16:
            raise ValidationError("Token too short (min 16 characters)", "token")
        
        # Validate password for protected shares
        if self.share_type == ShareType.PASSWORD_PROTECTED and not self.password:
            raise ValidationError("Password is required for password-protected shares", "password")
        
        # Validate custom slug
        if self.custom_slug:
            if len(self.custom_slug) < 3:
                raise ValidationError("Custom slug too short (min 3 characters)", "custom_slug")
            
            if not self.custom_slug.replace('-', '').replace('_', '').isalnum():
                raise ValidationError("Custom slug can only contain letters, numbers, hyphens, and underscores", "custom_slug")
        
        # Validate expiration
        if self.expires_at and self.expires_at <= datetime.utcnow():
            self.status = ShareStatus.EXPIRED
        
        # Validate permissions
        self.permissions.validate()
        
        # Validate title and description lengths
        if self.title and len(self.title) > 255:
            raise ValidationError("Title too long (max 255 characters)", "title")
        
        if self.description and len(self.description) > 1000:
            raise ValidationError("Description too long (max 1000 characters)", "description")
        
        # Validate tags
        if len(self.tags) > 10:
            raise ValidationError("Too many tags (max 10)", "tags")
        
        for tag in self.tags:
            if len(tag) > 50:
                raise ValidationError(f"Tag '{tag}' too long (max 50 characters)", "tags")
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @property
    def is_active(self) -> bool:
        """Check if share is active."""
        return self.status == ShareStatus.ACTIVE
    
    @property
    def is_expired(self) -> bool:
        """Check if share is expired."""
        if self.status == ShareStatus.EXPIRED:
            return True
        
        if self.expires_at and self.expires_at <= datetime.utcnow():
            self.status = ShareStatus.EXPIRED
            return True
        
        return False
    
    @property
    def is_accessible(self) -> bool:
        """Check if share is accessible."""
        return self.is_active and not self.is_expired
    
    @property
    def is_password_protected(self) -> bool:
        """Check if share is password protected."""
        return self.share_type == ShareType.PASSWORD_PROTECTED
    
    @property
    def is_view_limited(self) -> bool:
        """Check if share has view limits."""
        return self.permissions.max_views is not None
    
    @property
    def remaining_views(self) -> Optional[int]:
        """Get remaining views allowed."""
        if not self.is_view_limited:
            return None
        return max(0, self.permissions.max_views - self.view_count)
    
    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry (negative if expired)."""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - datetime.utcnow()
        return delta.days
    
    def can_be_accessed(
        self,
        ip_address: Optional[str] = None,
        referer: Optional[str] = None,
        current_time: Optional[datetime] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if share can be accessed with given parameters."""
        current_time = current_time or datetime.utcnow()
        
        # Check basic accessibility
        if not self.is_accessible:
            return False, "Share is not accessible"
        
        # Check time restrictions
        if not self.permissions.is_access_allowed_at(current_time):
            return False, "Access not allowed at this time"
        
        # Check view limits
        if self.is_view_limited and self.remaining_views == 0:
            return False, "View limit exceeded"
        
        # Check IP restrictions
        if ip_address and not self.permissions.is_ip_allowed(ip_address):
            return False, "IP address not allowed"
        
        # Check domain restrictions
        if not self.permissions.is_domain_allowed(referer):
            return False, "Domain not allowed"
        
        return True, None
    
    def verify_password(self, password: str) -> bool:
        """Verify password for protected shares."""
        if not self.is_password_protected:
            return True
        
        # In a real implementation, this would use proper password hashing
        return self.password == password
    
    def record_access(
        self,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
    ) -> None:
        """Record an access to the share."""
        if not self.is_accessible:
            raise BusinessRuleViolation("Cannot record access to inactive share")
        
        # Check access permissions
        can_access, reason = self.can_be_accessed(ip_address, referer)
        if not can_access:
            raise BusinessRuleViolation(f"Access denied: {reason}")
        
        # Record the access
        access = ShareAccess(
            accessed_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer
        )
        
        self.access_log.append(access)
        self.view_count += 1
        self.last_accessed_at = access.accessed_at
        
        # Check if view limit is reached
        if self.is_view_limited and self.remaining_views == 0:
            self.status = ShareStatus.EXPIRED
        
        self.mark_as_updated()
        
        self.add_event(ShareAccessedEvent(
            share_id=self.id or 0,
            token=self.token,
            ip_address=ip_address,
            user_agent=user_agent
        ))
    
    def update_permissions(self, permissions: SharePermissions) -> None:
        """Update share permissions."""
        if self.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Cannot update permissions on revoked share")
        
        permissions.validate()
        self.permissions = permissions
        self.validate()
        self.mark_as_updated()
    
    def set_expiry(self, expires_at: Optional[datetime]) -> None:
        """Set or update expiry time."""
        if expires_at and expires_at <= datetime.utcnow():
            raise ValidationError("Expiry time must be in the future", "expires_at")
        
        self.expires_at = expires_at
        
        # Update status if needed
        if expires_at is None and self.status == ShareStatus.EXPIRED:
            self.status = ShareStatus.ACTIVE
        
        self.mark_as_updated()
    
    def set_password(self, password: Optional[str]) -> None:
        """Set or update password."""
        if password and len(password) < 6:
            raise ValidationError("Password too short (min 6 characters)", "password")
        
        self.password = password
        
        # Update share type
        if password:
            self.share_type = ShareType.PASSWORD_PROTECTED
        elif self.share_type == ShareType.PASSWORD_PROTECTED:
            self.share_type = ShareType.PUBLIC
        
        self.mark_as_updated()
    
    def update_info(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        custom_slug: Optional[str] = None
    ) -> None:
        """Update share information."""
        if title is not None:
            self.title = title
        
        if description is not None:
            self.description = description
        
        if custom_slug is not None:
            self.custom_slug = custom_slug
        
        self.validate()
        self.mark_as_updated()
    
    def disable(self) -> None:
        """Disable the share temporarily."""
        if self.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Cannot disable revoked share")
        
        self.status = ShareStatus.DISABLED
        self.mark_as_updated()
    
    def enable(self) -> None:
        """Enable the share."""
        if self.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Cannot enable revoked share")
        
        # Check if expired
        if self.expires_at and self.expires_at <= datetime.utcnow():
            raise BusinessRuleViolation("Cannot enable expired share")
        
        self.status = ShareStatus.ACTIVE
        self.mark_as_updated()
    
    def revoke(self, revoked_by: str, reason: Optional[str] = None) -> None:
        """Revoke the share permanently."""
        if self.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Share is already revoked")
        
        self.status = ShareStatus.REVOKED
        self.mark_as_updated()
        self.increment_version()
        
        self.add_event(ShareRevokedEvent(
            share_id=self.id or 0,
            token=self.token,
            revoked_by=revoked_by,
            reason=reason
        ))
    
    def regenerate_token(self) -> str:
        """Generate a new token for the share."""
        if self.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Cannot regenerate token for revoked share")
        
        old_token = self.token
        self.token = self.generate_token()
        self.mark_as_updated()
        return old_token
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the share."""
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
        """Remove a tag from the share."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.mark_as_updated()
    
    def get_public_url(self, base_url: str) -> str:
        """Get the public URL for this share."""
        if self.custom_slug:
            return f"{base_url}/shared/{self.custom_slug}"
        return f"{base_url}/shared/{self.token}"
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data for the share."""
        # Group access by date
        access_by_date = {}
        for access in self.access_log:
            date_key = access.accessed_at.date().isoformat()
            access_by_date[date_key] = access_by_date.get(date_key, 0) + 1
        
        # Get unique IPs
        unique_ips = set(access.ip_address for access in self.access_log if access.ip_address)
        
        # Get top user agents
        user_agents = {}
        for access in self.access_log:
            if access.user_agent:
                user_agents[access.user_agent] = user_agents.get(access.user_agent, 0) + 1
        
        return {
            "total_views": self.view_count,
            "unique_visitors": len(unique_ips),
            "access_by_date": access_by_date,
            "top_user_agents": sorted(user_agents.items(), key=lambda x: x[1], reverse=True)[:5],
            "last_accessed": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "remaining_views": self.remaining_views,
            "days_until_expiry": self.days_until_expiry
        }
    
    @classmethod
    def create_project_share(
        cls,
        project_id: int,
        created_by: str,
        title: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        password: Optional[str] = None
    ) -> 'Share':
        """Create a share for a project."""
        share = cls(
            created_by=created_by,
            shareable_type=ShareableType.PROJECT,
            entity_id=project_id,
            title=title,
            expires_at=expires_at,
            password=password,
            share_type=ShareType.PASSWORD_PROTECTED if password else ShareType.PUBLIC
        )
        
        # Set project-specific permissions
        share.permissions.can_view = True
        share.permissions.can_download = True
        share.permissions.show_watermark = True
        
        return share
    
    @classmethod
    def create_invoice_share(
        cls,
        invoice_id: int,
        created_by: str,
        title: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> 'Share':
        """Create a share for an invoice."""
        share = cls(
            created_by=created_by,
            shareable_type=ShareableType.INVOICE,
            entity_id=invoice_id,
            title=title,
            expires_at=expires_at,
            share_type=ShareType.PUBLIC
        )
        
        # Set invoice-specific permissions
        share.permissions.can_view = True
        share.permissions.can_download = True
        share.permissions.can_print = True
        share.permissions.show_watermark = False
        share.permissions.hide_sensitive_data = False
        
        return share
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["shareable_type"] = self.shareable_type.value
        data["share_type"] = self.share_type.value
        data["status"] = self.status.value
        
        # Convert datetime fields
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        if self.last_accessed_at:
            data["last_accessed_at"] = self.last_accessed_at.isoformat()
        
        # Convert permissions
        data["permissions"] = self.permissions.to_dict()
        
        # Convert access log
        data["access_log"] = [access.to_dict() for access in self.access_log]
        
        # Add computed properties
        data["is_active"] = self.is_active
        data["is_expired"] = self.is_expired
        data["is_accessible"] = self.is_accessible
        data["is_password_protected"] = self.is_password_protected
        data["remaining_views"] = self.remaining_views
        data["days_until_expiry"] = self.days_until_expiry
        
        # Don't include password in serialization
        if "password" in data:
            del data["password"]
        
        return data