"""
Invoice use cases for the application layer.
Implements business logic for invoicing and billing operations.
"""

from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.invoice_dto import (
    CreateInvoiceRequestDTO, CreateInvoiceFromTimeRequestDTO, UpdateInvoiceRequestDTO,
    SendInvoiceRequestDTO, ListInvoicesRequestDTO, SearchInvoicesRequestDTO,
    InvoiceResponseDTO, InvoiceSummaryResponseDTO, InvoiceStatsResponseDTO,
    InvoiceReportResponseDTO, BulkUpdateInvoicesRequestDTO, BulkSendInvoicesRequestDTO,
    InvoiceAnalyticsResponseDTO, ExportInvoicesRequestDTO, InvoiceItemRequestDTO,
    InvoiceItemResponseDTO, PaymentRequestDTO, PaymentResponseDTO, InvoiceTotalsResponseDTO,
    InvoiceAddressDTO
)
from app.domain.models.invoice import (
    Invoice, InvoiceLineItem, TaxLineItem, PaymentRecord, InvoiceSettings,
    InvoiceStatus, InvoiceType, PaymentStatus, PaymentMethod
)
from app.domain.repositories.invoice_repository import InvoiceRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.time_entry_repository import TimeEntryRepository
from app.domain.services.billing_service import BillingService
from app.domain.services.invoice_service import InvoiceService


class CreateInvoiceUseCase(AuthorizedUseCase, CreateUseCase[CreateInvoiceRequestDTO, InvoiceResponseDTO]):
    """Use case for creating a new invoice."""
    
    def __init__(
        self, 
        invoice_repository: InvoiceRepository,
        client_repository: ClientRepository,
        billing_service: BillingService
    ):
        super().__init__()
        self.invoice_repository = invoice_repository
        self.client_repository = client_repository
        self.billing_service = billing_service
    
    async def _execute_command_logic(self, request: CreateInvoiceRequestDTO) -> InvoiceResponseDTO:
        # Verify client exists and user has access
        client = await self.client_repository.find_by_id(request.client_id)
        if not client:
            raise ValueError("Client not found")
        
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Generate invoice number
        invoice_number = await self.billing_service.generate_invoice_number(self.current_user_id)
        
        # Create line items
        line_items = []
        for item_req in request.items:
            line_items.append(InvoiceLineItem(
                description=item_req.description,
                quantity=item_req.quantity,
                unit_price=item_req.unit_price,
                discount_percentage=item_req.discount_percentage,
                tax_rate=item_req.tax_rate,
                item_type=item_req.item_type
            ))
        
        # Create tax line items
        tax_items = []
        for tax_req in request.tax_items or []:
            tax_items.append(TaxLineItem(
                name=tax_req.name,
                rate=tax_req.rate,
                amount=tax_req.amount
            ))
        
        # Create invoice
        invoice = Invoice.create(
            owner_id=self.current_user_id,
            client_id=request.client_id,
            project_id=request.project_id,
            invoice_number=invoice_number,
            invoice_type=request.invoice_type or InvoiceType.STANDARD,
            currency=request.currency or client.default_currency,
            issue_date=request.issue_date or date.today(),
            due_date=request.due_date,
            title=request.title,
            description=request.description,
            line_items=line_items,
            tax_items=tax_items,
            discount_percentage=request.discount_percentage,
            notes=request.notes,
            terms=request.terms
        )
        
        # Set addresses
        if request.billing_address:
            invoice.set_billing_address(
                name=request.billing_address.name,
                address_line_1=request.billing_address.address_line_1,
                address_line_2=request.billing_address.address_line_2,
                city=request.billing_address.city,
                state=request.billing_address.state,
                postal_code=request.billing_address.postal_code,
                country=request.billing_address.country
            )
        
        if request.shipping_address:
            invoice.set_shipping_address(
                name=request.shipping_address.name,
                address_line_1=request.shipping_address.address_line_1,
                address_line_2=request.shipping_address.address_line_2,
                city=request.shipping_address.city,
                state=request.shipping_address.state,
                postal_code=request.shipping_address.postal_code,
                country=request.shipping_address.country
            )
        
        # Save invoice
        saved_invoice = await self.invoice_repository.save(invoice)
        
        return await self._invoice_to_response_dto(saved_invoice)


