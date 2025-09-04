"""
Event system setup and configuration.
Registers all event handlers with the event dispatcher.
"""

import logging
from app.domain.events.base import get_event_dispatcher
from .notification_handlers import (
    EmailNotificationHandler,
    InvoiceNotificationHandler,
    ProjectNotificationHandler,
    TimeTrackingNotificationHandler
)

logger = logging.getLogger(__name__)


def setup_event_handlers():
    """Set up and register all event handlers."""
    
    dispatcher = get_event_dispatcher()
    
    # Register notification handlers
    email_handler = EmailNotificationHandler()
    invoice_handler = InvoiceNotificationHandler()
    project_handler = ProjectNotificationHandler()
    time_handler = TimeTrackingNotificationHandler()
    
    # Register global handler for logging
    dispatcher.register_global_handler(email_handler)
    
    # Register specific handlers for invoice events
    dispatcher.register_handler("InvoiceCreated", invoice_handler)
    dispatcher.register_handler("InvoiceSent", invoice_handler)
    dispatcher.register_handler("InvoicePaid", invoice_handler)
    dispatcher.register_handler("InvoiceOverdue", invoice_handler)
    dispatcher.register_handler("InvoiceCancelled", invoice_handler)
    
    # Register specific handlers for project events
    dispatcher.register_handler("ProjectCreated", project_handler)
    dispatcher.register_handler("ProjectStatusChanged", project_handler)
    dispatcher.register_handler("ProjectCompleted", project_handler)
    dispatcher.register_handler("ProjectMilestoneCompleted", project_handler)
    dispatcher.register_handler("ProjectDeadlineApproaching", project_handler)
    dispatcher.register_handler("ProjectBudgetExceeded", project_handler)
    
    # Register specific handlers for time tracking events
    dispatcher.register_handler("WeeklyTimeReport", time_handler)
    dispatcher.register_handler("MonthlyTimeReport", time_handler)
    dispatcher.register_handler("TimeEntryCreated", time_handler)
    dispatcher.register_handler("TimeEntryApproved", time_handler)
    dispatcher.register_handler("LongTimeEntryDetected", time_handler)
    
    logger.info("Event handlers registered successfully")
    
    # Log registered handlers
    registered = dispatcher.get_registered_handlers()
    for event_type, handlers in registered.items():
        logger.info(f"Event {event_type}: {', '.join(handlers)} handlers")


def initialize_event_system():
    """Initialize the complete event system."""
    try:
        setup_event_handlers()
        logger.info("Event system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize event system: {str(e)}")
        raise