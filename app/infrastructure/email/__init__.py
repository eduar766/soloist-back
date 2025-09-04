"""
Email and notification infrastructure.
Handles email templates, SMTP service, and notification delivery.
"""

from .email_service import EmailService, get_email_service
from .template_loader import EmailTemplateLoader

__all__ = [
    "EmailService",
    "get_email_service", 
    "EmailTemplateLoader"
]