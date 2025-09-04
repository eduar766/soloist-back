"""
Domain events related to invoices.
Events for invoice lifecycle management and notifications.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .base import DomainEvent


@dataclass
class InvoiceCreated(DomainEvent):
    """Event fired when a new invoice is created."""
    
    invoice_id: int
    client_id: int
    user_id: str
    invoice_number: str
    total_amount: float
    currency: str
    due_date: Optional[datetime] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "due_date": self.due_date.isoformat() if self.due_date else None
        }


@dataclass
class InvoicePaid(DomainEvent):
    """Event fired when an invoice is marked as paid."""
    
    invoice_id: int
    client_id: int
    user_id: str
    invoice_number: str
    amount_paid: float
    currency: str
    payment_method: str
    transaction_id: Optional[str] = None
    payment_date: Optional[datetime] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "amount_paid": self.amount_paid,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None
        }


@dataclass
class InvoiceOverdue(DomainEvent):
    """Event fired when an invoice becomes overdue."""
    
    invoice_id: int
    client_id: int
    user_id: str
    invoice_number: str
    total_amount: float
    currency: str
    due_date: datetime
    days_overdue: int
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "due_date": self.due_date.isoformat(),
            "days_overdue": self.days_overdue
        }


@dataclass
class InvoiceSent(DomainEvent):
    """Event fired when an invoice is sent to client."""
    
    invoice_id: int
    client_id: int
    user_id: str
    invoice_number: str
    client_email: str
    sent_at: Optional[datetime] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "client_email": self.client_email,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }


@dataclass
class InvoiceCancelled(DomainEvent):
    """Event fired when an invoice is cancelled."""
    
    invoice_id: int
    client_id: int
    user_id: str
    invoice_number: str
    cancellation_reason: Optional[str] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "cancellation_reason": self.cancellation_reason
        }