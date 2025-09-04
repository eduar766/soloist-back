"""
Notifications router.
Handles email notifications, event management, and notification settings.
"""

from typing import Annotated, Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.infrastructure.auth import get_current_user_id
from app.infrastructure.email import get_email_service, EmailMessage, EmailAttachment
from app.domain.events.base import get_event_dispatcher, publish_event
from app.domain.events.invoice_events import InvoiceSent, InvoicePaid
from app.domain.events.project_events import ProjectStatusChanged
from app.domain.events.time_entry_events import WeeklyTimeReport
from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
from app.infrastructure.repositories.project_repository import SQLAlchemyProjectRepository
from app.infrastructure.repositories.invoice_repository import SQLAlchemyInvoiceRepository
from app.infrastructure.db.database import get_db_session


router = APIRouter()


class SendEmailRequest(BaseModel):
    """Request model for sending custom emails."""
    to: str
    subject: str
    template: str
    context: Dict[str, Any]
    priority: str = "normal"


class TestNotificationRequest(BaseModel):
    """Request model for testing notifications."""
    notification_type: str
    recipient_email: EmailStr
    test_data: Dict[str, Any] = {}


class NotificationSettingsRequest(BaseModel):
    """Request model for notification settings."""
    email_notifications: bool = True
    invoice_notifications: bool = True
    project_notifications: bool = True
    time_report_notifications: bool = True
    notification_frequency: str = "immediate"  # immediate, daily, weekly