class CreateInvoiceFromTimeUseCase(AuthorizedUseCase, CreateUseCase[CreateInvoiceFromTimeRequestDTO, InvoiceResponseDTO]):
    """Use case for creating an invoice from time entries."""
    
    def __init__(
        self, 
        invoice_repository: InvoiceRepository,
        client_repository: ClientRepository,
        project_repository: ProjectRepository,
        time_entry_repository: TimeEntryRepository,
        billing_service: BillingService
    ):
        super().__init__()
        self.invoice_repository = invoice_repository
        self.client_repository = client_repository
        self.project_repository = project_repository
        self.time_entry_repository = time_entry_repository
        self.billing_service = billing_service
    
    async def _execute_command_logic(self, request: CreateInvoiceFromTimeRequestDTO) -> InvoiceResponseDTO:
        # Verify client exists and user has access
        client = await self.client_repository.find_by_id(request.client_id)
        if not client:
            raise ValueError("Client not found")
        
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Verify project if provided
        project = None
        if request.project_id:
            project = await self.project_repository.find_by_id(request.project_id)
            if not project or project.client_id != request.client_id:
                raise ValueError("Project not found or not associated with client")
        
        # Get time entries to invoice
        time_entries = await self.time_entry_repository.find_billable_entries(
            client_id=request.client_id,
            project_id=request.project_id,
            user_id=request.user_id,
            date_from=request.date_from,
            date_to=request.date_to,
            time_entry_ids=request.time_entry_ids
        )
        
        if not time_entries:
            raise ValueError("No billable time entries found")
        
        # Create invoice from time entries
        invoice = await self.billing_service.create_invoice_from_time_entries(
            owner_id=self.current_user_id,
            client_id=request.client_id,
            project_id=request.project_id,
            time_entries=time_entries,
            invoice_date=request.invoice_date or date.today(),
            due_date=request.due_date,
            title=request.title,
            description=request.description,
            group_by_task=request.group_by_task,
            group_by_user=request.group_by_user,
            include_time_details=request.include_time_details,
            notes=request.notes
        )
        
        # Save invoice
        saved_invoice = await self.invoice_repository.save(invoice)
        
        return await self._invoice_to_response_dto(saved_invoice)


