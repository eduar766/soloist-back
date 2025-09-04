"""
Share DTOs for the application layer.
Data Transfer Objects for resource sharing operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import Field, validator
from enum import Enum

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin
)


class ShareResourceType(str, Enum):
    """Shared resource type options."""
    PROJECT = "project"
    INVOICE = "invoice"
    TIME_REPORT = "time_report"
    TASK_BOARD = "task_board"
    CLIENT_REPORT = "client_report"


class ShareAccessLevel(str, Enum):
    """Share access level options."""
    VIEW_ONLY = "view_only"
    COMMENT = "comment"
    EDIT = "edit"


class ShareStatus(str, Enum):
    """Share status options."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DISABLED = "disabled"


# Request DTOs
class CreateShareRequestDTO(CreateRequestDTO):
    """DTO for creating a share link."""
    
    resource_type: ShareResourceType = Field(description="Type of resource to share")
    resource_id: int = Field(description="ID of the resource to share")
    
    # Access configuration
    access_level: ShareAccessLevel = Field(default=ShareAccessLevel.VIEW_ONLY, description="Access level")
    password_protected: bool = Field(default=False, description="Whether share requires password")
    password: Optional[str] = Field(default=None, min_length=4, max_length=50, description="Share password")
    
    # Expiration
    expires_at: Optional[datetime] = Field(default=None, description="Share expiration timestamp")
    max_views: Optional[int] = Field(default=None, ge=1, description="Maximum number of views")
    
    # Customization
    title: Optional[str] = Field(default=None, max_length=255, description="Custom share title")
    description: Optional[str] = Field(default=None, max_length=500, description="Share description")
    custom_message: Optional[str] = Field(default=None, max_length=1000, description="Custom message for viewers")
    
    # Branding
    show_branding: bool = Field(default=True, description="Whether to show app branding")
    custom_logo_url: Optional[str] = Field(default=None, max_length=500, description="Custom logo URL")
    
    # Notification
    notify_on_view: bool = Field(default=False, description="Notify owner when shared resource is viewed")
    
    @validator('password')
    def validate_password_requirement(cls, v, values):
        """Validate password when password protection is enabled."""
        if values.get('password_protected') and not v:
            raise ValueError('Password is required when password protection is enabled')
        if not values.get('password_protected') and v:
            raise ValueError('Password should not be provided when password protection is disabled')
        return v
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        """Validate expiration is in the future."""
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration must be in the future')
        return v


class UpdateShareRequestDTO(UpdateRequestDTO):
    """DTO for updating share configuration."""
    
    # Access configuration
    access_level: Optional[ShareAccessLevel] = Field(default=None, description="Access level")
    password_protected: Optional[bool] = Field(default=None, description="Whether share requires password")
    password: Optional[str] = Field(default=None, min_length=4, max_length=50, description="Share password")
    
    # Expiration
    expires_at: Optional[datetime] = Field(default=None, description="Share expiration timestamp")
    max_views: Optional[int] = Field(default=None, ge=1, description="Maximum number of views")
    
    # Customization
    title: Optional[str] = Field(default=None, max_length=255, description="Custom share title")
    description: Optional[str] = Field(default=None, max_length=500, description="Share description")
    custom_message: Optional[str] = Field(default=None, max_length=1000, description="Custom message for viewers")
    
    # Branding
    show_branding: Optional[bool] = Field(default=None, description="Whether to show app branding")
    custom_logo_url: Optional[str] = Field(default=None, max_length=500, description="Custom logo URL")
    
    # Notification
    notify_on_view: Optional[bool] = Field(default=None, description="Notify owner when viewed")


class AccessSharedResourceRequestDTO(RequestDTO):
    """DTO for accessing a shared resource."""
    
    token: str = Field(description="Share token")
    password: Optional[str] = Field(default=None, description="Share password if required")
    
    # Tracking
    user_agent: Optional[str] = Field(default=None, max_length=500, description="User agent string")
    ip_address: Optional[str] = Field(default=None, max_length=45, description="IP address")
    referrer: Optional[str] = Field(default=None, max_length=500, description="Referrer URL")


class RevokeShareRequestDTO(RequestDTO):
    """DTO for revoking a share."""
    
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for revocation")


class ListSharesRequestDTO(FilterRequestDTO):
    """DTO for listing shares with filters."""
    
    resource_type: Optional[ShareResourceType] = Field(default=None, description="Filter by resource type")
    resource_id: Optional[int] = Field(default=None, description="Filter by resource ID")
    status: Optional[ShareStatus] = Field(default=None, description="Filter by status")
    access_level: Optional[ShareAccessLevel] = Field(default=None, description="Filter by access level")
    is_password_protected: Optional[bool] = Field(default=None, description="Filter by password protection")
    is_expired: Optional[bool] = Field(default=None, description="Filter expired shares")
    has_been_viewed: Optional[bool] = Field(default=None, description="Filter shares that have been viewed")


class ShareAnalyticsRequestDTO(RequestDTO):
    """DTO for share analytics requests."""
    
    start_date: date = Field(description="Analytics start date")
    end_date: date = Field(description="Analytics end date")
    resource_type: Optional[ShareResourceType] = Field(default=None, description="Filter by resource type")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v


