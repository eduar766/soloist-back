"""
Domain models for the freelancer management system.
This module exports all domain entities and value objects.
"""

# Base classes
from .base import (
    BaseEntity,
    AggregateRoot,
    DomainEvent,
    DomainException,
    ValidationError,
    BusinessRuleViolation,
    EntityNotFoundError,
    DuplicateEntityError,
    ValueObject
)

# Value Objects
from .value_objects import (
    Money,
    Currency,
    TimeRange,
    InvoiceNumber,
    Email,
    PhoneNumber,
    Address
)

# Domain entities
from .user import (
    User,
    UserRole,
    UserStatus,
    UserPreferences,
    UserCreatedEvent,
    UserProfileUpdatedEvent,
    UserDeactivatedEvent
)

from .client import (
    Client,
    ClientStatus,
    PaymentTerms,
    ContactInfo,
    ClientCreatedEvent,
    ClientUpdatedEvent,
    ClientArchivedEvent
)

from .project import (
    Project,
    ProjectStatus,
    ProjectType,
    ProjectRole,
    BillingType,
    BillingConfiguration,
    ProjectMember,
    ProjectCreatedEvent,
    ProjectStatusChangedEvent,
    ProjectMemberAddedEvent,
    ProjectCompletedEvent
)

from .task import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskComment,
    TaskAttachment,
    TaskCreatedEvent,
    TaskStatusChangedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent
)

from .time_entry import (
    TimeEntry,
    TimeEntryStatus,
    TimeEntryType,
    TimeEntryStartedEvent,
    TimeEntryStoppedEvent,
    TimeEntryApprovedEvent,
    TimeEntryInvoicedEvent
)

from .invoice import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    PaymentStatus,
    PaymentMethod,
    InvoiceLineItem,
    TaxLineItem,
    PaymentRecord,
    InvoiceSettings,
    InvoiceCreatedEvent,
    InvoiceSentEvent,
    InvoicePaidEvent,
    InvoiceOverdueEvent
)

from .share import (
    Share,
    ShareableType,
    ShareType,
    ShareStatus,
    ShareAccess,
    SharePermissions,
    ShareCreatedEvent,
    ShareAccessedEvent,
    ShareRevokedEvent
)

__all__ = [
    # Base classes
    "BaseEntity",
    "AggregateRoot",
    "DomainEvent",
    "DomainException",
    "ValidationError",
    "BusinessRuleViolation",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "ValueObject",
    "Email",
    "Money",
    "TimeRange",
    "InvoiceNumber",
    
    # User
    "User",
    "UserRole",
    "UserStatus",
    "UserPreferences",
    "UserCreatedEvent",
    "UserProfileUpdatedEvent",
    "UserDeactivatedEvent",
    
    # Client
    "Client",
    "ClientStatus",
    "PaymentTerms",
    "ContactInfo",
    "ClientCreatedEvent",
    "ClientUpdatedEvent",
    "ClientArchivedEvent",
    
    # Project
    "Project",
    "ProjectStatus",
    "ProjectType",
    "ProjectRole",
    "BillingType",
    "BillingConfiguration",
    "ProjectMember",
    "ProjectCreatedEvent",
    "ProjectStatusChangedEvent",
    "ProjectMemberAddedEvent",
    "ProjectCompletedEvent",
    
    # Task
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "TaskComment",
    "TaskAttachment",
    "TaskCreatedEvent",
    "TaskStatusChangedEvent",
    "TaskAssignedEvent",
    "TaskCompletedEvent",
    
    # TimeEntry
    "TimeEntry",
    "TimeEntryStatus",
    "TimeEntryType",
    "TimeEntryStartedEvent",
    "TimeEntryStoppedEvent",
    "TimeEntryApprovedEvent",
    "TimeEntryInvoicedEvent",
    
    # Invoice
    "Invoice",
    "InvoiceStatus",
    "InvoiceType",
    "PaymentStatus",
    "PaymentMethod",
    "InvoiceLineItem",
    "TaxLineItem",
    "PaymentRecord",
    "InvoiceSettings",
    "InvoiceCreatedEvent",
    "InvoiceSentEvent",
    "InvoicePaidEvent",
    "InvoiceOverdueEvent",
    
    # Share
    "Share",
    "ShareableType",
    "ShareType",
    "ShareStatus",
    "ShareAccess",
    "SharePermissions",
    "ShareCreatedEvent",
    "ShareAccessedEvent",
    "ShareRevokedEvent",
]