@router.get("/email/templates")
async def list_email_templates(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    List available email templates.
    """
    try:
        email_service = get_email_service()
        templates = email_service.template_loader.list_templates()
        
        template_info = []
        for template in templates:
            info = email_service.template_loader.get_template_info(template)
            template_info.append(info)
        
        return {
            "templates": template_info,
            "total": len(template_info)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.post("/email/send")
async def send_custom_email(
    request: SendEmailRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Send a custom email using a template.
    
    - **to**: Recipient email address
    - **subject**: Email subject
    - **template**: Template name to use
    - **context**: Template context variables
    - **priority**: Email priority (high, normal, low)
    """
    try:
        email_service = get_email_service()
        
        message = EmailMessage(
            to=request.to,
            subject=request.subject,
            template=request.template,
            context=request.context,
            priority=request.priority
        )
        
        result = await email_service.send_email(message)
        
        return {
            "success": result.get("success", False),
            "message": "Email sent successfully" if result.get("success") else "Email send failed",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.get("/email/sent")
async def get_sent_emails(
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(20, description="Number of emails to retrieve")
):
    """
    Get list of recently sent emails (for development/testing).
    
    - **limit**: Maximum number of emails to retrieve
    """
    try:
        email_service = get_email_service()
        sent_emails = email_service.get_sent_emails()
        
        # Apply limit
        limited_emails = sent_emails[-limit:] if sent_emails else []
        
        return {
            "sent_emails": limited_emails,
            "total": len(sent_emails),
            "showing": len(limited_emails)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sent emails: {str(e)}"
        )


@router.delete("/email/sent")
async def clear_sent_emails(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Clear the sent emails log."""
    try:
        email_service = get_email_service()
        email_service.clear_sent_emails()
        
        return {"message": "Sent emails log cleared successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear sent emails: {str(e)}"
        )


@router.post("/test/{notification_type}")
async def test_notification(
    notification_type: str,
    request: TestNotificationRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Send a test notification.
    
    - **notification_type**: Type of notification to test (invoice, project, welcome, etc.)
    - **recipient_email**: Email to send test to
    - **test_data**: Optional test data for the notification
    """
    try:
        email_service = get_email_service()
        
        if notification_type == "invoice":
            # Send test invoice notification
            invoice_data = {
                "invoice_number": "TEST-001",
                "issue_date": datetime.now(),
                "due_date": datetime.now() + timedelta(days=30),
                "status": "sent",
                "subtotal": 1000.00,
                "tax_amount": 150.00,
                "total_amount": 1150.00,
                "currency": "USD",
                "company_name": "Test Company",
                **request.test_data
            }
            
            result = await email_service.send_invoice_notification(
                client_email=request.recipient_email,
                client_name="Test Client",
                invoice_data=invoice_data
            )
            
        elif notification_type == "payment":
            # Send test payment notification
            payment_data = {
                "invoice_number": "TEST-001",
                "amount": 1150.00,
                "currency": "USD",
                "payment_method": "Credit Card",
                "payment_date": datetime.now(),
                "transaction_id": "TXN-123456",
                **request.test_data
            }
            
            result = await email_service.send_payment_received_notification(
                client_email=request.recipient_email,
                client_name="Test Client",
                payment_data=payment_data
            )
            
        elif notification_type == "project":
            # Send test project update
            project_data = {
                "name": "Test Project",
                "status": "in_progress",
                "start_date": datetime.now() - timedelta(days=10),
                "end_date": datetime.now() + timedelta(days=20),
                "budget": 5000.00,
                "currency": "USD",
                "description": "This is a test project notification",
                **request.test_data
            }
            
            result = await email_service.send_project_update_notification(
                recipient_email=request.recipient_email,
                recipient_name="Test Client",
                project_data=project_data,
                update_type="status_change"
            )
            
        elif notification_type == "welcome":
            # Send test welcome email
            welcome_data = {
                "features": [
                    {"name": "Project Management", "description": "Organize your work efficiently"},
                    {"name": "Time Tracking", "description": "Track time accurately"},
                    {"name": "Invoice Generation", "description": "Create professional invoices"}
                ],
                "dashboard_url": "https://example.com/dashboard",
                **request.test_data
            }
            
            result = await email_service.send_welcome_email(
                user_email=request.recipient_email,
                user_name="Test User",
                welcome_data=welcome_data
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown notification type: {notification_type}"
            )
        
        return {
            "success": result.get("success", False),
            "message": f"Test {notification_type} notification sent",
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )


@router.get("/events/recent")
async def get_recent_events(
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(50, description="Number of events to retrieve")
):
    """
    Get recent domain events.
    
    - **limit**: Maximum number of events to retrieve
    """
    try:
        dispatcher = get_event_dispatcher()
        events = dispatcher.get_event_log(limit=limit)
        
        return {
            "events": events,
            "total": len(events)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}"
        )


@router.delete("/events/log")
async def clear_event_log(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Clear the event log."""
    try:
        dispatcher = get_event_dispatcher()
        dispatcher.clear_event_log()
        
        return {"message": "Event log cleared successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear event log: {str(e)}"
        )


@router.get("/events/handlers")
async def get_event_handlers(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Get information about registered event handlers."""
    try:
        dispatcher = get_event_dispatcher()
        handlers = dispatcher.get_registered_handlers()
        
        return {
            "handlers": handlers,
            "total_event_types": len([k for k in handlers.keys() if k != "global"]),
            "has_global_handlers": "global" in handlers
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get handlers: {str(e)}"
        )


@router.post("/events/trigger/{event_type}")
async def trigger_test_event(
    event_type: str,
    event_data: Dict[str, Any] = Body(...),
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Trigger a test domain event.
    
    - **event_type**: Type of event to trigger
    - **event_data**: Event data payload
    """
    try:
        if event_type == "invoice_sent":
            event = InvoiceSent(
                invoice_id=event_data.get("invoice_id", 1),
                client_id=event_data.get("client_id", 1),
                user_id=user_id,
                invoice_number=event_data.get("invoice_number", "TEST-001"),
                client_email=event_data.get("client_email", "test@example.com")
            )
            
        elif event_type == "invoice_paid":
            event = InvoicePaid(
                invoice_id=event_data.get("invoice_id", 1),
                client_id=event_data.get("client_id", 1),
                user_id=user_id,
                invoice_number=event_data.get("invoice_number", "TEST-001"),
                amount_paid=event_data.get("amount_paid", 1000.0),
                currency=event_data.get("currency", "USD"),
                payment_method=event_data.get("payment_method", "Credit Card")
            )
            
        elif event_type == "project_status_changed":
            event = ProjectStatusChanged(
                project_id=event_data.get("project_id", 1),
                client_id=event_data.get("client_id", 1),
                user_id=user_id,
                project_name=event_data.get("project_name", "Test Project"),
                old_status=event_data.get("old_status", "planning"),
                new_status=event_data.get("new_status", "in_progress")
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown event type: {event_type}"
            )
        
        # Publish the event
        await publish_event(event)
        
        return {
            "success": True,
            "message": f"Test event {event_type} triggered successfully",
            "event_id": event.event_id,
            "event_data": event.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger event: {str(e)}"
        )


@router.get("/settings")
async def get_notification_settings(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Get notification settings for the current user."""
    # TODO: Implement user notification preferences storage
    # For now, return default settings
    
    return {
        "email_notifications": True,
        "invoice_notifications": True,
        "project_notifications": True,
        "time_report_notifications": True,
        "notification_frequency": "immediate",
        "email_address": "user@example.com"  # Would get from user profile
    }


@router.put("/settings")
async def update_notification_settings(
    settings: NotificationSettingsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Update notification settings for the current user."""
    # TODO: Implement user notification preferences storage
    
    return {
        "message": "Notification settings updated successfully",
        "settings": {
            "email_notifications": settings.email_notifications,
            "invoice_notifications": settings.invoice_notifications,
            "project_notifications": settings.project_notifications,
            "time_report_notifications": settings.time_report_notifications,
            "notification_frequency": settings.notification_frequency
        }
    }


@router.get("/stats")
async def get_notification_stats(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """Get notification statistics."""
    try:
        email_service = get_email_service()
        dispatcher = get_event_dispatcher()
        
        sent_emails = email_service.get_sent_emails()
        events = dispatcher.get_event_log()
        
        # Basic stats
        stats = {
            "emails_sent_total": len(sent_emails),
            "events_processed_total": len(events),
            "emails_sent_today": len([
                email for email in sent_emails 
                if email.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))
            ]),
            "recent_activity": {
                "last_email_sent": sent_emails[-1] if sent_emails else None,
                "last_event_processed": events[0] if events else None
            }
        }
        
        # Count by notification type
        notification_types = {}
        for email in sent_emails:
            template = email.get("template", "unknown")
            notification_types[template] = notification_types.get(template, 0) + 1
        
        stats["by_type"] = notification_types
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification stats: {str(e)}"
        )