# Response DTOs
class ShareResponseDTO(ResponseDTO, TimestampMixin):
    """DTO for share response."""
    
    # Basic info
    token: str = Field(description="Unique share token")
    owner_id: str = Field(description="Share owner user ID")
    resource_type: ShareResourceType = Field(description="Type of shared resource")
    resource_id: int = Field(description="ID of shared resource")
    resource_title: str = Field(description="Title of shared resource")
    
    # Access configuration
    access_level: ShareAccessLevel = Field(description="Access level")
    password_protected: bool = Field(description="Whether password protected")
    status: ShareStatus = Field(description="Share status")
    
    # Expiration
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    max_views: Optional[int] = Field(default=None, description="Maximum views allowed")
    
    # Customization
    title: Optional[str] = Field(default=None, description="Custom share title")
    description: Optional[str] = Field(default=None, description="Share description")
    custom_message: Optional[str] = Field(default=None, description="Custom message")
    
    # Branding
    show_branding: bool = Field(description="Whether to show branding")
    custom_logo_url: Optional[str] = Field(default=None, description="Custom logo URL")
    
    # Settings
    notify_on_view: bool = Field(description="Whether to notify on view")
    
    # Usage tracking
    view_count: int = Field(description="Number of times viewed")
    unique_view_count: int = Field(description="Number of unique viewers")
    last_viewed_at: Optional[datetime] = Field(default=None, description="Last view timestamp")
    
    # Computed fields
    is_active: bool = Field(description="Whether share is currently active")
    is_expired: bool = Field(description="Whether share has expired")
    is_view_limit_reached: bool = Field(description="Whether view limit is reached")
    public_url: str = Field(description="Public access URL")
    days_until_expiration: Optional[int] = Field(default=None, description="Days until expiration")


class ShareSummaryResponseDTO(ResponseDTO):
    """DTO for share summary (used in lists)."""
    
    token: str = Field(description="Share token")
    resource_type: ShareResourceType = Field(description="Resource type")
    resource_title: str = Field(description="Resource title")
    access_level: ShareAccessLevel = Field(description="Access level")
    status: ShareStatus = Field(description="Status")
    password_protected: bool = Field(description="Password protected")
    view_count: int = Field(description="View count")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration")
    last_viewed_at: Optional[datetime] = Field(default=None, description="Last viewed")
    created_at: datetime = Field(description="Creation timestamp")
    is_active: bool = Field(description="Is active")
    public_url: str = Field(description="Public URL")


class SharedResourceResponseDTO(ResponseDTO):
    """DTO for accessing shared resource content."""
    
    # Share info
    share_token: str = Field(description="Share token")
    resource_type: ShareResourceType = Field(description="Resource type")
    access_level: ShareAccessLevel = Field(description="User's access level")
    
    # Customization
    title: Optional[str] = Field(default=None, description="Custom title")
    description: Optional[str] = Field(default=None, description="Description")
    custom_message: Optional[str] = Field(default=None, description="Custom message")
    
    # Branding
    show_branding: bool = Field(description="Show branding")
    custom_logo_url: Optional[str] = Field(default=None, description="Custom logo URL")
    
    # Resource content (varies by type)
    resource_data: Dict[str, Any] = Field(description="The actual shared resource data")
    
    # Access info
    accessed_at: datetime = Field(description="When resource was accessed")
    view_number: int = Field(description="View number for this access")
    
    # Capabilities
    can_comment: bool = Field(description="Whether user can comment")
    can_edit: bool = Field(description="Whether user can edit")
    can_download: bool = Field(description="Whether user can download")


