"""
Invoice domain model.
Represents invoices generated from time entries and project work.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from app.domain.models.base import (
    AggregateRoot,
    Money,
    InvoiceNumber,
    ValidationError,
    BusinessRuleViolation,
    DomainEvent
)


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class InvoiceType(str, Enum):
    """Invoice type."""
    TIME_BASED = "time_based"
    FIXED_PRICE = "fixed_price"
    MILESTONE = "milestone"
    RETAINER = "retainer"
    EXPENSE = "expense"
    MIXED = "mixed"


class PaymentStatus(str, Enum):
    """Payment status."""
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method."""
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    CHECK = "check"
    CASH = "cash"
    CRYPTO = "crypto"
    OTHER = "other"


# Domain Events

class InvoiceCreatedEvent(DomainEvent):
    """Event raised when an invoice is created."""
    
    def __init__(self, invoice_id: int, invoice_number: str, client_id: int, total_amount: float):
        super().__init__()
        self.invoice_id = invoice_id
        self.invoice_number = invoice_number
        self.client_id = client_id
        self.total_amount = total_amount
    
    @property
    def event_name(self) -> str:
        return "invoice.created"


class InvoiceSentEvent(DomainEvent):
    """Event raised when an invoice is sent to client."""
    
    def __init__(self, invoice_id: int, sent_to_email: str, sent_by: str):
        super().__init__()
        self.invoice_id = invoice_id
        self.sent_to_email = sent_to_email
        self.sent_by = sent_by
    
    @property
    def event_name(self) -> str:
        return "invoice.sent"


class InvoicePaidEvent(DomainEvent):
    """Event raised when an invoice is paid."""
    
    def __init__(self, invoice_id: int, payment_amount: float, payment_method: str, payment_date: date):
        super().__init__()
        self.invoice_id = invoice_id
        self.payment_amount = payment_amount
        self.payment_method = payment_method
        self.payment_date = payment_date
    
    @property
    def event_name(self) -> str:
        return "invoice.paid"


class InvoiceOverdueEvent(DomainEvent):
    """Event raised when an invoice becomes overdue."""
    
    def __init__(self, invoice_id: int, days_overdue: int, outstanding_amount: float):
        super().__init__()
        self.invoice_id = invoice_id
        self.days_overdue = days_overdue
        self.outstanding_amount = outstanding_amount
    
    @property
    def event_name(self) -> str:
        return "invoice.overdue"


