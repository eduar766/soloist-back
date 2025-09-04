"""
Invoice DTOs for the application layer.
Data Transfer Objects for invoice and billing operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from pydantic import Field, validator
from enum import Enum

from .base_dto import (
    RequestDTO, ResponseDTO, CreateRequestDTO, UpdateRequestDTO,
    ListRequestDTO, FilterRequestDTO, TimestampMixin, TagsMixin, NotesMixin
)


class InvoiceStatus(str, Enum):
    """Invoice status options."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceItemType(str, Enum):
    """Invoice item type options."""
    TIME = "time"
    EXPENSE = "expense"
    FIXED = "fixed"
    DISCOUNT = "discount"
    TAX = "tax"


class PaymentStatus(str, Enum):
    """Payment status options."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method options."""
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    CHECK = "check"
    CASH = "cash"
    OTHER = "other"


# Nested DTOs
class InvoiceItemRequestDTO(RequestDTO):
    """DTO for invoice item in requests."""
    
    item_type: InvoiceItemType = Field(description="Item type")
    description: str = Field(min_length=1, max_length=500, description="Item description")
    quantity: Decimal = Field(ge=0, description="Quantity")
    unit_price: Decimal = Field(ge=0, description="Unit price")
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Tax rate (0-1)")
    
    # Time-specific fields
    time_entry_ids: Optional[List[int]] = Field(default=None, description="Related time entry IDs")
    hourly_rate: Optional[Decimal] = Field(default=None, ge=0, description="Hourly rate for time items")
    hours: Optional[Decimal] = Field(default=None, ge=0, description="Hours for time items")
    
    # Date range for time items
    date_from: Optional[date] = Field(default=None, description="Start date for time items")
    date_to: Optional[date] = Field(default=None, description="End date for time items")


class InvoiceItemResponseDTO(ResponseDTO):
    """DTO for invoice item in responses."""
    
    item_type: InvoiceItemType = Field(description="Item type")
    description: str = Field(description="Item description")
    quantity: Decimal = Field(description="Quantity")
    unit_price: Decimal = Field(description="Unit price")
    line_total: Decimal = Field(description="Line total (quantity * unit_price)")
    tax_rate: Optional[Decimal] = Field(default=None, description="Tax rate")
    tax_amount: Optional[Decimal] = Field(default=None, description="Tax amount")
    total_amount: Decimal = Field(description="Total amount including tax")
    
    # Time-specific fields
    time_entry_ids: List[int] = Field(default_factory=list, description="Related time entry IDs")
    hourly_rate: Optional[Decimal] = Field(default=None, description="Hourly rate")
    hours: Optional[Decimal] = Field(default=None, description="Hours")
    date_from: Optional[date] = Field(default=None, description="Start date")
    date_to: Optional[date] = Field(default=None, description="End date")


class PaymentRequestDTO(RequestDTO):
    """DTO for payment in requests."""
    
    amount: Decimal = Field(gt=0, description="Payment amount")
    payment_method: PaymentMethod = Field(description="Payment method")
    payment_date: date = Field(description="Payment date")
    reference_number: Optional[str] = Field(default=None, max_length=100, description="Payment reference")
    notes: Optional[str] = Field(default=None, max_length=500, description="Payment notes")


class PaymentResponseDTO(ResponseDTO):
    """DTO for payment in responses."""
    
    amount: Decimal = Field(description="Payment amount")
    payment_method: PaymentMethod = Field(description="Payment method")
    payment_date: date = Field(description="Payment date")
    status: PaymentStatus = Field(description="Payment status")
    reference_number: Optional[str] = Field(default=None, description="Payment reference")
    notes: Optional[str] = Field(default=None, description="Payment notes")
    processed_at: Optional[datetime] = Field(default=None, description="Processing timestamp")
    processed_by_id: Optional[str] = Field(default=None, description="Processor user ID")