class ShareAccessLogResponseDTO(ResponseDTO):
    """DTO for share access log entry."""
    
    accessed_at: datetime = Field(description="Access timestamp")
    ip_address: Optional[str] = Field(default=None, description="Accessor IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    referrer: Optional[str] = Field(default=None, description="Referrer URL")
    location: Optional[Dict[str, str]] = Field(default=None, description="Estimated location")
    access_duration: Optional[int] = Field(default=None, description="Access duration in seconds")
    
    # Computed fields
    is_unique_visitor: bool = Field(description="Whether this was a unique visit")
    access_type: str = Field(description="Type of access (direct, referral, etc.)")


class ShareStatsResponseDTO(ResponseDTO):
    """DTO for share statistics."""
    
    share_token: str = Field(description="Share token")
    total_views: int = Field(description="Total views")
    unique_views: int = Field(description="Unique views")
    
    # Time-based stats
    views_today: int = Field(description="Views today")
    views_this_week: int = Field(description="Views this week")
    views_this_month: int = Field(description="Views this month")
    
    # Geographic stats
    top_countries: List[Dict[str, Any]] = Field(description="Top countries by views")
    top_cities: List[Dict[str, Any]] = Field(description="Top cities by views")
    
    # Temporal stats
    peak_viewing_hours: List[int] = Field(description="Peak viewing hours")
    daily_views: List[Dict[str, Any]] = Field(description="Daily view breakdown")
    
    # Referrer stats
    top_referrers: List[Dict[str, Any]] = Field(description="Top referrer sources")
    
    # Engagement
    average_view_duration: Optional[float] = Field(default=None, description="Average view duration")
    bounce_rate: Optional[float] = Field(default=None, description="Bounce rate percentage")
    
    stats_period_start: date = Field(description="Statistics period start")
    stats_period_end: date = Field(description="Statistics period end")


class ShareAnalyticsResponseDTO(ResponseDTO):
    """DTO for comprehensive share analytics."""
    
    # Overview metrics
    total_active_shares: int = Field(description="Total active shares")
    total_views: int = Field(description="Total views across all shares")
    unique_viewers: int = Field(description="Total unique viewers")
    
    # Performance metrics
    most_viewed_shares: List[Dict[str, Any]] = Field(description="Most viewed shares")
    best_performing_resource_types: List[Dict[str, Any]] = Field(description="Best performing resource types")
    
    # Trends
    view_trend: List[Dict[str, Any]] = Field(description="View trend over time")
    share_creation_trend: List[Dict[str, Any]] = Field(description="Share creation trend")
    
    # Geographic insights
    global_reach: Dict[str, Any] = Field(description="Global reach statistics")
    top_regions: List[Dict[str, Any]] = Field(description="Top regions by engagement")
    
    # Engagement analysis
    engagement_metrics: Dict[str, Any] = Field(description="Engagement analysis")
    conversion_funnel: List[Dict[str, Any]] = Field(description="Conversion funnel analysis")
    
    analysis_period_start: date = Field(description="Analysis period start")
    analysis_period_end: date = Field(description="Analysis period end")
    last_calculated: datetime = Field(description="When analytics were calculated")


# Bulk operation DTOs
class BulkUpdateSharesRequestDTO(RequestDTO):
    """DTO for bulk share updates."""
    
    share_ids: List[int] = Field(min_items=1, max_items=50, description="Share IDs")
    status: Optional[ShareStatus] = Field(default=None, description="New status")
    expires_at: Optional[datetime] = Field(default=None, description="New expiration")
    access_level: Optional[ShareAccessLevel] = Field(default=None, description="New access level")
    notify_on_view: Optional[bool] = Field(default=None, description="Enable/disable notifications")


class BulkRevokeSharesRequestDTO(RequestDTO):
    """DTO for bulk share revocation."""
    
    share_ids: List[int] = Field(min_items=1, max_items=50, description="Share IDs to revoke")
    reason: Optional[str] = Field(default=None, max_length=500, description="Revocation reason")


# Export DTOs
class ExportShareAnalyticsRequestDTO(RequestDTO):
    """DTO for exporting share analytics."""
    
    format: str = Field(description="Export format: csv, xlsx, pdf")
    start_date: date = Field(description="Export start date")
    end_date: date = Field(description="Export end date")
    resource_types: Optional[List[ShareResourceType]] = Field(default=None, description="Filter by resource types")
    include_access_logs: bool = Field(default=True, description="Include detailed access logs")
    include_geographic_data: bool = Field(default=True, description="Include geographic breakdown")
    
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


# Template DTOs
class ShareTemplateRequestDTO(RequestDTO):
    """DTO for creating share templates."""
    
    name: str = Field(min_length=1, max_length=100, description="Template name")
    resource_type: ShareResourceType = Field(description="Resource type for template")
    
    # Default settings
    default_access_level: ShareAccessLevel = Field(default=ShareAccessLevel.VIEW_ONLY, description="Default access level")
    default_expires_in_days: Optional[int] = Field(default=None, ge=1, le=365, description="Default expiration in days")
    default_max_views: Optional[int] = Field(default=None, ge=1, description="Default max views")
    default_password_protected: bool = Field(default=False, description="Default password protection")
    
    # Default customization
    default_title: Optional[str] = Field(default=None, max_length=255, description="Default title")
    default_message: Optional[str] = Field(default=None, max_length=1000, description="Default message")
    default_show_branding: bool = Field(default=True, description="Default branding setting")
    
    description: Optional[str] = Field(default=None, max_length=500, description="Template description")


class ShareTemplateResponseDTO(ResponseDTO, TimestampMixin):
    """DTO for share template response."""
    
    name: str = Field(description="Template name")
    resource_type: ShareResourceType = Field(description="Resource type")
    owner_id: str = Field(description="Template owner ID")
    
    # Default settings
    default_access_level: ShareAccessLevel = Field(description="Default access level")
    default_expires_in_days: Optional[int] = Field(default=None, description="Default expiration days")
    default_max_views: Optional[int] = Field(default=None, description="Default max views")
    default_password_protected: bool = Field(description="Default password protection")
    
    # Default customization
    default_title: Optional[str] = Field(default=None, description="Default title")
    default_message: Optional[str] = Field(default=None, description="Default message")
    default_show_branding: bool = Field(description="Default branding setting")
    
    description: Optional[str] = Field(default=None, description="Template description")
    
    # Usage stats
    usage_count: int = Field(description="Number of times template was used")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")
    
    is_active: bool = Field(description="Whether template is active")