@dataclass
class InvoiceLineItem:
    """Individual line item in an invoice."""
    
    description: str
    quantity: float
    rate: float
    amount: float
    
    # Time tracking reference
    time_entry_id: Optional[int] = None
    task_id: Optional[int] = None
    
    # Additional details
    unit: str = "hours"
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Initialize line item."""
        # Auto-calculate amount if not provided
        if not self.amount:
            self.amount = self.quantity * self.rate
    
    def validate(self) -> None:
        """Validate line item."""
        if not self.description:
            raise ValidationError("Description is required", "description")
        
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative", "quantity")
        
        if self.rate < 0:
            raise ValidationError("Rate cannot be negative", "rate")
        
        if abs(self.amount - (self.quantity * self.rate)) > 0.01:  # Allow small floating point errors
            raise ValidationError("Amount must equal quantity * rate", "amount")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "quantity": self.quantity,
            "rate": self.rate,
            "amount": self.amount,
            "unit": self.unit,
            "time_entry_id": self.time_entry_id,
            "task_id": self.task_id,
            "notes": self.notes
        }


@dataclass
class TaxLineItem:
    """Tax line item in an invoice."""
    
    name: str
    rate: float  # Tax rate as percentage (e.g., 19.0 for 19%)
    amount: float
    
    # Tax configuration
    tax_id: Optional[str] = None  # Tax authority ID
    is_compound: bool = False  # Whether this tax is calculated on top of other taxes
    
    def validate(self) -> None:
        """Validate tax line item."""
        if not self.name:
            raise ValidationError("Tax name is required", "name")
        
        if self.rate < 0 or self.rate > 100:
            raise ValidationError("Tax rate must be between 0 and 100", "rate")
        
        if self.amount < 0:
            raise ValidationError("Tax amount cannot be negative", "amount")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "rate": self.rate,
            "amount": self.amount,
            "tax_id": self.tax_id,
            "is_compound": self.is_compound
        }


@dataclass
class PaymentRecord:
    """Payment record for an invoice."""
    
    amount: float
    payment_date: date
    payment_method: PaymentMethod
    
    # Payment details
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    processed_by: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.utcnow)
    
    def validate(self) -> None:
        """Validate payment record."""
        if self.amount <= 0:
            raise ValidationError("Payment amount must be positive", "amount")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "amount": self.amount,
            "payment_date": self.payment_date.isoformat(),
            "payment_method": self.payment_method.value,
            "reference_number": self.reference_number,
            "notes": self.notes,
            "processed_by": self.processed_by,
            "processed_at": self.processed_at.isoformat()
        }


@dataclass
class InvoiceSettings:
    """Invoice configuration and settings."""
    
    # Numbering
    number_prefix: str = "INV"
    number_suffix: Optional[str] = None
    next_number: int = 1
    
    # Terms and conditions
    payment_terms_days: int = 30
    late_fee_percentage: float = 0  # Late fee as percentage per month
    
    # Display settings
    currency: str = "USD"
    language: str = "en"
    
    # Contact information
    from_name: str = ""
    from_email: str = ""
    from_address: str = ""
    
    # Banking details
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    routing_number: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "number_prefix": self.number_prefix,
            "number_suffix": self.number_suffix,
            "next_number": self.next_number,
            "payment_terms_days": self.payment_terms_days,
            "late_fee_percentage": self.late_fee_percentage,
            "currency": self.currency,
            "language": self.language,
            "from_name": self.from_name,
            "from_email": self.from_email,
            "from_address": self.from_address,
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "routing_number": self.routing_number
        }


class Invoice(AggregateRoot):
    """
    Invoice aggregate root.
    Represents an invoice for time worked or services provided.
    """
    
    def __init__(
        self,
        client_id: int,
        project_id: int,
        created_by: str,
        invoice_number: InvoiceNumber,
        invoice_type: InvoiceType = InvoiceType.TIME_BASED,
        status: InvoiceStatus = InvoiceStatus.DRAFT,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Required fields
        self.client_id = client_id
        self.project_id = project_id
        self.created_by = created_by  # User ID who created the invoice
        
        # Invoice identification
        self.invoice_number = invoice_number
        self.invoice_type = invoice_type
        self.status = status
        
        # Dates
        self.invoice_date = date.today()
        self.due_date = None
        self.sent_date = None
        
        # Financial information
        self.currency = "USD"
        self.line_items = []
        self.tax_items = []
        
        # Calculated amounts
        self.subtotal = 0.0
        self.tax_total = 0.0
        self.total = 0.0
        
        # Discount
        self.discount_percentage = 0.0
        self.discount_amount = 0.0
        
        # Payment information
        self.payment_status = PaymentStatus.UNPAID
        self.payment_records = []
        self.amount_paid = 0.0
        
        # Content
        self.title = None
        self.description = None
        self.notes = None
        self.terms_and_conditions = None
        
        # File references
        self.pdf_url = None
        self.pdf_generated_at = None
        
        # Sharing and access
        self.public_url = None
        self.client_viewed_at = None
        
        # Time entries included in this invoice
        self.time_entry_ids = []
    
    def __post_init__(self):
        """Initialize invoice after creation."""
        super().__post_init__()
        
        # Set due date if not provided
        if not self.due_date:
            # Default to 30 days from invoice date
            from datetime import timedelta
            self.due_date = self.invoice_date + timedelta(days=30)
        
        # Calculate totals
        self.recalculate_totals()
        
        # Validate on creation
        self.validate()
        
        # Add creation event if new
        if self.is_new:
            self.add_event(InvoiceCreatedEvent(
                invoice_id=self.id or 0,
                invoice_number=str(self.invoice_number),
                client_id=self.client_id,
                total_amount=self.total
            ))
    
    def validate(self) -> None:
        """Validate invoice state."""
        # Required fields
        if not self.client_id:
            raise ValidationError("Client ID is required", "client_id")
        
        if not self.project_id:
            raise ValidationError("Project ID is required", "project_id")
        
        if not self.created_by:
            raise ValidationError("Created by is required", "created_by")
        
        # Validate dates
        if self.due_date < self.invoice_date:
            raise ValidationError("Due date cannot be before invoice date", "due_date")
        
        # Validate line items
        for item in self.line_items:
            item.validate()
        
        # Validate tax items
        for tax in self.tax_items:
            tax.validate()
        
        # Validate payment records
        for payment in self.payment_records:
            payment.validate()
        
        # Validate amounts
        if self.subtotal < 0:
            raise ValidationError("Subtotal cannot be negative", "subtotal")
        
        if self.total < 0:
            raise ValidationError("Total cannot be negative", "total")
        
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise ValidationError("Discount percentage must be between 0 and 100", "discount_percentage")
        
        if self.amount_paid < 0:
            raise ValidationError("Amount paid cannot be negative", "amount_paid")
        
        if self.amount_paid > self.total:
            raise ValidationError("Amount paid cannot exceed total", "amount_paid")
        
        # Business rules
        if self.status == InvoiceStatus.SENT and not self.sent_date:
            raise ValidationError("Sent date is required for sent invoices", "sent_date")
        
        if self.payment_status == PaymentStatus.PAID and self.amount_paid < self.total:
            raise ValidationError("Invoice marked as paid but amount paid is less than total", "payment_status")
    
    @property
    def is_draft(self) -> bool:
        """Check if invoice is in draft status."""
        return self.status == InvoiceStatus.DRAFT
    
    @property
    def is_sent(self) -> bool:
        """Check if invoice has been sent."""
        return self.status in [InvoiceStatus.SENT, InvoiceStatus.VIEWED, InvoiceStatus.PAID]
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.payment_status == PaymentStatus.PAID
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.is_paid or self.status in [InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED]:
            return False
        return date.today() > self.due_date
    
    @property
    def days_until_due(self) -> int:
        """Get days until due date (negative if overdue)."""
        return (self.due_date - date.today()).days
    
    @property
    def days_overdue(self) -> int:
        """Get days overdue (0 if not overdue)."""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days
    
    @property
    def outstanding_amount(self) -> float:
        """Get outstanding amount to be paid."""
        return max(0, self.total - self.amount_paid)
    
    @property
    def payment_percentage(self) -> float:
        """Get percentage of invoice that has been paid."""
        if self.total == 0:
            return 0
        return (self.amount_paid / self.total) * 100
    
    def add_line_item(
        self,
        description: str,
        quantity: float,
        rate: float,
        time_entry_id: Optional[int] = None,
        task_id: Optional[int] = None,
        unit: str = "hours"
    ) -> None:
        """Add a line item to the invoice."""
        if not self.can_be_edited():
            raise BusinessRuleViolation("Cannot edit this invoice")
        
        amount = quantity * rate
        item = InvoiceLineItem(
            description=description,
            quantity=quantity,
            rate=rate,
            amount=amount,
            time_entry_id=time_entry_id,
            task_id=task_id,
            unit=unit
        )
        
        item.validate()
        self.line_items.append(item)
        
        # Add time entry reference
        if time_entry_id and time_entry_id not in self.time_entry_ids:
            self.time_entry_ids.append(time_entry_id)
        
        self.recalculate_totals()
        self.mark_as_updated()
    
    def remove_line_item(self, index: int) -> None:
        """Remove a line item by index."""
        if not self.can_be_edited():
            raise BusinessRuleViolation("Cannot edit this invoice")
        
        if index < 0 or index >= len(self.line_items):
            raise ValidationError("Invalid line item index", "index")
        
        # Remove time entry reference if applicable
        item = self.line_items[index]
        if item.time_entry_id and item.time_entry_id in self.time_entry_ids:
            self.time_entry_ids.remove(item.time_entry_id)
        
        self.line_items.pop(index)
        self.recalculate_totals()
        self.mark_as_updated()
    
    def add_tax(self, name: str, rate: float, tax_id: Optional[str] = None) -> None:
        """Add a tax to the invoice."""
        if not self.can_be_edited():
            raise BusinessRuleViolation("Cannot edit this invoice")
        
        # Calculate tax amount on current subtotal
        tax_amount = (self.subtotal - self.discount_amount) * (rate / 100)
        
        tax_item = TaxLineItem(
            name=name,
            rate=rate,
            amount=tax_amount,
            tax_id=tax_id
        )
        
        tax_item.validate()
        self.tax_items.append(tax_item)
        self.recalculate_totals()
        self.mark_as_updated()
    
    def remove_tax(self, index: int) -> None:
        """Remove a tax item by index."""
        if not self.can_be_edited():
            raise BusinessRuleViolation("Cannot edit this invoice")
        
        if index < 0 or index >= len(self.tax_items):
            raise ValidationError("Invalid tax item index", "index")
        
        self.tax_items.pop(index)
        self.recalculate_totals()
        self.mark_as_updated()
    
    def set_discount(self, percentage: float = 0, amount: float = 0) -> None:
        """Set discount on the invoice."""
        if not self.can_be_edited():
            raise BusinessRuleViolation("Cannot edit this invoice")
        
        if percentage < 0 or percentage > 100:
            raise ValidationError("Discount percentage must be between 0 and 100", "percentage")
        
        if amount < 0:
            raise ValidationError("Discount amount cannot be negative", "amount")
        
        if percentage > 0 and amount > 0:
            raise ValidationError("Cannot set both percentage and amount discount", "discount")
        
        if percentage > 0:
            self.discount_percentage = percentage
            self.discount_amount = self.subtotal * (percentage / 100)
        else:
            self.discount_percentage = 0
            self.discount_amount = amount
        
        self.recalculate_totals()
        self.mark_as_updated()
    
    def recalculate_totals(self) -> None:
        """Recalculate all totals."""
        # Calculate subtotal from line items
        self.subtotal = sum(item.amount for item in self.line_items)
        
        # Apply discount
        discounted_subtotal = self.subtotal - self.discount_amount
        
        # Calculate tax total
        self.tax_total = sum(tax.amount for tax in self.tax_items)
        
        # Calculate total
        self.total = discounted_subtotal + self.tax_total
        
        # Update payment status based on amount paid
        self.update_payment_status()
    
    def update_payment_status(self) -> None:
        """Update payment status based on amount paid."""
        if self.amount_paid == 0:
            self.payment_status = PaymentStatus.OVERDUE if self.is_overdue else PaymentStatus.UNPAID
        elif self.amount_paid >= self.total:
            self.payment_status = PaymentStatus.PAID
        else:
            self.payment_status = PaymentStatus.PARTIALLY_PAID
    
    def send_to_client(self, sent_by: str, client_email: str) -> None:
        """Mark invoice as sent to client."""
        if self.status in [InvoiceStatus.CANCELLED]:
            raise BusinessRuleViolation("Cannot send cancelled invoice")
        
        if self.is_draft and len(self.line_items) == 0:
            raise BusinessRuleViolation("Cannot send empty invoice")
        
        self.status = InvoiceStatus.SENT
        self.sent_date = date.today()
        
        self.mark_as_updated()
        self.increment_version()
        
        self.add_event(InvoiceSentEvent(
            invoice_id=self.id or 0,
            sent_to_email=client_email,
            sent_by=sent_by
        ))
    
    def mark_as_viewed(self) -> None:
        """Mark invoice as viewed by client."""
        if self.status == InvoiceStatus.SENT:
            self.status = InvoiceStatus.VIEWED
            self.client_viewed_at = datetime.utcnow()
            self.mark_as_updated()
    
    def add_payment(
        self,
        amount: float,
        payment_method: PaymentMethod,
        payment_date: Optional[date] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        processed_by: Optional[str] = None
    ) -> None:
        """Add a payment to the invoice."""
        if amount <= 0:
            raise ValidationError("Payment amount must be positive", "amount")
        
        if self.amount_paid + amount > self.total:
            raise ValidationError("Payment amount exceeds outstanding balance", "amount")
        
        payment = PaymentRecord(
            amount=amount,
            payment_date=payment_date or date.today(),
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            processed_by=processed_by
        )
        
        payment.validate()
        self.payment_records.append(payment)
        self.amount_paid += amount
        
        # Update payment status
        self.update_payment_status()
        
        # If fully paid, mark as paid and add event
        if self.is_paid:
            self.status = InvoiceStatus.PAID
            self.add_event(InvoicePaidEvent(
                invoice_id=self.id or 0,
                payment_amount=amount,
                payment_method=payment_method.value,
                payment_date=payment.payment_date
            ))
        
        self.mark_as_updated()
        self.increment_version()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the invoice."""
        if self.status == InvoiceStatus.PAID:
            raise BusinessRuleViolation("Cannot cancel paid invoice")
        
        if self.amount_paid > 0:
            raise BusinessRuleViolation("Cannot cancel invoice with payments. Create refund instead.")
        
        self.status = InvoiceStatus.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}" if not self.notes else f"{self.notes}\nCancelled: {reason}"
        
        self.mark_as_updated()
        self.increment_version()
    
    def can_be_edited(self) -> bool:
        """Check if invoice can be edited."""
        return self.status in [InvoiceStatus.DRAFT, InvoiceStatus.PENDING]
    
    def can_be_deleted(self) -> bool:
        """Check if invoice can be deleted."""
        return self.status in [InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED] and self.amount_paid == 0
    
    def generate_pdf_url(self, base_url: str) -> str:
        """Generate PDF URL for the invoice."""
        # This would typically integrate with a PDF generation service
        return f"{base_url}/invoices/{self.id}/pdf"
    
    def generate_public_url(self, base_url: str, token: str) -> str:
        """Generate public URL for client access."""
        return f"{base_url}/public/invoices/{token}"
    
    @classmethod
    def create_from_time_entries(
        cls,
        client_id: int,
        project_id: int,
        created_by: str,
        time_entry_data: List[Dict],
        invoice_settings: InvoiceSettings
    ) -> 'Invoice':
        """Create an invoice from time entries."""
        # Generate invoice number
        invoice_number = InvoiceNumber(
            prefix=invoice_settings.number_prefix,
            number=invoice_settings.next_number,
            suffix=invoice_settings.number_suffix
        )
        
        # Calculate due date
        from datetime import timedelta
        due_date = date.today() + timedelta(days=invoice_settings.payment_terms_days)
        
        # Create invoice
        invoice = cls(
            client_id=client_id,
            project_id=project_id,
            created_by=created_by,
            invoice_number=invoice_number,
            invoice_type=InvoiceType.TIME_BASED,
            currency=invoice_settings.currency,
            due_date=due_date
        )
        
        # Add line items from time entries
        for entry_data in time_entry_data:
            invoice.add_line_item(
                description=entry_data.get('description', 'Time tracking'),
                quantity=entry_data['hours'],
                rate=entry_data['hourly_rate'],
                time_entry_id=entry_data['time_entry_id'],
                task_id=entry_data.get('task_id')
            )
        
        return invoice
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        data = super().to_dict()
        
        # Convert enum values
        data["invoice_type"] = self.invoice_type.value
        data["status"] = self.status.value
        data["payment_status"] = self.payment_status.value
        
        # Convert dates
        data["invoice_date"] = self.invoice_date.isoformat()
        data["due_date"] = self.due_date.isoformat()
        if self.sent_date:
            data["sent_date"] = self.sent_date.isoformat()
        
        # Convert optional datetime fields
        if self.pdf_generated_at:
            data["pdf_generated_at"] = self.pdf_generated_at.isoformat()
        if self.client_viewed_at:
            data["client_viewed_at"] = self.client_viewed_at.isoformat()
        
        # Convert invoice number
        data["invoice_number"] = str(self.invoice_number)
        
        # Convert nested objects
        data["line_items"] = [item.to_dict() for item in self.line_items]
        data["tax_items"] = [tax.to_dict() for tax in self.tax_items]
        data["payment_records"] = [payment.to_dict() for payment in self.payment_records]
        
        # Add computed properties
        data["is_draft"] = self.is_draft
        data["is_sent"] = self.is_sent
        data["is_paid"] = self.is_paid
        data["is_overdue"] = self.is_overdue
        data["days_until_due"] = self.days_until_due
        data["days_overdue"] = self.days_overdue
        data["outstanding_amount"] = self.outstanding_amount
        data["payment_percentage"] = self.payment_percentage
        
        return data