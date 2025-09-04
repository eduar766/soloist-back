"""
Base entity and value objects for the domain layer.
This module contains the foundational classes for all domain entities.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import uuid


class DomainEvent(ABC):
    """Base class for domain events."""
    
    def __init__(self):
        self.occurred_at = datetime.utcnow()
        self.event_id = str(uuid.uuid4())
    
    @property
    @abstractmethod
    def event_name(self) -> str:
        """Return the name of the event."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
            "data": self.__dict__
        }


@dataclass
class BaseEntity(ABC):
    """
    Base class for all domain entities.
    Provides common attributes and behavior for all entities.
    """
    
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Domain events
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize entity after creation."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def __eq__(self, other: Any) -> bool:
        """Entities are equal if they have the same ID and are of the same type."""
        if not isinstance(other, self.__class__):
            return False
        if self.id is None or other.id is None:
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on entity ID."""
        if self.id is None:
            return hash(id(self))
        return hash((self.__class__.__name__, self.id))
    
    def mark_as_updated(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event."""
        self._events.append(event)
    
    def pull_events(self) -> list[DomainEvent]:
        """Get and clear all domain events."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def is_new(self) -> bool:
        """Check if entity is new (not persisted)."""
        return self.id is None
    
    def validate(self) -> None:
        """
        Validate the entity's state.
        Should be overridden by subclasses to implement specific validation rules.
        Raises ValidationError if the entity is in an invalid state.
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, BaseEntity):
                    data[key] = value.to_dict()
                elif isinstance(value, list):
                    data[key] = [
                        item.to_dict() if isinstance(item, BaseEntity) else item
                        for item in value
                    ]
                else:
                    data[key] = value
        return data


@dataclass
class AggregateRoot(BaseEntity):
    """
    Base class for aggregate roots.
    Aggregate roots are the entry points to aggregates and handle domain events.
    """
    
    version: int = field(default=1)
    
    def increment_version(self) -> None:
        """Increment the aggregate version for optimistic locking."""
        self.version += 1
        self.mark_as_updated()


class DomainException(Exception):
    """Base exception for domain errors."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class ValidationError(DomainException):
    """Exception raised when entity validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class BusinessRuleViolation(DomainException):
    """Exception raised when a business rule is violated."""
    
    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_RULE_VIOLATION")


class EntityNotFoundError(DomainException):
    """Exception raised when an entity is not found."""
    
    def __init__(self, entity_type: str, entity_id: Any):
        message = f"{entity_type} with id {entity_id} not found"
        super().__init__(message, "ENTITY_NOT_FOUND")
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateEntityError(DomainException):
    """Exception raised when trying to create a duplicate entity."""
    
    def __init__(self, entity_type: str, field: str, value: Any):
        message = f"{entity_type} with {field}='{value}' already exists"
        super().__init__(message, "DUPLICATE_ENTITY")
        self.entity_type = entity_type
        self.field = field
        self.value = value


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    Base class for value objects.
    Value objects are immutable and are compared by their values.
    """
    
    def __post_init__(self):
        """Validate value object after creation."""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Validate the value object's state."""
        pass


# Common value objects

@dataclass(frozen=True)
class Email(ValueObject):
    """Email value object with validation."""
    
    value: str
    
    def validate(self) -> None:
        """Validate email format."""
        if not self.value:
            raise ValidationError("Email cannot be empty", "email")
        
        # Basic email validation
        if '@' not in self.value or '.' not in self.value.split('@')[1]:
            raise ValidationError(f"Invalid email format: {self.value}", "email")
        
        # Additional validation rules
        if len(self.value) > 255:
            raise ValidationError("Email too long (max 255 characters)", "email")
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def domain(self) -> str:
        """Get the domain part of the email."""
        return self.value.split('@')[1]
    
    @property
    def local(self) -> str:
        """Get the local part of the email."""
        return self.value.split('@')[0]


@dataclass(frozen=True)
class Money(ValueObject):
    """Money value object with currency."""
    
    amount: float
    currency: str = "USD"
    
    def validate(self) -> None:
        """Validate money amount and currency."""
        if self.amount < 0:
            raise ValidationError("Money amount cannot be negative", "amount")
        
        # Validate currency code (ISO 4217)
        valid_currencies = ["USD", "EUR", "CLP", "ARS", "BRL", "MXN", "COP", "PEN"]
        if self.currency not in valid_currencies:
            raise ValidationError(f"Invalid currency code: {self.currency}", "currency")
    
    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"
    
    def __add__(self, other: 'Money') -> 'Money':
        """Add two money values."""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract two money values."""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, factor: float) -> 'Money':
        """Multiply money by a factor."""
        return Money(self.amount * factor, self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "amount": self.amount,
            "currency": self.currency
        }


@dataclass(frozen=True)
class TimeRange(ValueObject):
    """Time range value object."""
    
    start: datetime
    end: Optional[datetime] = None
    
    def validate(self) -> None:
        """Validate time range."""
        if self.end and self.end < self.start:
            raise ValidationError("End time cannot be before start time", "end")
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get duration in seconds."""
        if self.end:
            return int((self.end - self.start).total_seconds())
        return None
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Get duration in minutes."""
        if self.duration_seconds:
            return self.duration_seconds // 60
        return None
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Get duration in hours."""
        if self.duration_seconds:
            return self.duration_seconds / 3600
        return None
    
    @property
    def is_open(self) -> bool:
        """Check if the time range is open (no end time)."""
        return self.end is None
    
    def close(self, end_time: Optional[datetime] = None) -> 'TimeRange':
        """Close the time range with an end time."""
        if not self.is_open:
            raise BusinessRuleViolation("Time range is already closed")
        return TimeRange(self.start, end_time or datetime.utcnow())
    
    def overlaps_with(self, other: 'TimeRange') -> bool:
        """Check if this time range overlaps with another."""
        if self.is_open or other.is_open:
            return True  # Open ranges always potentially overlap
        
        return not (self.end <= other.start or other.end <= self.start)


@dataclass(frozen=True)
class InvoiceNumber(ValueObject):
    """Invoice number value object with format validation."""
    
    prefix: str
    number: int
    suffix: Optional[str] = None
    
    def validate(self) -> None:
        """Validate invoice number format."""
        if self.number <= 0:
            raise ValidationError("Invoice number must be positive", "number")
        
        if self.prefix and len(self.prefix) > 10:
            raise ValidationError("Invoice prefix too long (max 10 characters)", "prefix")
        
        if self.suffix and len(self.suffix) > 10:
            raise ValidationError("Invoice suffix too long (max 10 characters)", "suffix")
    
    def __str__(self) -> str:
        """Format invoice number as string."""
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(str(self.number).zfill(6))  # Pad with zeros
        if self.suffix:
            parts.append(self.suffix)
        return "-".join(parts)
    
    @classmethod
    def from_string(cls, value: str) -> 'InvoiceNumber':
        """Parse invoice number from string."""
        parts = value.split("-")
        if len(parts) == 1:
            return cls("", int(parts[0]))
        elif len(parts) == 2:
            return cls(parts[0], int(parts[1]))
        elif len(parts) == 3:
            return cls(parts[0], int(parts[1]), parts[2])
        else:
            raise ValidationError(f"Invalid invoice number format: {value}")
    
    def next(self) -> 'InvoiceNumber':
        """Get the next invoice number in sequence."""
        return InvoiceNumber(self.prefix, self.number + 1, self.suffix)
