"""
Client domain model and related entities.
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class ClientStatus(str, Enum):
    """Client status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PaymentTerms(str, Enum):
    """Payment terms enumeration."""
    IMMEDIATE = "immediate"
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_60 = "net_60"
    NET_90 = "net_90"
    CUSTOM = "custom"


@dataclass
class ContactInfo:
    """Contact information for a client."""
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None


from datetime import datetime
from decimal import Decimal
from .base import BaseEntity


class Client(BaseEntity):
    """Client domain entity."""
    
    def __init__(
        self,
        name: str,
        owner_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        contact_info: Optional[ContactInfo] = None,
        status: ClientStatus = ClientStatus.ACTIVE,
        payment_terms: PaymentTerms = PaymentTerms.NET_30,
        default_currency: str = "USD",
        default_hourly_rate: Optional[Decimal] = None,
        tax_id: Optional[str] = None,
        logo_url: Optional[str] = None,
        notes: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name
        self.owner_id = owner_id
        self.email = email
        self.phone = phone
        self.company = company
        self.contact_info = contact_info or ContactInfo()
        self.status = status
        self.payment_terms = payment_terms
        self.default_currency = default_currency
        self.default_hourly_rate = default_hourly_rate
        self.tax_id = tax_id
        self.logo_url = logo_url
        self.notes = notes
        
        # Validate required fields
        if not name or not name.strip():
            raise ValueError("Client name is required")
        if not owner_id or not owner_id.strip():
            raise ValueError("Owner ID is required")
    
    @classmethod
    def create(
        cls,
        name: str,
        owner_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        contact_info: Optional[ContactInfo] = None,
        status: ClientStatus = ClientStatus.ACTIVE,
        payment_terms: PaymentTerms = PaymentTerms.NET_30,
        default_currency: str = "USD",
        default_hourly_rate: Optional[Decimal] = None,
        tax_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> "Client":
        """Create a new client."""
        return cls(
            name=name,
            owner_id=owner_id,
            email=email,
            phone=phone,
            company=company,
            contact_info=contact_info,
            status=status,
            payment_terms=payment_terms,
            default_currency=default_currency,
            default_hourly_rate=default_hourly_rate,
            tax_id=tax_id,
            notes=notes
        )
    
    def update_info(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        contact_info: Optional[ContactInfo] = None,
        payment_terms: Optional[PaymentTerms] = None,
        default_currency: Optional[str] = None,
        default_hourly_rate: Optional[Decimal] = None,
        tax_id: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Update client information."""
        if name is not None:
            if not name.strip():
                raise ValueError("Client name cannot be empty")
            self.name = name
        if email is not None:
            self.email = email
        if phone is not None:
            self.phone = phone
        if company is not None:
            self.company = company
        if contact_info is not None:
            self.contact_info = contact_info
        if payment_terms is not None:
            self.payment_terms = payment_terms
        if default_currency is not None:
            self.default_currency = default_currency
        if default_hourly_rate is not None:
            self.default_hourly_rate = default_hourly_rate
        if tax_id is not None:
            self.tax_id = tax_id
        if notes is not None:
            self.notes = notes
        
        self.updated_at = datetime.now()
    
    def set_logo(self, logo_url: str):
        """Set client logo URL."""
        self.logo_url = logo_url
        self.updated_at = datetime.now()
    
    def activate(self):
        """Activate the client."""
        self.status = ClientStatus.ACTIVE
        self.updated_at = datetime.now()
    
    def deactivate(self):
        """Deactivate the client."""
        self.status = ClientStatus.INACTIVE
        self.updated_at = datetime.now()
    
    def archive(self):
        """Archive the client."""
        self.status = ClientStatus.ARCHIVED
        self.updated_at = datetime.now()
    
    def is_active(self) -> bool:
        """Check if client is active."""
        return self.status == ClientStatus.ACTIVE
    
    def get_display_name(self) -> str:
        """Get display name for the client."""
        if self.company:
            return f"{self.company} ({self.name})"
        return self.name
    
    def __str__(self) -> str:
        return f"Client(id={self.id}, name='{self.name}', company='{self.company}')"
    
    def __repr__(self) -> str:
        return self.__str__()


# Domain Events
from .base import DomainEvent


class ClientCreatedEvent(DomainEvent):
    """Event fired when a new client is created."""
    
    def __init__(self, client: Client):
        super().__init__()
        self.client_id = client.id
        self.owner_id = client.owner_id
        self.client_name = client.name
        self.client_email = client.email


class ClientUpdatedEvent(DomainEvent):
    """Event fired when a client is updated."""
    
    def __init__(self, client: Client, updated_fields: List[str]):
        super().__init__()
        self.client_id = client.id
        self.owner_id = client.owner_id
        self.client_name = client.name
        self.updated_fields = updated_fields


class ClientArchivedEvent(DomainEvent):
    """Event fired when a client is archived."""
    
    def __init__(self, client: Client):
        super().__init__()
        self.client_id = client.id
        self.owner_id = client.owner_id
        self.client_name = client.name