class InvoiceAddressDTO(RequestDTO):
    """DTO for invoice addresses."""
    
    name: str = Field(min_length=1, max_length=255, description="Name")
    company: Optional[str] = Field(default=None, max_length=255, description="Company name")
    address_line_1: str = Field(min_length=1, max_length=255, description="Address line 1")
    address_line_2: Optional[str] = Field(default=None, max_length=255, description="Address line 2")
    city: str = Field(min_length=1, max_length=100, description="City")
    state: Optional[str] = Field(default=None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(default=None, max_length=20, description="Postal code")
    country: str = Field(min_length=2, max_length=2, description="Country code")
    tax_number: Optional[str] = Field(default=None, max_length=50, description="Tax number")


# Request DTOs
class CreateInvoiceRequestDTO(CreateRequestDTO, TagsMixin, NotesMixin):
    """DTO for invoice creation requests."""
    
    project_id: int = Field(description="Project ID")
    client_id: int = Field(description="Client ID")
    
    # Invoice details
    invoice_number: Optional[str] = Field(default=None, max_length=50, description="Custom invoice number")
    title: Optional[str] = Field(default=None, max_length=255, description="Invoice title")
    description: Optional[str] = Field(default=None, max_length=1000, description="Invoice description")
    
    # Dates
    issue_date: date = Field(description="Invoice issue date")
    due_date: date = Field(description="Payment due date")
    
    # Currency
    currency: str = Field(max_length=3, description="Invoice currency")
    
    # Addresses
    from_address: InvoiceAddressDTO = Field(description="Sender address")
    to_address: InvoiceAddressDTO = Field(description="Recipient address")
    
    # Items
    items: List[InvoiceItemRequestDTO] = Field(min_items=1, description="Invoice items")
    
    # Discounts and adjustments
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Discount percentage")
    discount_amount: Optional[Decimal] = Field(default=None, ge=0, description="Fixed discount amount")
    tax_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Overall tax percentage")
    
    # Payment terms
    payment_terms: Optional[str] = Field(default=None, max_length=500, description="Payment terms text")
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate due date is after issue date."""
        if v and values.get('issue_date') and v < values['issue_date']:
            raise ValueError('Due date must be after issue date')
        return v


class CreateInvoiceFromTimeRequestDTO(RequestDTO):
    """DTO for creating invoice from time entries."""
    
    project_id: int = Field(description="Project ID")
    time_entry_ids: List[int] = Field(min_items=1, description="Time entry IDs to include")
    
    # Invoice details
    title: Optional[str] = Field(default=None, max_length=255, description="Invoice title")
    description: Optional[str] = Field(default=None, max_length=1000, description="Invoice description")
    issue_date: date = Field(description="Invoice issue date")
    due_date: date = Field(description="Payment due date")
    
    # Grouping options
    group_by_task: bool = Field(default=True, description="Group time entries by task")
    group_by_date: bool = Field(default=False, description="Group time entries by date")
    include_details: bool = Field(default=True, description="Include detailed time breakdown")
    
    # Additional items
    additional_items: Optional[List[InvoiceItemRequestDTO]] = Field(default=None, description="Additional non-time items")
    
    # Adjustments
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Discount percentage")
    tax_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Tax percentage")
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate due date is after issue date."""
        if v and values.get('issue_date') and v < values['issue_date']:
            raise ValueError('Due date must be after issue date')
        return v


class UpdateInvoiceRequestDTO(UpdateRequestDTO, TagsMixin, NotesMixin):
    """DTO for invoice update requests."""
    
    # Invoice details
    title: Optional[str] = Field(default=None, max_length=255, description="Invoice title")
    description: Optional[str] = Field(default=None, max_length=1000, description="Invoice description")
    
    # Dates
    issue_date: Optional[date] = Field(default=None, description="Invoice issue date")
    due_date: Optional[date] = Field(default=None, description="Payment due date")
    
    # Addresses
    from_address: Optional[InvoiceAddressDTO] = Field(default=None, description="Sender address")
    to_address: Optional[InvoiceAddressDTO] = Field(default=None, description="Recipient address")
    
    # Items
    items: Optional[List[InvoiceItemRequestDTO]] = Field(default=None, description="Invoice items")
    
    # Adjustments
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Discount percentage")
    discount_amount: Optional[Decimal] = Field(default=None, ge=0, description="Fixed discount amount")
    tax_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1, description="Overall tax percentage")
    
    # Payment terms
    payment_terms: Optional[str] = Field(default=None, max_length=500, description="Payment terms text")
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate due date is after issue date."""
        if v and values.get('issue_date') and v < values['issue_date']:
            raise ValueError('Due date must be after issue date')
        return v


class SendInvoiceRequestDTO(RequestDTO):
    """DTO for sending invoice."""
    
    send_to_emails: List[str] = Field(min_items=1, description="Email addresses to send to")
    subject: Optional[str] = Field(default=None, max_length=255, description="Email subject")
    message: Optional[str] = Field(default=None, max_length=2000, description="Email message")
    include_pdf: bool = Field(default=True, description="Include PDF attachment")
    send_copy_to_self: bool = Field(default=True, description="Send copy to sender")


class ListInvoicesRequestDTO(FilterRequestDTO, TagsMixin):
    """DTO for listing invoices with filters."""
    
    project_id: Optional[int] = Field(default=None, description="Filter by project ID")
    client_id: Optional[int] = Field(default=None, description="Filter by client ID")
    status: Optional[InvoiceStatus] = Field(default=None, description="Filter by status")
    is_overdue: Optional[bool] = Field(default=None, description="Filter overdue invoices")
    has_payments: Optional[bool] = Field(default=None, description="Filter invoices with payments")
    currency: Optional[str] = Field(default=None, description="Filter by currency")
    
    # Amount filters
    min_amount: Optional[Decimal] = Field(default=None, ge=0, description="Minimum total amount")
    max_amount: Optional[Decimal] = Field(default=None, ge=0, description="Maximum total amount")
    
    # Date filters
    issue_date_from: Optional[date] = Field(default=None, description="Filter by issue date from")
    issue_date_to: Optional[date] = Field(default=None, description="Filter by issue date to")
    due_date_from: Optional[date] = Field(default=None, description="Filter by due date from")
    due_date_to: Optional[date] = Field(default=None, description="Filter by due date to")


class SearchInvoicesRequestDTO(ListInvoicesRequestDTO):
    """DTO for searching invoices."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")