class UpdateInvoiceUseCase(AuthorizedUseCase, UpdateUseCase[UpdateInvoiceRequestDTO, InvoiceResponseDTO]):
    """Use case for updating an invoice."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _check_authorization(self, request: UpdateInvoiceRequestDTO) -> None:
        if hasattr(request, 'id'):
            invoice = await self.invoice_repository.find_by_id(request.id)
            if invoice:
                self._require_owner_or_role(invoice.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateInvoiceRequestDTO) -> InvoiceResponseDTO:
        # Get invoice
        invoice = await self.invoice_repository.find_by_id(request.id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Check if invoice can be edited
        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            raise ValueError("Cannot edit paid or cancelled invoices")
        
        # Update basic fields
        if request.title is not None:
            invoice.title = request.title
        if request.description is not None:
            invoice.description = request.description
        if request.issue_date is not None:
            invoice.issue_date = request.issue_date
        if request.due_date is not None:
            invoice.due_date = request.due_date
        if request.notes is not None:
            invoice.notes = request.notes
        if request.terms is not None:
            invoice.terms = request.terms
        if request.discount_percentage is not None:
            invoice.discount_percentage = request.discount_percentage
        
        # Update line items if provided
        if request.items is not None:
            new_line_items = []
            for item_req in request.items:
                new_line_items.append(InvoiceLineItem(
                    description=item_req.description,
                    quantity=item_req.quantity,
                    unit_price=item_req.unit_price,
                    discount_percentage=item_req.discount_percentage,
                    tax_rate=item_req.tax_rate,
                    item_type=item_req.item_type
                ))
            invoice.update_line_items(new_line_items)
        
        # Update tax items if provided
        if request.tax_items is not None:
            new_tax_items = []
            for tax_req in request.tax_items:
                new_tax_items.append(TaxLineItem(
                    name=tax_req.name,
                    rate=tax_req.rate,
                    amount=tax_req.amount
                ))
            invoice.tax_items = new_tax_items
        
        # Update addresses
        if request.billing_address is not None:
            invoice.set_billing_address(
                name=request.billing_address.name,
                address_line_1=request.billing_address.address_line_1,
                address_line_2=request.billing_address.address_line_2,
                city=request.billing_address.city,
                state=request.billing_address.state,
                postal_code=request.billing_address.postal_code,
                country=request.billing_address.country
            )
        
        if request.shipping_address is not None:
            invoice.set_shipping_address(
                name=request.shipping_address.name,
                address_line_1=request.shipping_address.address_line_1,
                address_line_2=request.shipping_address.address_line_2,
                city=request.shipping_address.city,
                state=request.shipping_address.state,
                postal_code=request.shipping_address.postal_code,
                country=request.shipping_address.country
            )
        
        # Save invoice
        saved_invoice = await self.invoice_repository.save(invoice)
        
        return await self._invoice_to_response_dto(saved_invoice)


class SendInvoiceUseCase(AuthorizedUseCase, UpdateUseCase[SendInvoiceRequestDTO, InvoiceResponseDTO]):
    """Use case for sending an invoice to the client."""
    
    def __init__(
        self, 
        invoice_repository: InvoiceRepository,
        invoice_service: InvoiceService
    ):
        super().__init__()
        self.invoice_repository = invoice_repository
        self.invoice_service = invoice_service
    
    async def _execute_command_logic(self, request: SendInvoiceRequestDTO) -> InvoiceResponseDTO:
        # Get invoice
        invoice = await self.invoice_repository.find_by_id(request.id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Check authorization
        self._require_owner_or_role(invoice.owner_id, "admin")
        
        # Send invoice
        await self.invoice_service.send_invoice(
            invoice=invoice,
            recipient_email=request.recipient_email,
            subject=request.subject,
            message=request.message,
            send_copy_to_self=request.send_copy_to_self,
            schedule_send=request.schedule_send
        )
        
        # Update invoice status
        invoice.send(sent_to=request.recipient_email)
        
        # Save invoice
        saved_invoice = await self.invoice_repository.save(invoice)
        
        return await self._invoice_to_response_dto(saved_invoice)


class RecordPaymentUseCase(AuthorizedUseCase, CreateUseCase[PaymentRequestDTO, PaymentResponseDTO]):
    """Use case for recording a payment against an invoice."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_command_logic(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        # Get invoice
        invoice = await self.invoice_repository.find_by_id(request.invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Check authorization
        self._require_owner_or_role(invoice.owner_id, "admin")
        
        # Record payment
        payment = invoice.record_payment(
            amount=request.amount,
            payment_date=request.payment_date or date.today(),
            payment_method=request.payment_method,
            reference=request.reference,
            notes=request.notes
        )
        
        # Save invoice
        await self.invoice_repository.save(invoice)
        
        return PaymentResponseDTO(
            id=payment.id,
            invoice_id=invoice.id,
            amount=payment.amount,
            payment_date=payment.payment_date,
            payment_method=payment.payment_method,
            reference=payment.reference,
            notes=payment.notes,
            created_at=payment.created_at
        )


class GetInvoiceByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, InvoiceResponseDTO]):
    """Use case for getting invoice by ID."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_business_logic(self, invoice_id: int) -> InvoiceResponseDTO:
        invoice = await self.invoice_repository.find_by_id(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Check authorization
        self._require_owner_or_role(invoice.owner_id, "admin")
        
        return await self._invoice_to_response_dto(invoice)


class ListInvoicesUseCase(AuthorizedUseCase, ListUseCase[ListInvoicesRequestDTO, InvoiceSummaryResponseDTO]):
    """Use case for listing invoices with filters."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_business_logic(self, request: ListInvoicesRequestDTO) -> List[InvoiceSummaryResponseDTO]:
        invoices = await self.invoice_repository.find_with_filters(
            owner_id=self.current_user_id,
            client_id=request.client_id,
            project_id=request.project_id,
            status=request.status,
            payment_status=request.payment_status,
            invoice_type=request.invoice_type,
            is_overdue=request.is_overdue,
            currency=request.currency,
            issue_date_from=request.issue_date_from,
            issue_date_to=request.issue_date_to,
            due_date_from=request.due_date_from,
            due_date_to=request.due_date_to,
            search=request.search,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [await self._invoice_to_summary_dto(invoice) for invoice in invoices]


class SearchInvoicesUseCase(AuthorizedUseCase, SearchUseCase[SearchInvoicesRequestDTO, InvoiceSummaryResponseDTO]):
    """Use case for searching invoices."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_business_logic(self, request: SearchInvoicesRequestDTO) -> List[InvoiceSummaryResponseDTO]:
        invoices = await self.invoice_repository.search_invoices(
            owner_id=self.current_user_id,
            query=request.query,
            client_id=request.client_id,
            status=request.status,
            payment_status=request.payment_status,
            date_from=request.date_from,
            date_to=request.date_to,
            page=request.page,
            page_size=request.page_size
        )
        
        return [await self._invoice_to_summary_dto(invoice) for invoice in invoices]


class DeleteInvoiceUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting an invoice."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_command_logic(self, invoice_id: int) -> bool:
        # Get invoice
        invoice = await self.invoice_repository.find_by_id(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Check authorization
        self._require_owner_or_role(invoice.owner_id, "admin")
        
        # Check if invoice can be deleted
        if invoice.status in [InvoiceStatus.SENT, InvoiceStatus.PAID]:
            raise ValueError("Cannot delete sent or paid invoices")
        
        if invoice.payments:
            raise ValueError("Cannot delete invoices with payments")
        
        # Delete invoice
        await self.invoice_repository.delete(invoice_id)
        
        return True


class BulkUpdateInvoicesUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateInvoicesRequestDTO, dict]):
    """Use case for bulk updating invoices."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_business_logic(self, request: BulkUpdateInvoicesRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for invoice_id in request.invoice_ids:
            try:
                # Get invoice
                invoice = await self.invoice_repository.find_by_id(invoice_id)
                if not invoice:
                    results["errors"].append({"id": invoice_id, "error": "Invoice not found"})
                    continue
                
                # Check authorization
                if invoice.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": invoice_id, "error": "Insufficient permissions"})
                    continue
                
                # Check if invoice can be edited
                if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
                    results["errors"].append({"id": invoice_id, "error": "Cannot edit paid or cancelled invoices"})
                    continue
                
                # Apply updates
                if request.status is not None:
                    invoice.status = request.status
                if request.due_date is not None:
                    invoice.due_date = request.due_date
                if request.notes is not None:
                    invoice.notes = request.notes
                
                # Save invoice
                await self.invoice_repository.save(invoice)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": invoice_id, "error": str(e)})
        
        return results


class BulkSendInvoicesUseCase(AuthorizedUseCase, BulkUseCase[BulkSendInvoicesRequestDTO, dict]):
    """Use case for bulk sending invoices."""
    
    def __init__(
        self, 
        invoice_repository: InvoiceRepository,
        invoice_service: InvoiceService
    ):
        super().__init__()
        self.invoice_repository = invoice_repository
        self.invoice_service = invoice_service
    
    async def _execute_business_logic(self, request: BulkSendInvoicesRequestDTO) -> dict:
        results = {"sent": 0, "errors": []}
        
        for invoice_id in request.invoice_ids:
            try:
                # Get invoice
                invoice = await self.invoice_repository.find_by_id(invoice_id)
                if not invoice:
                    results["errors"].append({"id": invoice_id, "error": "Invoice not found"})
                    continue
                
                # Check authorization
                if invoice.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": invoice_id, "error": "Insufficient permissions"})
                    continue
                
                # Check if invoice can be sent
                if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
                    results["errors"].append({"id": invoice_id, "error": "Cannot send paid or cancelled invoices"})
                    continue
                
                # Send invoice
                await self.invoice_service.send_invoice(
                    invoice=invoice,
                    recipient_email=request.recipient_email,
                    subject=request.subject,
                    message=request.message,
                    send_copy_to_self=request.send_copy_to_self
                )
                
                # Update invoice status
                invoice.send(sent_to=request.recipient_email)
                await self.invoice_repository.save(invoice)
                
                results["sent"] += 1
                
            except Exception as e:
                results["errors"].append({"id": invoice_id, "error": str(e)})
        
        return results


class GetInvoiceStatsUseCase(AuthorizedUseCase, GetByIdUseCase[int, InvoiceStatsResponseDTO]):
    """Use case for getting invoice statistics."""
    
    def __init__(self, invoice_repository: InvoiceRepository):
        super().__init__()
        self.invoice_repository = invoice_repository
    
    async def _execute_business_logic(self, user_id: int) -> InvoiceStatsResponseDTO:
        # Check authorization
        if user_id != self.current_user_id:
            self._require_role("admin")
        
        # Get stats
        stats = await self.invoice_repository.get_invoice_stats(user_id)
        
        return InvoiceStatsResponseDTO(
            total_invoices=stats.total_invoices,
            draft_invoices=stats.draft_invoices,
            sent_invoices=stats.sent_invoices,
            paid_invoices=stats.paid_invoices,
            overdue_invoices=stats.overdue_invoices,
            cancelled_invoices=stats.cancelled_invoices,
            total_amount=stats.total_amount,
            paid_amount=stats.paid_amount,
            outstanding_amount=stats.outstanding_amount,
            overdue_amount=stats.overdue_amount,
            avg_payment_time_days=stats.avg_payment_time_days,
            total_revenue_this_month=stats.total_revenue_this_month,
            total_revenue_last_month=stats.total_revenue_last_month,
            revenue_growth_percentage=stats.revenue_growth_percentage
        )


class GetInvoiceAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[int, InvoiceAnalyticsResponseDTO]):
    """Use case for getting invoice analytics."""
    
    def __init__(
        self, 
        invoice_repository: InvoiceRepository,
        billing_service: BillingService
    ):
        super().__init__()
        self.invoice_repository = invoice_repository
        self.billing_service = billing_service
    
    async def _execute_business_logic(self, user_id: int) -> InvoiceAnalyticsResponseDTO:
        # Check authorization
        if user_id != self.current_user_id:
            self._require_role("admin")
        
        # Get analytics
        analytics = await self.billing_service.get_invoice_analytics(user_id)
        
        return InvoiceAnalyticsResponseDTO(
            user_id=user_id,
            period_months=12,
            revenue_trend=analytics.revenue_trend,
            payment_behavior=analytics.payment_behavior,
            client_breakdown=analytics.client_breakdown,
            project_breakdown=analytics.project_breakdown,
            currency_breakdown=analytics.currency_breakdown,
            seasonal_patterns=analytics.seasonal_patterns,
            collection_metrics=analytics.collection_metrics,
            performance_indicators=analytics.performance_indicators
        )


    async def _invoice_to_response_dto(self, invoice: Invoice) -> InvoiceResponseDTO:
        """Convert Invoice domain model to response DTO."""
        # Get client info
        client = await self.client_repository.find_by_id(invoice.client_id) if hasattr(self, 'client_repository') else None
        
        # Get project info
        project = None
        if invoice.project_id and hasattr(self, 'project_repository'):
            project = await self.project_repository.find_by_id(invoice.project_id)
        
        # Convert line items
        line_items = []
        for item in invoice.line_items:
            line_items.append(InvoiceItemResponseDTO(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percentage=item.discount_percentage,
                tax_rate=item.tax_rate,
                subtotal=item.subtotal,
                tax_amount=item.tax_amount,
                total=item.total,
                item_type=item.item_type
            ))
        
        # Convert payments
        payments = []
        for payment in invoice.payments:
            payments.append(PaymentResponseDTO(
                id=payment.id,
                invoice_id=invoice.id,
                amount=payment.amount,
                payment_date=payment.payment_date,
                payment_method=payment.payment_method,
                reference=payment.reference,
                notes=payment.notes,
                created_at=payment.created_at
            ))
        
        # Convert addresses
        billing_address = None
        if invoice.billing_address:
            billing_address = InvoiceAddressDTO(
                name=invoice.billing_address.name,
                address_line_1=invoice.billing_address.address_line_1,
                address_line_2=invoice.billing_address.address_line_2,
                city=invoice.billing_address.city,
                state=invoice.billing_address.state,
                postal_code=invoice.billing_address.postal_code,
                country=invoice.billing_address.country
            )
        
        shipping_address = None
        if invoice.shipping_address:
            shipping_address = InvoiceAddressDTO(
                name=invoice.shipping_address.name,
                address_line_1=invoice.shipping_address.address_line_1,
                address_line_2=invoice.shipping_address.address_line_2,
                city=invoice.shipping_address.city,
                state=invoice.shipping_address.state,
                postal_code=invoice.shipping_address.postal_code,
                country=invoice.shipping_address.country
            )
        
        # Calculate totals
        totals = InvoiceTotalsResponseDTO(
            subtotal=invoice.subtotal,
            discount_amount=invoice.discount_amount,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            paid_amount=invoice.paid_amount,
            balance_due=invoice.balance_due
        )
        
        return InvoiceResponseDTO(
            id=invoice.id,
            owner_id=invoice.owner_id,
            client_id=invoice.client_id,
            client_name=client.name if client else "",
            project_id=invoice.project_id,
            project_name=project.name if project else None,
            invoice_number=invoice.invoice_number,
            invoice_type=invoice.invoice_type,
            status=invoice.status,
            payment_status=invoice.payment_status,
            currency=invoice.currency,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            sent_date=invoice.sent_date,
            paid_date=invoice.paid_date,
            title=invoice.title,
            description=invoice.description,
            line_items=line_items,
            tax_items=invoice.tax_items,
            discount_percentage=invoice.discount_percentage,
            notes=invoice.notes,
            terms=invoice.terms,
            billing_address=billing_address,
            shipping_address=shipping_address,
            payments=payments,
            totals=totals,
            is_overdue=invoice.is_overdue,
            days_overdue=invoice.days_overdue,
            can_be_sent=invoice.can_be_sent,
            can_be_edited=invoice.can_be_edited,
            can_be_deleted=invoice.can_be_deleted,
            pdf_url=invoice.pdf_url,
            public_url=invoice.public_url,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at
        )
    
    async def _invoice_to_summary_dto(self, invoice: Invoice) -> InvoiceSummaryResponseDTO:
        """Convert Invoice domain model to summary DTO."""
        # Get client info
        client = await self.client_repository.find_by_id(invoice.client_id) if hasattr(self, 'client_repository') else None
        
        return InvoiceSummaryResponseDTO(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            client_name=client.name if client else "",
            status=invoice.status,
            payment_status=invoice.payment_status,
            currency=invoice.currency,
            total_amount=invoice.total_amount,
            paid_amount=invoice.paid_amount,
            balance_due=invoice.balance_due,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            is_overdue=invoice.is_overdue,
            days_overdue=invoice.days_overdue,
            created_at=invoice.created_at
        )