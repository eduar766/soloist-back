"""
User DTOs for the application layer.
Data Transfer Objects for user-related operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, EmailStr, validator

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin
)


# Request DTOs
class CreateUserRequestDTO(CreateRequestDTO):
    """DTO for user creation requests."""
    
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(default=None, max_length=255, description="Full name")
    password: str = Field(min_length=8, max_length=128, description="Password")
    phone: Optional[str] = Field(default=None, max_length=20, description="Phone number")
    company: Optional[str] = Field(default=None, max_length=255, description="Company name")
    position: Optional[str] = Field(default=None, max_length=255, description="Job position")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UpdateUserRequestDTO(UpdateRequestDTO):
    """DTO for user update requests."""
    
    full_name: Optional[str] = Field(default=None, max_length=255, description="Full name")
    phone: Optional[str] = Field(default=None, max_length=20, description="Phone number")
    company: Optional[str] = Field(default=None, max_length=255, description="Company name")
    position: Optional[str] = Field(default=None, max_length=255, description="Job position")
    bio: Optional[str] = Field(default=None, max_length=1000, description="User biography")
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="Avatar URL")


class UpdateUserPreferencesRequestDTO(RequestDTO):
    """DTO for updating user preferences."""
    
    locale: Optional[str] = Field(default=None, max_length=10, description="User locale")
    timezone: Optional[str] = Field(default=None, max_length=50, description="User timezone")
    currency: Optional[str] = Field(default=None, max_length=3, description="Default currency")
    date_format: Optional[str] = Field(default=None, max_length=20, description="Date format preference")
    time_format: Optional[str] = Field(default=None, max_length=10, description="Time format preference")
    notifications_enabled: Optional[bool] = Field(default=None, description="Enable notifications")
    email_notifications: Optional[bool] = Field(default=None, description="Enable email notifications")
    weekly_summary: Optional[bool] = Field(default=None, description="Enable weekly summary emails")


class UpdateBillingInfoRequestDTO(RequestDTO):
    """DTO for updating user billing information."""
    
    hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    currency: Optional[str] = Field(default=None, max_length=3, description="Default currency")
    tax_id: Optional[str] = Field(default=None, max_length=50, description="Tax ID")
    billing_address: Optional[str] = Field(default=None, max_length=500, description="Billing address")


class ChangePasswordRequestDTO(RequestDTO):
    """DTO for password change requests."""
    
    current_password: str = Field(description="Current password")
    new_password: str = Field(min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class ListUsersRequestDTO(FilterRequestDTO):
    """DTO for listing users with filters."""
    
    role: Optional[str] = Field(default=None, description="Filter by user role")
    status: Optional[str] = Field(default=None, description="Filter by user status")
    company: Optional[str] = Field(default=None, description="Filter by company")


# Response DTOs
class UserPreferencesResponseDTO(ResponseDTO):
    """DTO for user preferences response."""
    
    locale: str = Field(description="User locale")
    timezone: str = Field(description="User timezone")
    currency: str = Field(description="Default currency")
    date_format: str = Field(description="Date format preference")
    time_format: str = Field(description="Time format preference")
    notifications_enabled: bool = Field(description="Notifications enabled")
    email_notifications: bool = Field(description="Email notifications enabled")
    weekly_summary: bool = Field(description="Weekly summary enabled")


class UserStatsResponseDTO(ResponseDTO):
    """DTO for user statistics response."""
    
    total_projects: int = Field(description="Total number of projects")
    active_projects: int = Field(description="Number of active projects")
    total_clients: int = Field(description="Total number of clients")
    total_hours_tracked: float = Field(description="Total hours tracked")
    total_revenue: float = Field(description="Total revenue generated")
    hours_this_week: float = Field(description="Hours tracked this week")
    hours_this_month: float = Field(description="Hours tracked this month")
    avg_hourly_rate: Optional[float] = Field(default=None, description="Average hourly rate")


class UserResponseDTO(ResponseDTO, TimestampMixin):
    """DTO for user response."""
    
    user_id: str = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(default=None, description="Full name")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL")
    phone: Optional[str] = Field(default=None, description="Phone number")
    company: Optional[str] = Field(default=None, description="Company name")
    position: Optional[str] = Field(default=None, description="Job position")
    bio: Optional[str] = Field(default=None, description="User biography")
    
    # System fields
    role: str = Field(description="User role")
    status: str = Field(description="User status")
    email_verified: bool = Field(description="Email verified status")
    email_verified_at: Optional[datetime] = Field(default=None, description="Email verification timestamp")
    last_sign_in_at: Optional[datetime] = Field(default=None, description="Last sign in timestamp")
    
    # Preferences
    preferences: UserPreferencesResponseDTO = Field(description="User preferences")
    
    # Billing info (only for freelancers)
    default_hourly_rate: Optional[float] = Field(default=None, description="Default hourly rate")
    default_currency: str = Field(description="Default currency")
    tax_id: Optional[str] = Field(default=None, description="Tax ID")
    billing_address: Optional[str] = Field(default=None, description="Billing address")
    
    # Statistics
    stats: Optional[UserStatsResponseDTO] = Field(default=None, description="User statistics")


class UserProfileResponseDTO(ResponseDTO):
    """DTO for public user profile response."""
    
    user_id: str = Field(description="User ID")
    full_name: Optional[str] = Field(default=None, description="Full name")
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL")
    company: Optional[str] = Field(default=None, description="Company name")
    position: Optional[str] = Field(default=None, description="Job position")
    bio: Optional[str] = Field(default=None, description="User biography")


class AuthUserResponseDTO(ResponseDTO):
    """DTO for authenticated user response."""
    
    user: UserResponseDTO = Field(description="User information")
    access_token: str = Field(description="JWT access token")
    refresh_token: Optional[str] = Field(default=None, description="JWT refresh token")
    expires_at: datetime = Field(description="Token expiration time")
    token_type: str = Field(default="bearer", description="Token type")


# Authentication DTOs
class LoginRequestDTO(RequestDTO):
    """DTO for login requests."""
    
    email: EmailStr = Field(description="User email")
    password: str = Field(description="User password")
    remember_me: bool = Field(default=False, description="Remember login")


class RegisterRequestDTO(CreateUserRequestDTO):
    """DTO for user registration requests."""
    
    confirm_password: str = Field(description="Confirm password")
    terms_accepted: bool = Field(description="Terms and conditions accepted")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('terms_accepted')
    def terms_must_be_accepted(cls, v):
        """Validate that terms are accepted."""
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class RefreshTokenRequestDTO(RequestDTO):
    """DTO for token refresh requests."""
    
    refresh_token: str = Field(description="Refresh token")


class ForgotPasswordRequestDTO(RequestDTO):
    """DTO for forgot password requests."""
    
    email: EmailStr = Field(description="User email")


class ResetPasswordRequestDTO(RequestDTO):
    """DTO for password reset requests."""
    
    token: str = Field(description="Password reset token")
    new_password: str = Field(min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class VerifyEmailRequestDTO(RequestDTO):
    """DTO for email verification requests."""
    
    token: str = Field(description="Email verification token")


# Activity and Analytics DTOs
class UserActivityResponseDTO(ResponseDTO):
    """DTO for user activity response."""
    
    date: datetime = Field(description="Activity date")
    activity_type: str = Field(description="Type of activity")
    description: str = Field(description="Activity description")
    project_id: Optional[int] = Field(default=None, description="Related project ID")
    task_id: Optional[int] = Field(default=None, description="Related task ID")


class UserProductivityResponseDTO(ResponseDTO):
    """DTO for user productivity metrics."""
    
    period_start: datetime = Field(description="Period start date")
    period_end: datetime = Field(description="Period end date")
    total_hours: float = Field(description="Total hours worked")
    billable_hours: float = Field(description="Billable hours")
    productivity_score: float = Field(description="Productivity score (0-100)")
    avg_session_length: float = Field(description="Average session length in hours")
    most_productive_hours: List[int] = Field(description="Most productive hours of day")
    daily_breakdown: List[Dict[str, Any]] = Field(description="Daily breakdown of hours")
    project_breakdown: List[Dict[str, Any]] = Field(description="Breakdown by project")


class UserTimeTrackingStatsDTO(ResponseDTO):
    """DTO for user time tracking statistics."""
    
    today_hours: float = Field(description="Hours tracked today")
    week_hours: float = Field(description="Hours tracked this week")
    month_hours: float = Field(description="Hours tracked this month")
    running_timers: int = Field(description="Number of running timers")
    pending_entries: int = Field(description="Number of pending approval entries")
    recent_projects: List[Dict[str, Any]] = Field(description="Recently worked on projects")
    time_distribution: Dict[str, float] = Field(description="Time distribution by project")