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