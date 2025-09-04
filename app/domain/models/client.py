"website": self.website
        }


@dataclass
class Client(AggregateRoot):
    """
    Client aggregate root.
    Represents a client/customer that hires the freelancer.
    """
    
    # Required fields
    owner_id: str  # UUID of the freelancer who owns this client
    name: str
    
    # Contact information
    contact: ContactInfo = field(default_factory=ContactInfo)
    
    # Business information
    tax_id: Optional[str] = None
    company_type: Optional[str] = None  # SA, SpA, Ltda, etc.
    industry: Optional[str] = None
    
    # Billing configuration
    default_currency: str = "USD"
    default_hourly_rate: Optional[float] = None
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    custom_payment_terms: Optional[str] = None  # For CUSTOM payment terms
    
    # Additional information
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # System fields
    status: ClientStatus = ClientStatus.ACTIVE
    
    # Statistics (computed fields)
    total_projects: int = 0
    active_projects: int = 0
    total_invoiced: float = 0
    total_paid: float = 0
    outstanding_balance: float = 0
    
    def __post_init__(self):
        """Initialize client after creation."""
        super().__post_init__()
        
        # Validate on creation
        self.validate()
        
        # Add creation event if new
        if self.is_new:
            self.add_event(ClientCreatedEvent(
                client_id=self.id or 0,
                name=self.name,
                owner_id=self.owner_id
            ))
    
    def validate(self) -> None:
        """Validate client state."""
        # Required fields
        if not self.owner_id:
            raise ValidationError("Owner ID is required", "owner_id")
        
        if not self.name:
            raise ValidationError("Client name is required", "name")
        
        if len(self.name) > 255:
            raise ValidationError("Client name too long (max 255 characters)", "name")
        
        # Validate contact info
        if self.contact:
            self.contact.validate()
        
        # Validate tax ID format if provided
        if self.tax_id and len(self.tax_id) > 50:
            raise ValidationError("Tax ID too long (max 50 characters)", "tax_id")
        
        # Validate hourly rate if provided
        if self.default_hourly_rate is not None and self.default_hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative", "default_hourly_rate")
        
        # Validate custom payment terms
        if self.payment_terms == PaymentTerms.CUSTOM and not self.custom_payment_terms:
            raise ValidationError(
                "Custom payment terms description is required when using CUSTOM payment terms",
                "custom_payment_terms"
            )
        
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
        """Check if client is active."""
        return self.status == ClientStatus.ACTIVE
    
    @property
    def is_archived(self) -> bool:
        """Check if client is archived."""
        return self.status == ClientStatus.ARCHIVED
    
    @property
    def has_outstanding_balance(self) -> bool:
        """Check if client has outstanding balance."""
        return self.outstanding_balance > 0
    
    @property
    def payment_terms_days(self) -> int:
        """Get payment terms in days."""
        terms_map = {
            PaymentTerms.IMMEDIATE: 0,
            PaymentTerms.NET_15: 15,
            PaymentTerms.NET_30: 30,
            PaymentTerms.NET_45: 45,
            PaymentTerms.NET_60: 60,
            PaymentTerms.NET_90: 90,
            PaymentTerms.CUSTOM: 30  # Default for custom
        }
        return terms_map.get(self.payment_terms, 30)
    
    @property
    def display_payment_terms(self) -> str:
        """Get display string for payment terms."""
        if self.payment_terms == PaymentTerms.CUSTOM:
            return self.custom_payment_terms or "Custom terms"
        return self.payment_terms.value.replace("_", " ")
    
    def update_info(
        self,
        name: Optional[str] = None,
        contact: Optional[ContactInfo] = None,
        tax_id: Optional[str] = None,
        company_type: Optional[str] = None,
        industry: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """Update client information."""
        if not self.is_active:
            raise BusinessRuleViolation("Cannot update archived client")
        
        changes = {}
        
        if name is not None and name != self.name:
            if not name:
                raise ValidationError("Client name cannot be empty", "name")
            self.name = name
            changes["name"] = name
        
        if contact is not None:
            contact.validate()
            self.contact = contact
            changes["contact"] = contact.to_dict()
        
        if tax_id is not None and tax_id != self.tax_id:
            self.tax_id = tax_id
            changes["tax_id"] = tax_id
        
        if company_type is not None and company_type != self.company_type:
            self.company_type = company_type
            changes["company_type"] = company_type
        
        if industry is not None and industry != self.industry:
            self.industry = industry
            changes["industry"] = industry
        
        if notes is not None and notes != self.notes:
            self.notes = notes
            changes["notes"] = notes
        
        if changes:
            self.validate()
            self.mark_as_updated()
            self.increment_version()
            self.add_event(ClientUpdatedEvent(self.id or 0, changes))
    
    def update_billing_config(
        self,
        currency: Optional[str] = None,
        hourly_rate: Optional[float] = None,
        payment_terms: Optional[PaymentTerms] = None,
        custom_payment_terms: Optional[str] = None
    ) -> None:
        """Update client billing configuration."""
        if not self.is_active:
            raise BusinessRuleViolation("Cannot update billing for archived client")
        
        if currency is not None:
            self.default_currency = currency
        
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise ValidationError("Hourly rate cannot be negative", "hourly_rate")
            self.default_hourly_rate = hourly_rate
        
        if payment_terms is not None:
            self.payment_terms = payment_terms
            
        if custom_payment_terms is not None:
            self.custom_payment_terms = custom_payment_terms
        
        self.validate()
        self.mark_as_updated()
        self.increment_version()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the client."""
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
        """Remove a tag from the client."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.mark_as_updated()
    
    def archive(self, reason: Optional[str] = None) -> None:
        """Archive the client."""
        if self.status == ClientStatus.ARCHIVED:
            raise BusinessRuleViolation("Client is already archived")
        
        if self.active_projects > 0:
            raise BusinessRuleViolation(
                f"Cannot archive client with {self.active_projects} active projects"
            )
        
        if self.has_outstanding_balance:
            raise BusinessRuleViolation(
                f"Cannot archive client with outstanding balance of {self.default_currency} {self.outstanding_balance}"
            )
        
        self.status = ClientStatus.ARCHIVED
        self.mark_as_updated()
        self.increment_version()
        self.add_event(ClientArchivedEvent(self.id or 0, reason))
    
    def reactivate(self) -> None:
        """Reactivate an archived client."""
        if self.status != ClientStatus.ARCHIVED:
            raise BusinessRuleViolation("Only archived clients can be reactivated")
        
        self.status = ClientStatus.ACTIVE
        self.mark_as_updated()
        self.increment_version()
    
    def calculate_credit_limit(self) -> Money:
        """
        Calculate suggested credit limit based on payment history.
        This is a simplified version - real implementation would use payment history.
        """
        if self.total_paid == 0:
            # New client - conservative limit
            return Money(1000, self.default_currency)
        
        # Based on average monthly billing
        average_monthly = self.total_paid / 12  # Simplified
        credit_limit = average_monthly * 2  # 2 months credit
        
        return Money(credit_limit, self.default_currency)
    
    def can_create_project(self) -> bool:
        """Check if a new project can be created for this client."""
        return self.is_active and not self.has_outstanding_balance
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["status"] = self.status.value
        data["payment_terms"] = self.payment_terms.value
        
        # Convert contact info
        data["contact"] = self.contact.to_dict() if self.contact else None
        
        # Add computed display values
        data["payment_terms_days"] = self.payment_terms_days
        data["display_payment_terms"] = self.display_payment_terms
        
        return data"""
Client domain model.
Represents a client/customer in the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from app.domain.models.base import (
    AggregateRoot,
    Email,
    Money,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class ClientStatus(str, Enum):
    """Client status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PaymentTerms(str, Enum):
    """Standard payment terms."""
    IMMEDIATE = "IMMEDIATE"
    NET_15 = "NET_15"
    NET_30 = "NET_30"
    NET_45 = "NET_45"
    NET_60 = "NET_60"
    NET_90 = "NET_90"
    CUSTOM = "CUSTOM"


# Domain Events

class ClientCreatedEvent(DomainEvent):
    """Event raised when a new client is created."""
    
    def __init__(self, client_id: int, name: str, owner_id: str):
        super().__init__()
        self.client_id = client_id
        self.name = name
        self.owner_id = owner_id
    
    @property
    def event_name(self) -> str:
        return "client.created"


class ClientUpdatedEvent(DomainEvent):
    """Event raised when client information is updated."""
    
    def __init__(self, client_id: int, changes: dict):
        super().__init__()
        self.client_id = client_id
        self.changes = changes
    
    @property
    def event_name(self) -> str:
        return "client.updated"


class ClientArchivedEvent(DomainEvent):
    """Event raised when a client is archived."""
    
    def __init__(self, client_id: int, reason: Optional[str] = None):
        super().__init__()
        self.client_id = client_id
        self.reason = reason
    
    @property
    def event_name(self) -> str:
        return "client.archived"


@dataclass
class ContactInfo:
    """Client contact information value object."""
    
    contact_name: Optional[str] = None
    email: Optional[Email] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    
    def __post_init__(self):
        """Convert email string to Email value object if needed."""
        if isinstance(self.email, str):
            self.email = Email(self.email) if self.email else None
    
    def validate(self) -> None:
        """Validate contact information."""
        if self.phone and len(self.phone) > 20:
            raise ValidationError("Phone number too long (max 20 characters)", "phone")
        
        if self.mobile and len(self.mobile) > 20:
            raise ValidationError("Mobile number too long (max 20 characters)", "mobile")
        
        if self.postal_code and len(self.postal_code) > 20:
            raise ValidationError("Postal code too long (max 20 characters)", "postal_code")
        
        if self.website and len(self.website) > 255:
            raise ValidationError("Website URL too long (max 255 characters)", "website")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "contact_name": self.contact_name,
            "email": str(self.email) if self.email else None,
            "phone": self.phone,
            "mobile": self.mobile,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "website": self.website
        }