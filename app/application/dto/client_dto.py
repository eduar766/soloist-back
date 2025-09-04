"""
Client DTOs for the application layer.
Data Transfer Objects for client-related operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, EmailStr, validator

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin, TagsMixin, NotesMixin
)
from app.infrastructure.validation.validators import (
    SecurityValidator, DataValidator, BusinessValidator
)


# Nested DTOs
class ContactInfoRequestDTO(RequestDTO):
    """DTO for contact information in requests."""
    
    contact_name: Optional[str] = Field(default=None, max_length=255, description="Contact person name")
    email: Optional[str] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, max_length=20, description="Phone number")
    mobile: Optional[str] = Field(default=None, max_length=20, description="Mobile number")
    address: Optional[str] = Field(default=None, max_length=500, description="Address")
    city: Optional[str] = Field(default=None, max_length=100, description="City")
    state: Optional[str] = Field(default=None, max_length=100, description="State/Province")
    country: Optional[str] = Field(default=None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(default=None, max_length=20, description="Postal code")
    website: Optional[str] = Field(default=None, max_length=255, description="Website URL")
    
    @validator('contact_name', 'address', 'city', 'state', 'country', pre=True)
    def validate_safe_strings(cls, v):
        if v is not None:
            SecurityValidator.check_sql_injection(v)
            SecurityValidator.check_xss(v)
        return v
    
    @validator('email', pre=True)
    def validate_email(cls, v):
        if v is not None:
            return DataValidator.validate_email(v)
        return v
    
    @validator('phone', 'mobile', pre=True)
    def validate_phone(cls, v):
        if v is not None:
            return DataValidator.validate_phone(v, region='US')
        return v
    
    @validator('postal_code', pre=True)
    def validate_postal_code(cls, v):
        if v is not None:
            return DataValidator.validate_postal_code(v)
        return v
    
    @validator('website', pre=True)
    def validate_website(cls, v):
        if v is not None:
            return DataValidator.validate_url(v)
        return v


class ContactInfoResponseDTO(ResponseDTO):
    """DTO for contact information in responses."""
    
    contact_name: Optional[str] = Field(default=None, description="Contact person name")
    email: Optional[str] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, description="Phone number")
    mobile: Optional[str] = Field(default=None, description="Mobile number")
    address: Optional[str] = Field(default=None, description="Address")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State/Province")
    country: Optional[str] = Field(default=None, description="Country")
    postal_code: Optional[str] = Field(default=None, description="Postal code")
    website: Optional[str] = Field(default=None, description="Website URL")


# Request DTOs
class CreateClientRequestDTO(CreateRequestDTO, TagsMixin, NotesMixin):
    """DTO for client creation requests."""
    
    name: str = Field(min_length=1, max_length=255, description="Client name")
    contact: Optional[ContactInfoRequestDTO] = Field(default=None, description="Contact information")
    
    # Business information
    tax_id: Optional[str] = Field(default=None, max_length=50, description="Tax ID")
    company_type: Optional[str] = Field(default=None, max_length=50, description="Company type")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry")
    
    # Billing configuration
    default_currency: str = Field(default="USD", max_length=3, description="Default currency")
    default_hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    payment_terms: str = Field(default="NET_30", description="Payment terms")
    custom_payment_terms: Optional[str] = Field(default=None, max_length=255, description="Custom payment terms")
    
    @validator('name', pre=True)
    def validate_name(cls, v):
        return BusinessValidator.validate_client_name(v)
    
    @validator('tax_id', pre=True)
    def validate_tax_id(cls, v):
        if v is not None:
            return DataValidator.validate_tax_id(v)
        return v
    
    @validator('company_type', 'industry', 'custom_payment_terms', pre=True)
    def validate_safe_strings(cls, v):
        if v is not None:
            SecurityValidator.check_sql_injection(v)
            SecurityValidator.check_xss(v)
        return v
    
    @validator('default_currency', pre=True)
    def validate_currency(cls, v):
        return DataValidator.validate_currency_code(v)
    
    @validator('default_hourly_rate', pre=True)
    def validate_hourly_rate(cls, v):
        if v is not None:
            return BusinessValidator.validate_hourly_rate(v)
        return v
    
    @validator('payment_terms')
    def validate_payment_terms(cls, v, values):
        """Validate payment terms."""
        valid_terms = ["IMMEDIATE", "NET_15", "NET_30", "NET_45", "NET_60", "NET_90", "CUSTOM"]
        if v not in valid_terms:
            raise ValueError(f'Payment terms must be one of: {", ".join(valid_terms)}')
        
        if v == "CUSTOM" and not values.get('custom_payment_terms'):
            raise ValueError('Custom payment terms description is required when using CUSTOM payment terms')
        
        return v


class UpdateClientRequestDTO(UpdateRequestDTO, TagsMixin, NotesMixin):
    """DTO for client update requests."""
    
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Client name")
    contact: Optional[ContactInfoRequestDTO] = Field(default=None, description="Contact information")
    
    # Business information
    tax_id: Optional[str] = Field(default=None, max_length=50, description="Tax ID")
    company_type: Optional[str] = Field(default=None, max_length=50, description="Company type")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry")
    
    # Billing configuration
    default_currency: Optional[str] = Field(default=None, max_length=3, description="Default currency")
    default_hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    custom_payment_terms: Optional[str] = Field(default=None, max_length=255, description="Custom payment terms")
    
    @validator('payment_terms')
    def validate_payment_terms(cls, v, values):
        """Validate payment terms."""
        if v is None:
            return v
            
        valid_terms = ["IMMEDIATE", "NET_15", "NET_30", "NET_45", "NET_60", "NET_90", "CUSTOM"]
        if v not in valid_terms:
            raise ValueError(f'Payment terms must be one of: {", ".join(valid_terms)}')
        
        return v


class UpdateClientBillingRequestDTO(RequestDTO):
    """DTO for updating client billing configuration."""
    
    default_currency: Optional[str] = Field(default=None, max_length=3, description="Default currency")
    default_hourly_rate: Optional[float] = Field(default=None, ge=0, description="Default hourly rate")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    custom_payment_terms: Optional[str] = Field(default=None, max_length=255, description="Custom payment terms")


class ListClientsRequestDTO(FilterRequestDTO, TagsMixin):
    """DTO for listing clients with filters."""
    
    status: Optional[str] = Field(default=None, description="Filter by client status")
    payment_terms: Optional[str] = Field(default=None, description="Filter by payment terms")
    industry: Optional[str] = Field(default=None, description="Filter by industry")
    has_outstanding_balance: Optional[bool] = Field(default=None, description="Filter by outstanding balance")
    has_active_projects: Optional[bool] = Field(default=None, description="Filter by active projects")


class SearchClientsRequestDTO(ListClientsRequestDTO):
    """DTO for searching clients."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")


