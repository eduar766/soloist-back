"""
Event handlers for email notifications.
Converts domain events into email notifications.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from app.domain.events.base import EventHandler, DomainEvent
from app.domain.events.invoice_events import InvoiceCreated, InvoicePaid, InvoiceSent, InvoiceOverdue
from app.domain.events.project_events import ProjectCreated, ProjectCompleted, ProjectStatusChanged, ProjectDeadlineApproaching
from app.domain.events.client_events import ClientRegistered
from app.domain.events.time_entry_events import WeeklyTimeReport, MonthlyTimeReport

from app.infrastructure.email import get_email_service
from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
from app.infrastructure.repositories.project_repository import SQLAlchemyProjectRepository 
from app.infrastructure.repositories.invoice_repository import SQLAlchemyInvoiceRepository
from app.infrastructure.db.database import get_db_session


logger = logging.getLogger(__name__)


class EmailNotificationHandler(EventHandler):
    """Base handler for email notifications."""
    
    def __init__(self):
        """Initialize email notification handler."""
        self.email_service = get_email_service()
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process the given event."""
        return True  # Base handler can process any event for logging
    
    async def handle(self, event: DomainEvent) -> None:
        """Log all events for debugging."""
        logger.info(f"Email handler received event: {event.event_type} (ID: {event.event_id})")


class InvoiceNotificationHandler(EventHandler):
    """Handler for invoice-related notifications."""
    
    def __init__(self):
        """Initialize invoice notification handler."""
        self.email_service = get_email_service()
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process invoice events."""
        return isinstance(event, (InvoiceCreated, InvoicePaid, InvoiceSent, InvoiceOverdue))
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle invoice events and send appropriate notifications."""
        try:
            if isinstance(event, InvoiceSent):
                await self._handle_invoice_sent(event)
            elif isinstance(event, InvoicePaid):
                await self._handle_invoice_paid(event)
            elif isinstance(event, InvoiceOverdue):
                await self._handle_invoice_overdue(event)
            elif isinstance(event, InvoiceCreated):
                await self._handle_invoice_created(event)
                
        except Exception as e:
            logger.error(f"Error handling invoice event {event.event_type}: {str(e)}")
    
    async def _handle_invoice_sent(self, event: InvoiceSent) -> None:
        """Send invoice notification to client."""
        try:
            # Get client and invoice data
            session = next(get_db_session())
            client_repo = SQLAlchemyClientRepository(session)
            invoice_repo = SQLAlchemyInvoiceRepository(session)
            
            client = await client_repo.find_by_id(event.client_id)
            invoice = await invoice_repo.find_by_id(event.invoice_id)
            
            if not client or not client.email or not invoice:
                logger.warning(f"Cannot send invoice notification: missing data for event {event.event_id}")
                return
            
            # Prepare invoice data
            invoice_data = {
                "invoice_number": invoice.invoice_number,
                "issue_date": invoice.issue_date,
                "due_date": invoice.due_date,
                "status": invoice.status,
                "subtotal": invoice.subtotal,
                "tax_amount": invoice.tax_amount,
                "tax_rate": invoice.tax_rate,
                "total_amount": invoice.total_amount,
                "currency": invoice.currency,
                "payment_instructions": invoice.notes,
                "items": []  # Would need to get from invoice items
            }
            
            # Send notification
            result = await self.email_service.send_invoice_notification(
                client_email=client.email,
                client_name=client.name,
                invoice_data=invoice_data
            )
            
            if result.get("success"):
                logger.info(f"Invoice notification sent successfully to {client.email}")
            else:
                logger.error(f"Failed to send invoice notification: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error sending invoice notification: {str(e)}")
    
    async def _handle_invoice_paid(self, event: InvoicePaid) -> None:
        """Send payment received confirmation."""
        try:
            # Get client data
            session = next(get_db_session())
            client_repo = SQLAlchemyClientRepository(session)
            
            client = await client_repo.find_by_id(event.client_id)
            
            if not client or not client.email:
                logger.warning(f"Cannot send payment confirmation: missing client email for event {event.event_id}")
                return
            
            # Prepare payment data
            payment_data = {
                "invoice_number": event.invoice_number,
                "amount": event.amount_paid,
                "currency": event.currency,
                "payment_method": event.payment_method,
                "payment_date": event.payment_date or datetime.now(),
                "transaction_id": event.transaction_id
            }
            
            # Send confirmation
            result = await self.email_service.send_payment_received_notification(
                client_email=client.email,
                client_name=client.name,
                payment_data=payment_data
            )
            
            if result.get("success"):
                logger.info(f"Payment confirmation sent to {client.email}")
            else:
                logger.error(f"Failed to send payment confirmation: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")
    
    async def _handle_invoice_overdue(self, event: InvoiceOverdue) -> None:
        """Send overdue invoice reminder."""
        try:
            # Get client data  
            session = next(get_db_session())
            client_repo = SQLAlchemyClientRepository(session)
            
            client = await client_repo.find_by_id(event.client_id)
            
            if not client or not client.email:
                logger.warning(f"Cannot send overdue reminder: missing client email for event {event.event_id}")
                return
            
            # For now, log the overdue event
            # TODO: Create overdue email template and send notification
            logger.info(f"Invoice {event.invoice_number} is {event.days_overdue} days overdue for client {client.name}")
                
        except Exception as e:
            logger.error(f"Error handling overdue invoice: {str(e)}")
    
    async def _handle_invoice_created(self, event: InvoiceCreated) -> None:
        """Handle invoice creation (internal notification)."""
        logger.info(f"New invoice created: {event.invoice_number} for client {event.client_id}")


