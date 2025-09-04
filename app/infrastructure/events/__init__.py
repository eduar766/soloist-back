"""
Infrastructure event handlers.
Handles domain events and triggers appropriate notifications.
"""

from .notification_handlers import EmailNotificationHandler, InvoiceNotificationHandler, ProjectNotificationHandler
from .event_setup import setup_event_handlers

__all__ = [
    "EmailNotificationHandler",
    "InvoiceNotificationHandler", 
    "ProjectNotificationHandler",
    "setup_event_handlers"
]