# Response DTOs
class ClientStatsResponseDTO(ResponseDTO):
    """DTO for client statistics."""
    
    total_projects: int = Field(description="Total number of projects")
    active_projects: int = Field(description="Number of active projects")
    total_invoiced: float = Field(description="Total amount invoiced")
    total_paid: float = Field(description="Total amount paid")
    outstanding_balance: float = Field(description="Outstanding balance")
    avg_payment_time_days: Optional[float] = Field(default=None, description="Average payment time in days")
    last_project_date: Optional[datetime] = Field(default=None, description="Date of last project")
    last_payment_date: Optional[datetime] = Field(default=None, description="Date of last payment")


class ClientResponseDTO(ResponseDTO, TimestampMixin, TagsMixin, NotesMixin):
    """DTO for client response."""
    
    owner_id: str = Field(description="Owner user ID")
    name: str = Field(description="Client name")
    contact: Optional[ContactInfoResponseDTO] = Field(default=None, description="Contact information")
    
    # Business information
    tax_id: Optional[str] = Field(default=None, description="Tax ID")
    company_type: Optional[str] = Field(default=None, description="Company type")
    industry: Optional[str] = Field(default=None, description="Industry")
    
    # Billing configuration
    default_currency: str = Field(description="Default currency")
    default_hourly_rate: Optional[float] = Field(default=None, description="Default hourly rate")
    payment_terms: str = Field(description="Payment terms")
    payment_terms_days: int = Field(description="Payment terms in days")
    display_payment_terms: str = Field(description="Human-readable payment terms")
    custom_payment_terms: Optional[str] = Field(default=None, description="Custom payment terms")
    
    # System fields
    status: str = Field(description="Client status")
    
    # Statistics
    stats: Optional[ClientStatsResponseDTO] = Field(default=None, description="Client statistics")
    
    # Computed fields
    is_active: bool = Field(description="Whether client is active")
    is_archived: bool = Field(description="Whether client is archived")
    has_outstanding_balance: bool = Field(description="Whether client has outstanding balance")
    can_create_project: bool = Field(description="Whether new projects can be created")


