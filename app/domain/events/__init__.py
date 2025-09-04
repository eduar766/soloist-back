"""
Domain events for the application.
Event-driven architecture components for notifications and business logic.
"""

from .base import DomainEvent, EventHandler, EventDispatcher
from .invoice_events import InvoiceCreated, InvoicePaid, InvoiceOverdue
from .project_events import ProjectCreated, ProjectCompleted, ProjectStatusChanged
from .client_events import ClientRegistered, ClientUpdated
from .time_entry_events import TimeEntryCreated, WeeklyTimeReport

__all__ = [
    "DomainEvent",
    "EventHandler", 
    "EventDispatcher",
    "InvoiceCreated",
    "InvoicePaid",
    "InvoiceOverdue",
    "ProjectCreated",
    "ProjectCompleted",
    "ProjectStatusChanged",
    "ClientRegistered",
    "ClientUpdated",
    "TimeEntryCreated",
    "WeeklyTimeReport"
]