# Response DTOs
class InvoiceTotalsResponseDTO(ResponseDTO):
    """DTO for invoice totals."""
    
    subtotal: Decimal = Field(description="Subtotal before discounts and tax")
    discount_amount: Decimal = Field(description="Total discount amount")
    tax_amount: Decimal = Field(description="Total tax amount")
    total_amount: Decimal = Field(description="Final total amount")
    amount_paid: Decimal = Field(description="Amount already paid")
    balance_due: Decimal = Field(description="Remaining balance due")


class InvoiceResponseDTO(ResponseDTO, TimestampMixin, TagsMixin, NotesMixin):
    """DTO for invoice response."""
    
    # Basic info
    invoice_number: str = Field(description="Invoice number")
    owner_id: str = Field(description="Invoice owner user ID")
    project_id: int = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    client_id: int = Field(description="Client ID")
    client_name: str = Field(description="Client name")
    
    # Invoice details
    title: Optional[str] = Field(default=None, description="Invoice title")
    description: Optional[str] = Field(default=None, description="Invoice description")
    status: InvoiceStatus = Field(description="Invoice status")
    
    # Dates
    issue_date: date = Field(description="Issue date")
    due_date: date = Field(description="Due date")
    sent_at: Optional[datetime] = Field(default=None, description="When invoice was sent")
    paid_at: Optional[datetime] = Field(default=None, description="When invoice was fully paid")
    
    # Currency
    currency: str = Field(description="Invoice currency")
    
    # Addresses
    from_address: InvoiceAddressDTO = Field(description="Sender address")
    to_address: InvoiceAddressDTO = Field(description="Recipient address")
    
    # Items
    items: List[InvoiceItemResponseDTO] = Field(description="Invoice items")
    
    # Totals
    totals: InvoiceTotalsResponseDTO = Field(description="Invoice totals")
    
    # Payments
    payments: List[PaymentResponseDTO] = Field(default_factory=list, description="Invoice payments")
    
    # Payment terms
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    
    # File attachments
    pdf_url: Optional[str] = Field(default=None, description="PDF file URL")
    pdf_generated_at: Optional[datetime] = Field(default=None, description="PDF generation timestamp")
    
    # Computed fields
    is_overdue: bool = Field(description="Whether invoice is overdue")
    days_overdue: Optional[int] = Field(default=None, description="Days overdue")
    is_fully_paid: bool = Field(description="Whether invoice is fully paid")
    payment_progress: float = Field(description="Payment progress percentage (0-1)")
    
    # Sharing
    public_url: Optional[str] = Field(default=None, description="Public sharing URL")
    view_count: int = Field(description="Number of times viewed")
    last_viewed_at: Optional[datetime] = Field(default=None, description="Last viewed timestamp")