class ClientSummaryResponseDTO(ResponseDTO):
    """DTO for client summary (used in lists)."""
    
    name: str = Field(description="Client name")
    status: str = Field(description="Client status")
    default_currency: str = Field(description="Default currency")
    total_projects: int = Field(description="Total number of projects")
    active_projects: int = Field(description="Number of active projects")
    outstanding_balance: float = Field(description="Outstanding balance")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity date")
    contact_email: Optional[str] = Field(default=None, description="Primary contact email")


class ClientActivityResponseDTO(ResponseDTO):
    """DTO for client activity response."""
    
    date: datetime = Field(description="Activity date")
    activity_type: str = Field(description="Type of activity")
    description: str = Field(description="Activity description")
    project_id: Optional[int] = Field(default=None, description="Related project ID")
    project_name: Optional[str] = Field(default=None, description="Related project name")
    amount: Optional[float] = Field(default=None, description="Related amount (if financial)")


class ClientRevenueResponseDTO(ResponseDTO):
    """DTO for client revenue breakdown."""
    
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    period_start: datetime = Field(description="Period start date")
    period_end: datetime = Field(description="Period end date")
    total_revenue: float = Field(description="Total revenue for period")
    invoice_count: int = Field(description="Number of invoices")
    avg_invoice_amount: float = Field(description="Average invoice amount")
    hours_billed: float = Field(description="Total hours billed")
    avg_hourly_rate: Optional[float] = Field(default=None, description="Average hourly rate")


# Bulk operation DTOs
class BulkUpdateClientsRequestDTO(RequestDTO):
    """DTO for bulk client updates."""
    
    client_ids: List[int] = Field(min_items=1, max_items=100, description="List of client IDs")
    payment_terms: Optional[str] = Field(default=None, description="New payment terms")
    status: Optional[str] = Field(default=None, description="New status")
    tags_to_add: Optional[List[str]] = Field(default=None, description="Tags to add")
    tags_to_remove: Optional[List[str]] = Field(default=None, description="Tags to remove")


class ArchiveClientRequestDTO(RequestDTO):
    """DTO for archiving a client."""
    
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for archiving")


# Analytics DTOs
class ClientAnalyticsResponseDTO(ResponseDTO):
    """DTO for client analytics."""
    
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    
    # Financial metrics
    total_revenue: float = Field(description="Total revenue")
    revenue_trend: List[Dict[str, Any]] = Field(description="Revenue trend over time")
    avg_project_value: float = Field(description="Average project value")
    payment_behavior: Dict[str, Any] = Field(description="Payment behavior metrics")
    
    # Project metrics
    project_count: int = Field(description="Total project count")
    project_success_rate: float = Field(description="Project success rate percentage")
    avg_project_duration: Optional[float] = Field(default=None, description="Average project duration in days")
    
    # Time metrics
    total_hours: float = Field(description="Total hours worked")
    billable_hours: float = Field(description="Total billable hours")
    avg_hourly_rate: Optional[float] = Field(default=None, description="Average hourly rate")
    
    # Relationship metrics
    relationship_duration_days: int = Field(description="Days since first project")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity date")
    communication_frequency: str = Field(description="Communication frequency (high/medium/low)")


class ClientHealthScoreResponseDTO(ResponseDTO):
    """DTO for client health score."""
    
    client_id: int = Field(description="Client ID")
    health_score: float = Field(description="Health score (0-100)")
    risk_level: str = Field(description="Risk level (low/medium/high)")
    
    # Score components
    payment_score: float = Field(description="Payment behavior score")
    activity_score: float = Field(description="Recent activity score")
    revenue_score: float = Field(description="Revenue contribution score")
    
    # Recommendations
    recommendations: List[str] = Field(description="Recommendations for improving relationship")
    warning_signs: List[str] = Field(description="Warning signs to watch for")
    
    last_calculated: datetime = Field(description="When score was calculated")