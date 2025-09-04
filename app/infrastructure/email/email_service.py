"""
Email service for sending professional notifications.
Handles SMTP connections, template rendering, and delivery.
"""

import asyncio
import smtplib
import logging
from typing import List, Dict, Any, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from app.config import settings
from .template_loader import EmailTemplateLoader


logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment data."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass 
class EmailMessage:
    """Email message data."""
    to: Union[str, List[str]]
    subject: str
    template: str
    context: Dict[str, Any]
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    attachments: Optional[List[EmailAttachment]] = None
    priority: str = "normal"  # high, normal, low
    from_name: Optional[str] = None
    from_address: Optional[str] = None


class EmailService:
    """Service for sending professional email notifications."""
    
    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_name = settings.email_from_name
        self.from_address = settings.email_from_address
        self.template_loader = EmailTemplateLoader()
        self.sent_emails = []  # For tracking in development
        
    async def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Send an email message.
        
        Args:
            message: Email message to send
            
        Returns:
            Result dictionary with success status and details
        """
        try:
            # Validate SMTP configuration
            if not self._is_smtp_configured():
                logger.warning("SMTP not configured, email will be logged instead")
                return await self._log_email(message)
            
            # Render email template
            html_content, text_content = await self._render_template(
                message.template, 
                message.context
            )
            
            # Create MIME message
            mime_message = self._create_mime_message(
                message=message,
                html_content=html_content,
                text_content=text_content
            )
            
            # Send email via SMTP
            result = await self._send_via_smtp(mime_message, message)
            
            # Log successful send
            logger.info(f"Email sent successfully to {message.to}: {message.subject}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_invoice_notification(
        self,
        client_email: str,
        client_name: str,
        invoice_data: Dict[str, Any],
        pdf_attachment: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Send invoice notification to client."""
        
        attachments = []
        if pdf_attachment:
            attachments.append(EmailAttachment(
                filename=f"factura_{invoice_data['invoice_number']}.pdf",
                content=pdf_attachment,
                content_type="application/pdf"
            ))
        
        message = EmailMessage(
            to=client_email,
            subject=f"Factura {invoice_data['invoice_number']} - {invoice_data['company_name']}",
            template="invoice_sent",
            context={
                "client_name": client_name,
                "invoice": invoice_data,
                "company_name": invoice_data.get("company_name", settings.email_from_name)
            },
            attachments=attachments,
            priority="high"
        )
        
        return await self.send_email(message)
    
    async def send_payment_received_notification(
        self,
        client_email: str,
        client_name: str,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send payment received confirmation."""
        
        message = EmailMessage(
            to=client_email,
            subject=f"Pago recibido - Factura {payment_data['invoice_number']}",
            template="payment_received",
            context={
                "client_name": client_name,
                "payment": payment_data
            },
            priority="high"
        )
        
        return await self.send_email(message)
    
    async def send_project_update_notification(
        self,
        recipient_email: str,
        recipient_name: str,
        project_data: Dict[str, Any],
        update_type: str = "status_change"
    ) -> Dict[str, Any]:
        """Send project update notification."""
        
        message = EmailMessage(
            to=recipient_email,
            subject=f"Actualización del proyecto: {project_data['name']}",
            template="project_update",
            context={
                "recipient_name": recipient_name,
                "project": project_data,
                "update_type": update_type
            }
        )
        
        return await self.send_email(message)
    
    async def send_time_entry_summary(
        self,
        client_email: str,
        client_name: str,
        time_summary: Dict[str, Any],
        period: str = "weekly"
    ) -> Dict[str, Any]:
        """Send time tracking summary."""
        
        message = EmailMessage(
            to=client_email,
            subject=f"Resumen de tiempo trabajado - {period}",
            template="time_summary", 
            context={
                "client_name": client_name,
                "summary": time_summary,
                "period": period
            }
        )
        
        return await self.send_email(message)
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        welcome_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send welcome email for new users."""
        
        message = EmailMessage(
            to=user_email,
            subject="¡Bienvenido al Sistema de Gestión Freelancer!",
            template="welcome",
            context={
                "user_name": user_name,
                "welcome_data": welcome_data
            }
        )
        
        return await self.send_email(message)
    
    async def send_bulk_emails(self, messages: List[EmailMessage]) -> List[Dict[str, Any]]:
        """Send multiple emails concurrently."""
        tasks = [self.send_email(message) for message in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            result if not isinstance(result, Exception) 
            else {"success": False, "error": str(result)}
            for result in results
        ]
    
    async def _render_template(
        self, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> tuple[str, str]:
        """Render email template with context."""
        html_content = await self.template_loader.render_template(
            f"{template_name}.html", 
            context
        )
        
        # Try to render text version, fallback to HTML stripped
        try:
            text_content = await self.template_loader.render_template(
                f"{template_name}.txt", 
                context
            )
        except:
            # Strip HTML tags for text version
            import re
            text_content = re.sub(r'<[^>]+>', '', html_content)
        
        return html_content, text_content
    
    def _create_mime_message(
        self,
        message: EmailMessage,
        html_content: str,
        text_content: str
    ) -> MIMEMultipart:
        """Create MIME message from email data."""
        
        mime_msg = MIMEMultipart("alternative")
        
        # Headers
        mime_msg["Subject"] = message.subject
        mime_msg["From"] = f"{message.from_name or self.from_name} <{message.from_address or self.from_address}>"
        
        # Recipients
        if isinstance(message.to, list):
            mime_msg["To"] = ", ".join(message.to)
        else:
            mime_msg["To"] = message.to
            
        if message.cc:
            if isinstance(message.cc, list):
                mime_msg["Cc"] = ", ".join(message.cc)
            else:
                mime_msg["Cc"] = message.cc
        
        # Priority
        if message.priority == "high":
            mime_msg["X-Priority"] = "1"
        elif message.priority == "low":
            mime_msg["X-Priority"] = "5"
        
        # Content
        text_part = MIMEText(text_content, "plain", "utf-8")
        html_part = MIMEText(html_content, "html", "utf-8")
        
        mime_msg.attach(text_part)
        mime_msg.attach(html_part)
        
        # Attachments
        if message.attachments:
            for attachment in message.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment.filename}"
                )
                mime_msg.attach(part)
        
        return mime_msg
    
    async def _send_via_smtp(
        self, 
        mime_message: MIMEMultipart, 
        original_message: EmailMessage
    ) -> Dict[str, Any]:
        """Send email via SMTP server."""
        
        try:
            # Get all recipients
            recipients = []
            if isinstance(original_message.to, list):
                recipients.extend(original_message.to)
            else:
                recipients.append(original_message.to)
                
            if original_message.cc:
                if isinstance(original_message.cc, list):
                    recipients.extend(original_message.cc)
                else:
                    recipients.append(original_message.cc)
                    
            if original_message.bcc:
                if isinstance(original_message.bcc, list):
                    recipients.extend(original_message.bcc)
                else:
                    recipients.append(original_message.bcc)
            
            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(mime_message, to_addrs=recipients)
            
            return {
                "success": True,
                "message_id": mime_message["Message-ID"],
                "recipients": recipients,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"SMTP send failed: {str(e)}")
    
    async def _log_email(self, message: EmailMessage) -> Dict[str, Any]:
        """Log email instead of sending (for development)."""
        
        html_content, text_content = await self._render_template(
            message.template, 
            message.context
        )
        
        email_log = {
            "timestamp": datetime.now().isoformat(),
            "to": message.to,
            "subject": message.subject,
            "template": message.template,
            "html_preview": html_content[:200] + "..." if len(html_content) > 200 else html_content,
            "has_attachments": bool(message.attachments),
            "priority": message.priority
        }
        
        self.sent_emails.append(email_log)
        
        logger.info(f"Email logged (SMTP not configured): {message.subject} to {message.to}")
        
        return {
            "success": True,
            "logged": True,
            "message": "Email logged successfully (SMTP not configured)",
            "timestamp": datetime.now().isoformat()
        }
    
    def _is_smtp_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return all([
            self.smtp_host,
            self.smtp_user,
            self.smtp_password
        ])
    
    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Get list of sent emails (for development/testing)."""
        return self.sent_emails.copy()
    
    def clear_sent_emails(self) -> None:
        """Clear sent emails log."""
        self.sent_emails.clear()


# Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service