class InvoiceSummaryResponseDTO(ResponseDTO):
    """DTO for invoice summary (used in lists)."""
    
    invoice_number: str = Field(description="Invoice number")
    project_name: str = Field(description="Project name")
    client_name: str = Field(description="Client name")
    status: InvoiceStatus = Field(description="Invoice status")
    issue_date: date = Field(description="Issue date")
    due_date: date = Field(description="Due date")
    currency: str = Field(description="Currency")
    total_amount: Decimal = Field(description="Total amount")
    amount_paid: Decimal = Field(description="Amount paid")
    balance_due: Decimal = Field(description="Balance due")
    is_overdue: bool = Field(description="Whether overdue")
    days_overdue: Optional[int] = Field(default=None, description="Days overdue")
    payment_progress: float = Field(description="Payment progress (0-1)")


class InvoiceStatsResponseDTO(ResponseDTO):
    """DTO for invoice statistics."""
    
    total_invoices: int = Field(description="Total number of invoices")
    total_amount: Decimal = Field(description="Total invoiced amount")
    total_paid: Decimal = Field(description="Total amount paid")
    total_outstanding: Decimal = Field(description="Total outstanding amount")
    
    # Status breakdown
    draft_count: int = Field(description="Draft invoices count")
    sent_count: int = Field(description="Sent invoices count")
    paid_count: int = Field(description="Paid invoices count")
    overdue_count: int = Field(description="Overdue invoices count")
    
    # Financial metrics
    average_invoice_amount: Decimal = Field(description="Average invoice amount")
    average_payment_time: Optional[float] = Field(default=None, description="Average payment time in days")
    collection_rate: float = Field(description="Collection rate percentage")
    
    period_start: date = Field(description="Statistics period start")
    period_end: date = Field(description="Statistics period end")


class InvoiceReportResponseDTO(ResponseDTO):
    """DTO for invoice reports."""
    
    report_title: str = Field(description="Report title")
    report_period_start: date = Field(description="Report period start")
    report_period_end: date = Field(description="Report period end")
    generated_at: datetime = Field(description="Report generation time")
    
    # Summary metrics
    total_invoiced: Decimal = Field(description="Total amount invoiced")
    total_collected: Decimal = Field(description="Total amount collected")
    collection_rate: float = Field(description="Collection rate percentage")
    average_collection_time: Optional[float] = Field(default=None, description="Average collection time in days")
    
    # Breakdown data
    client_breakdown: List[Dict[str, Any]] = Field(description="Revenue breakdown by client")
    project_breakdown: List[Dict[str, Any]] = Field(description="Revenue breakdown by project")
    monthly_breakdown: List[Dict[str, Any]] = Field(description="Monthly revenue breakdown")
    
    # Status summary
    status_summary: Dict[str, Dict[str, Any]] = Field(description="Summary by invoice status")
    
    # Aging report
    aging_buckets: Dict[str, Dict[str, Any]] = Field(description="Aging analysis buckets")


