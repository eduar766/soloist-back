"""
Email service for sending notifications and communications.
Handles email sending for various user operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class EmailService(ABC):
    """
    Email service interface.
    Defines email operations for user communications.
    """

    @abstractmethod
    async def send_email(self,
                        to: str,
                        subject: str,
                        body: str,
                        html_body: Optional[str] = None,
                        from_email: Optional[str] = None) -> bool:
        """
        Send an email to the specified recipient.
        """
        pass

    @abstractmethod
    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """
        Send a welcome email to new users.
        """
        pass

    @abstractmethod
    async def send_password_reset_email(self,
                                       user_email: str,
                                       reset_token: str,
                                       user_name: str) -> bool:
        """
        Send a password reset email with reset token.
        """
        pass

    @abstractmethod
    async def send_email_verification(self,
                                     user_email: str,
                                     verification_token: str,
                                     user_name: str) -> bool:
        """
        Send an email verification message.
        """
        pass

    @abstractmethod
    async def send_invoice_email(self,
                                client_email: str,
                                invoice_pdf_url: str,
                                invoice_number: str,
                                client_name: str) -> bool:
        """
        Send an invoice to a client via email.
        """
        pass

    @abstractmethod
    async def send_bulk_email(self,
                             recipients: List[str],
                             subject: str,
                             body: str,
                             html_body: Optional[str] = None) -> List[bool]:
        """
        Send bulk emails to multiple recipients.
        Returns list of success/failure for each recipient.
        """
        pass