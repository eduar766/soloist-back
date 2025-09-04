"""
Invoice mapper for converting between domain entities and database models.
"""

import json
from typing import List, Optional

from app.domain.models.invoice import (
    Invoice, LineItem, TaxItem, PaymentRecord,
    InvoiceStatus, PaymentStatus, PaymentMethod
)
from app.infrastructure.db.models import (
    InvoiceModel, InvoiceLineItemModel, 
    TaxLineItemModel, PaymentRecordModel
)


class InvoiceMapper:
    """Maps between Invoice domain entity and InvoiceModel database model."""
    
    def domain_to_model(self, invoice: Invoice) -> InvoiceModel:
        """Convert Invoice domain entity to InvoiceModel."""
        return InvoiceModel(
            id=invoice.id,
            owner_id=invoice.owner_id,
            client_id=invoice.client_id,
            project_id=invoice.project_id,
            invoice_number=invoice.invoice_number,
            status=invoice.status.value,
            payment_status=invoice.payment_status.value,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            subtotal_amount=invoice.subtotal_amount,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            currency=invoice.currency,
            notes=invoice.notes,
            payment_terms=invoice.payment_terms,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            version=invoice.version
        )
    
    def model_to_domain(self, model: InvoiceModel) -> Invoice:
        """Convert InvoiceModel to Invoice domain entity."""
        # Convert line items
        line_items = []
        if hasattr(model, 'line_items') and model.line_items:
            line_items = [self._line_item_model_to_domain(item) for item in model.line_items]
        
        # Convert tax items
        tax_items = []
        if hasattr(model, 'tax_items') and model.tax_items:
            tax_items = [self._tax_item_model_to_domain(item) for item in model.tax_items]
        
        # Convert payment records
        payment_records = []
        if hasattr(model, 'payment_records') and model.payment_records:
            payment_records = [self._payment_record_model_to_domain(record) for record in model.payment_records]
        
        invoice = Invoice(
            owner_id=model.owner_id,
            client_id=model.client_id,
            project_id=model.project_id,
            invoice_number=model.invoice_number,
            status=InvoiceStatus(model.status) if model.status else InvoiceStatus.DRAFT,
            payment_status=PaymentStatus(model.payment_status) if model.payment_status else PaymentStatus.PENDING,
            issue_date=model.issue_date,
            due_date=model.due_date,
            subtotal_amount=model.subtotal_amount or 0.0,
            tax_amount=model.tax_amount or 0.0,
            total_amount=model.total_amount or 0.0,
            currency=model.currency or "USD",
            notes=model.notes,
            payment_terms=model.payment_terms,
            line_items=line_items,
            tax_items=tax_items,
            payment_records=payment_records
        )
        
        # Set entity metadata
        invoice.id = model.id
        invoice.created_at = model.created_at
        invoice.updated_at = model.updated_at
        invoice.version = model.version or 1
        
        return invoice
    
    def _line_item_model_to_domain(self, model: InvoiceLineItemModel) -> LineItem:
        """Convert line item model to domain."""
        return LineItem(
            description=model.description,
            quantity=model.quantity,
            unit_price=model.unit_price,
            total_amount=model.total_amount,
            time_entry_id=model.time_entry_id
        )
    
    def _tax_item_model_to_domain(self, model: TaxLineItemModel) -> TaxItem:
        """Convert tax item model to domain."""
        return TaxItem(
            name=model.name,
            rate=model.rate,
            amount=model.amount
        )
    
    def _payment_record_model_to_domain(self, model: PaymentRecordModel) -> PaymentRecord:
        """Convert payment record model to domain."""
        return PaymentRecord(
            amount=model.amount,
            payment_date=model.payment_date,
            payment_method=PaymentMethod(model.payment_method) if model.payment_method else PaymentMethod.BANK_TRANSFER,
            reference=model.reference,
            notes=model.notes
        )