# Bulk operation DTOs
class BulkUpdateInvoicesRequestDTO(RequestDTO):
    """DTO for bulk invoice updates."""
    
    invoice_ids: List[int] = Field(min_items=1, max_items=50, description="Invoice IDs")
    status: Optional[InvoiceStatus] = Field(default=None, description="New status")
    due_date: Optional[date] = Field(default=None, description="New due date")
    tags_to_add: Optional[List[str]] = Field(default=None, description="Tags to add")
    tags_to_remove: Optional[List[str]] = Field(default=None, description="Tags to remove")


class BulkSendInvoicesRequestDTO(RequestDTO):
    """DTO for bulk sending invoices."""
    
    invoice_ids: List[int] = Field(min_items=1, max_items=20, description="Invoice IDs to send")
    subject: Optional[str] = Field(default=None, max_length=255, description="Email subject")
    message: Optional[str] = Field(default=None, max_length=2000, description="Email message")
    include_pdf: bool = Field(default=True, description="Include PDF attachments")


# Analytics DTOs
class InvoiceAnalyticsResponseDTO(ResponseDTO):
    """DTO for invoice analytics."""
    
    # Revenue metrics
    total_revenue: Decimal = Field(description="Total revenue")
    revenue_trend: List[Dict[str, Any]] = Field(description="Revenue trend over time")
    monthly_recurring_revenue: Optional[Decimal] = Field(default=None, description="MRR if applicable")
    
    # Collection metrics
    collection_efficiency: float = Field(description="Collection efficiency score")
    average_collection_time: float = Field(description="Average collection time in days")
    collection_trend: List[Dict[str, Any]] = Field(description="Collection trend over time")
    
    # Client metrics
    top_clients_by_revenue: List[Dict[str, Any]] = Field(description="Top clients by revenue")
    client_payment_behavior: List[Dict[str, Any]] = Field(description="Client payment behavior analysis")
    
    # Invoice metrics
    average_invoice_size: Decimal = Field(description="Average invoice size")
    invoice_frequency: float = Field(description="Average invoices per month")
    
    # Overdue analysis
    overdue_analysis: Dict[str, Any] = Field(description="Overdue invoice analysis")
    risk_assessment: List[Dict[str, Any]] = Field(description="Payment risk assessment")
    
    analysis_period_start: date = Field(description="Analysis period start")
    analysis_period_end: date = Field(description="Analysis period end")
    last_calculated: datetime = Field(description="When analytics were calculated")


# Export DTOs
class ExportInvoicesRequestDTO(RequestDTO):
    """DTO for exporting invoices."""
    
    format: str = Field(description="Export format: csv, xlsx, pdf")
    start_date: date = Field(description="Export start date")
    end_date: date = Field(description="Export end date")
    client_ids: Optional[List[int]] = Field(default=None, description="Filter by client IDs")
    project_ids: Optional[List[int]] = Field(default=None, description="Filter by project IDs")
    status: Optional[InvoiceStatus] = Field(default=None, description="Filter by status")
    include_payments: bool = Field(default=True, description="Include payment details")
    include_line_items: bool = Field(default=True, description="Include line item details")
    
    @validator('format')
    def validate_format(cls, v):
        """Validate export format."""
        valid_formats = ["csv", "xlsx", "pdf"]
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {", ".join(valid_formats)}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v