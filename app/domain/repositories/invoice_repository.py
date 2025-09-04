"""Invoice repository interface.
Defines the contract for invoice data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.domain.models.invoice import Invoice, InvoiceStatus, InvoiceType, PaymentStatus
from app.domain.models.base import InvoiceNumber


class InvoiceRepository(ABC):
    """
    Repository interface for Invoice aggregate.
    Defines all operations needed for invoice data persistence.
    """

    @abstractmethod
    async def save(self, invoice: Invoice) -> Invoice:
        """
        Save an invoice entity.
        Returns the saved invoice with updated version and timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """
        Find an invoice by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def find_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Find an invoice by its number.
        Used for uniqueness checks and client lookups.
        """
        pass

    @abstractmethod
    async def find_by_client_id(self, client_id: int) -> List[Invoice]:
        """
        Find all invoices for a specific client.
        """
        pass

    @abstractmethod
    async def find_by_project_id(self, project_id: int) -> List[Invoice]:
        """
        Find all invoices for a specific project.
        """
        pass

    @abstractmethod
    async def find_by_created_by(self, user_id: str) -> List[Invoice]:
        """
        Find all invoices created by a specific user.
        """
        pass

    @abstractmethod
    async def find_by_status(self, user_id: str, status: InvoiceStatus) -> List[Invoice]:
        """
        Find all invoices with a specific status for a user.
        """
        pass

    @abstractmethod
    async def find_by_payment_status(
        self, 
        user_id: str, 
        payment_status: PaymentStatus
    ) -> List[Invoice]:
        """
        Find all invoices with a specific payment status for a user.
        """
        pass

    @abstractmethod
    async def find_by_type(self, user_id: str, invoice_type: InvoiceType) -> List[Invoice]:
        """
        Find all invoices of a specific type for a user.
        """
        pass

    @abstractmethod
    async def find_draft_invoices(self, user_id: str) -> List[Invoice]:
        """
        Find all draft invoices for a user.
        """
        pass

    @abstractmethod
    async def find_sent_invoices(self, user_id: str) -> List[Invoice]:
        """
        Find all sent (but not paid) invoices for a user.
        """
        pass

    @abstractmethod
    async def find_overdue_invoices(self, user_id: str) -> List[Invoice]:
        """
        Find all overdue invoices for a user.
        """
        pass

    @abstractmethod
    async def find_paid_invoices(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Invoice]:
        """
        Find all paid invoices for a user, optionally in a date range.
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        date_field: str = "invoice_date"
    ) -> List[Invoice]:
        """
        Find invoices within a date range.
        date_field can be 'invoice_date', 'due_date', or 'sent_date'.
        """
        pass

    @abstractmethod
    async def find_by_due_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Invoice]:
        """
        Find invoices with due dates within a range.
        """
        pass

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        status: Optional[InvoiceStatus] = None,
        client_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Invoice]:
        """
        Search invoices by query string, optionally filtered.
        Searches in invoice number, title, description, client name.
        """
        pass

    @abstractmethod
    async def get_invoice_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive invoice statistics for a user.
        Includes totals by status, revenue, outstanding amounts, etc.
        """
        pass

    @abstractmethod
    async def get_revenue_statistics(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get revenue statistics for a user in a date range.
        Includes total revenue, average invoice amount, etc.
        """
        pass

    @abstractmethod
    async def get_client_invoice_summary(self, client_id: int) -> Dict[str, Any]:
        """
        Get invoice summary for a specific client.
        Includes total invoiced, paid, outstanding amounts.
        """
        pass

    @abstractmethod
    async def get_project_invoice_summary(self, project_id: int) -> Dict[str, Any]:
        """
        Get invoice summary for a specific project.
        """
        pass

    @abstractmethod
    async def get_next_invoice_number(
        self,
        user_id: str,
        prefix: str = "INV",
        suffix: Optional[str] = None
    ) -> InvoiceNumber:
        """
        Get the next available invoice number for a user.
        """
        pass

    @abstractmethod
    async def update_invoice_number_sequence(
        self,
        user_id: str,
        prefix: str,
        next_number: int
    ) -> None:
        """
        Update the invoice number sequence for a user.
        """
        pass

    @abstractmethod
    async def mark_as_sent(
        self,
        invoice_id: int,
        sent_to_email: str,
        sent_by: str
    ) -> None:
        """
        Mark an invoice as sent and record details.
        """
        pass

    @abstractmethod
    async def mark_as_viewed(self, invoice_id: int) -> None:
        """
        Mark an invoice as viewed by the client.
        """
        pass

    @abstractmethod
    async def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_method: str,
        payment_date: date,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """
        Record a payment for an invoice.
        """
        pass

    @abstractmethod
    async def cancel_invoice(self, invoice_id: int, reason: Optional[str] = None) -> None:
        """
        Cancel an invoice.
        """
        pass

    @abstractmethod
    async def delete(self, invoice_id: int) -> bool:
        """
        Delete an invoice by ID.
        Returns True if deleted, False if not found.
        Only allowed for draft invoices with no payments.
        """
        pass

    @abstractmethod
    async def exists(self, invoice_id: int) -> bool:
        """
        Check if an invoice exists by ID.
        """
        pass

    @abstractmethod
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[InvoiceStatus] = None
    ) -> int:
        """
        Count invoices for a user, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def count_by_client(self, client_id: int) -> int:
        """
        Count invoices for a specific client.
        """
        pass

    @abstractmethod
    async def find_recently_created(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 10
    ) -> List[Invoice]:
        """
        Find recently created invoices.
        """
        pass

    @abstractmethod
    async def find_recently_paid(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 10
    ) -> List[Invoice]:
        """
        Find recently paid invoices.
        """
        pass

    @abstractmethod
    async def find_invoices_due_soon(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Invoice]:
        """
        Find invoices due within the specified number of days.
        """
        pass

    @abstractmethod
    async def get_aging_report(self, user_id: str) -> Dict[str, Any]:
        """
        Get accounts receivable aging report.
        Groups outstanding invoices by age (0-30, 31-60, 61-90, 90+ days).
        """
        pass

    @abstractmethod
    async def get_monthly_revenue_report(
        self,
        user_id: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """
        Get monthly revenue report for a year.
        Returns list of {month, revenue, invoice_count}.
        """
        pass

    @abstractmethod
    async def get_client_payment_history(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Get payment history for a client.
        Includes payment patterns and average payment time.
        """
        pass

    @abstractmethod
    async def find_duplicate_invoices(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Find potential duplicate invoices.
        Based on client, amount, date similarity.
        """
        pass

    @abstractmethod
    async def bulk_update_status(
        self,
        invoice_ids: List[int],
        new_status: InvoiceStatus,
        updated_by: str
    ) -> int:
        """
        Bulk update status for multiple invoices.
        Returns number of invoices updated.
        """
        pass

    @abstractmethod
    async def send_reminder_for_overdue(
        self,
        user_id: str,
        days_overdue: int = 7
    ) -> List[int]:
        """
        Find invoices that need payment reminders.
        Returns list of invoice IDs.
        """
        pass

    @abstractmethod
    async def auto_mark_overdue(self, user_id: str) -> int:
        """
        Automatically mark invoices as overdue based on due date.
        Returns number of invoices marked as overdue.
        """
        pass

    @abstractmethod
    async def get_tax_report(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get tax report for invoices in a date range.
        Includes total taxes collected by type and rate.
        """
        pass

    @abstractmethod
    async def archive_old_invoices(
        self,
        user_id: str,
        older_than_years: int = 7
    ) -> int:
        """
        Archive paid invoices older than specified years.
        Returns number of invoices archived.
        """
        pass

    @abstractmethod
    async def get_payment_method_statistics(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get statistics on payment methods used.
        """
        pass

    @abstractmethod
    async def find_high_value_invoices(
        self,
        user_id: str,
        threshold_amount: float
    ) -> List[Invoice]:
        """
        Find invoices above a certain amount threshold.
        """
        pass

    @abstractmethod
    async def get_average_payment_time(
        self,
        user_id: str,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get average time between invoice creation and payment.
        Optionally filtered by client.
        """
        pass