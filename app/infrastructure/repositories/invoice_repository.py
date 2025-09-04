"""
Invoice repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc

from app.domain.models.invoice import Invoice
from app.domain.repositories.invoice_repository import InvoiceRepository as InvoiceRepositoryInterface
from app.domain.models.base import EntityNotFoundError, DuplicateEntityError
from app.infrastructure.db.models import InvoiceModel
from app.infrastructure.mappers.invoice_mapper import InvoiceMapper


class SQLAlchemyInvoiceRepository(InvoiceRepositoryInterface):
    """SQLAlchemy implementation of invoice repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = InvoiceMapper()
    
    def save(self, invoice: Invoice) -> Invoice:
        """Save an invoice entity."""
        if invoice.is_new:
            # Check for duplicate invoice number within owner
            existing = self.session.query(InvoiceModel).filter_by(
                owner_id=invoice.owner_id,
                invoice_number=invoice.invoice_number
            ).first()
            if existing:
                raise DuplicateEntityError("Invoice", "invoice_number", invoice.invoice_number)
            
            # Create new invoice
            model = self.mapper.domain_to_model(invoice)
            self.session.add(model)
        else:
            # Update existing invoice
            model = self.session.query(InvoiceModel).filter_by(
                id=invoice.id
            ).first()
            if not model:
                raise EntityNotFoundError("Invoice", invoice.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(invoice)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated invoice with ID
        if invoice.is_new:
            invoice.id = model.id
        return invoice
    
    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID."""
        model = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project),
            joinedload(InvoiceModel.line_items),
            joinedload(InvoiceModel.tax_items),
            joinedload(InvoiceModel.payment_records)
        ).filter_by(id=invoice_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_number(self, owner_id: str, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by number."""
        model = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project),
            joinedload(InvoiceModel.line_items),
            joinedload(InvoiceModel.tax_items),
            joinedload(InvoiceModel.payment_records)
        ).filter_by(
            owner_id=owner_id,
            invoice_number=invoice_number
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_owner(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Invoice]:
        """Get invoices by owner with optional pagination."""
        query = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter_by(owner_id=owner_id).order_by(desc(InvoiceModel.issue_date))
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_client(self, client_id: int, limit: Optional[int] = None) -> List[Invoice]:
        """Get invoices by client."""
        query = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter_by(client_id=client_id).order_by(desc(InvoiceModel.issue_date))
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_project(self, project_id: int) -> List[Invoice]:
        """Get invoices by project."""
        models = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter_by(project_id=project_id).order_by(desc(InvoiceModel.issue_date)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, invoice_id: int) -> bool:
        """Delete invoice by ID."""
        model = self.session.query(InvoiceModel).filter_by(
            id=invoice_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count_by_owner(self, owner_id: str) -> int:
        """Get invoice count for owner."""
        return self.session.query(func.count(InvoiceModel.id)).filter_by(
            owner_id=owner_id
        ).scalar()
    
    def get_by_status(self, owner_id: str, status: str) -> List[Invoice]:
        """Get invoices by status."""
        models = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter_by(
            owner_id=owner_id,
            status=status
        ).order_by(desc(InvoiceModel.issue_date)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_payment_status(self, owner_id: str, payment_status: str) -> List[Invoice]:
        """Get invoices by payment status."""
        models = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter_by(
            owner_id=owner_id,
            payment_status=payment_status
        ).order_by(desc(InvoiceModel.issue_date)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_overdue_invoices(self, owner_id: str) -> List[Invoice]:
        """Get overdue invoices."""
        from datetime import date
        
        models = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter(
            and_(
                InvoiceModel.owner_id == owner_id,
                InvoiceModel.due_date < date.today(),
                InvoiceModel.payment_status != 'paid'
            )
        ).order_by(InvoiceModel.due_date).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_date_range(self, owner_id: str, start_date: date, end_date: date) -> List[Invoice]:
        """Get invoices within date range."""
        models = self.session.query(InvoiceModel).options(
            joinedload(InvoiceModel.client),
            joinedload(InvoiceModel.project)
        ).filter(
            and_(
                InvoiceModel.owner_id == owner_id,
                InvoiceModel.issue_date >= start_date,
                InvoiceModel.issue_date <= end_date
            )
        ).order_by(desc(InvoiceModel.issue_date)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_next_invoice_number(self, owner_id: str) -> int:
        """Get next invoice number for owner."""
        last_number = self.session.query(func.max(InvoiceModel.invoice_number)).filter_by(
            owner_id=owner_id
        ).scalar()
        
        if last_number and last_number.isdigit():
            return int(last_number) + 1
        
        return 1
    
    def get_total_revenue_by_owner(self, owner_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> float:
        """Get total revenue for owner."""
        query = self.session.query(func.sum(InvoiceModel.total_amount)).filter(
            and_(
                InvoiceModel.owner_id == owner_id,
                InvoiceModel.payment_status == 'paid'
            )
        )
        
        if start_date:
            query = query.filter(InvoiceModel.issue_date >= start_date)
        
        if end_date:
            query = query.filter(InvoiceModel.issue_date <= end_date)
        
        result = query.scalar()
        return result or 0.0