class ProjectNotificationHandler(EventHandler):
    """Handler for project-related notifications."""
    
    def __init__(self):
        """Initialize project notification handler."""
        self.email_service = get_email_service()
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process project events."""
        return isinstance(event, (ProjectCreated, ProjectCompleted, ProjectStatusChanged, ProjectDeadlineApproaching))
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle project events and send appropriate notifications."""
        try:
            if isinstance(event, ProjectStatusChanged):
                await self._handle_project_status_changed(event)
            elif isinstance(event, ProjectCompleted):
                await self._handle_project_completed(event)
            elif isinstance(event, ProjectDeadlineApproaching):
                await self._handle_deadline_approaching(event)
            elif isinstance(event, ProjectCreated):
                await self._handle_project_created(event)
                
        except Exception as e:
            logger.error(f"Error handling project event {event.event_type}: {str(e)}")
    
    async def _handle_project_status_changed(self, event: ProjectStatusChanged) -> None:
        """Send project status change notification."""
        try:
            # Get client and project data
            session = next(get_db_session())
            client_repo = SQLAlchemyClientRepository(session)
            project_repo = SQLAlchemyProjectRepository(session)
            
            client = await client_repo.find_by_id(event.client_id)
            project = await project_repo.find_by_id(event.project_id)
            
            if not client or not client.email or not project:
                logger.warning(f"Cannot send project update: missing data for event {event.event_id}")
                return
            
            # Prepare project data
            project_data = {
                "name": project.name,
                "status": event.new_status,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "budget": project.budget,
                "currency": project.currency,
                "description": project.description
            }
            
            # Send notification
            result = await self.email_service.send_project_update_notification(
                recipient_email=client.email,
                recipient_name=client.name,
                project_data=project_data,
                update_type="status_change"
            )
            
            if result.get("success"):
                logger.info(f"Project status change notification sent to {client.email}")
            else:
                logger.error(f"Failed to send project notification: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error sending project status notification: {str(e)}")
    
    async def _handle_project_completed(self, event: ProjectCompleted) -> None:
        """Send project completion notification."""
        try:
            # Get client data
            session = next(get_db_session())
            client_repo = SQLAlchemyClientRepository(session)
            
            client = await client_repo.find_by_id(event.client_id)
            
            if not client or not client.email:
                logger.warning(f"Cannot send completion notification: missing client email for event {event.event_id}")
                return
            
            # Prepare project data
            project_data = {
                "name": event.project_name,
                "status": "completed",
                "completion_date": event.completion_date,
                "total_hours": event.total_hours,
                "total_cost": event.total_cost,
                "currency": event.currency
            }
            
            # Send notification
            result = await self.email_service.send_project_update_notification(
                recipient_email=client.email,
                recipient_name=client.name,
                project_data=project_data,
                update_type="completion"
            )
            
            if result.get("success"):
                logger.info(f"Project completion notification sent to {client.email}")
            
        except Exception as e:
            logger.error(f"Error sending project completion notification: {str(e)}")
    
    async def _handle_deadline_approaching(self, event: ProjectDeadlineApproaching) -> None:
        """Send deadline approaching notification."""
        logger.info(f"Project {event.project_name} deadline approaching: {event.days_remaining} days remaining")
    
    async def _handle_project_created(self, event: ProjectCreated) -> None:
        """Handle project creation (internal notification)."""
        logger.info(f"New project created: {event.project_name} for client {event.client_id}")


class TimeTrackingNotificationHandler(EventHandler):
    """Handler for time tracking notifications."""
    
    def __init__(self):
        """Initialize time tracking notification handler."""
        self.email_service = get_email_service()
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process time tracking events."""
        return isinstance(event, (WeeklyTimeReport, MonthlyTimeReport))
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle time tracking events."""
        try:
            if isinstance(event, WeeklyTimeReport):
                await self._handle_weekly_report(event)
            elif isinstance(event, MonthlyTimeReport):
                await self._handle_monthly_report(event)
                
        except Exception as e:
            logger.error(f"Error handling time tracking event {event.event_type}: {str(e)}")
    
    async def _handle_weekly_report(self, event: WeeklyTimeReport) -> None:
        """Send weekly time tracking report."""
        logger.info(f"Weekly time report for user {event.user_id}: {event.total_hours} hours")
        
        # TODO: Get user email and send summary
        # This would require a user repository to get email address
    
    async def _handle_monthly_report(self, event: MonthlyTimeReport) -> None:
        """Send monthly time tracking report."""
        logger.info(f"Monthly time report for user {event.user_id}: {event.total_hours} hours, {event.total_earnings} earnings")