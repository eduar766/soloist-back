"""
Invoice management router.
Handles invoice creation, management, payment tracking, and PDF generation.
"""

from typing import Annotated, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse

from app.infrastructure.auth import get_current_user_id
from app.application.use_cases.invoice import (
    CreateInvoiceUseCase,
    UpdateInvoiceUseCase,
    GetInvoiceUseCase,
    ListInvoicesUseCase,
    DeleteInvoiceUseCase,
    SendInvoiceUseCase,
    MarkInvoicePaidUseCase,
    GenerateInvoicePDFUseCase,
    DuplicateInvoiceUseCase
)
from app.application.dto.invoice import (
    CreateInvoiceRequest,
    UpdateInvoiceRequest,
    InvoiceResponse,
    InvoiceListResponse,
    InvoicePaymentRequest
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.invoice_repository import SQLAlchemyInvoiceRepository
from app.domain.models.base import EntityNotFoundError, ValidationError, BusinessRuleViolation


router = APIRouter()


def get_invoice_repository(session=Depends(get_db_session)):
    """Dependency to get invoice repository."""
    return SQLAlchemyInvoiceRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvoiceResponse)
async def create_invoice(
    request: CreateInvoiceRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Create a new invoice.
    
    - **client_id**: Client to invoice (required)
    - **project_id**: Associated project (optional)
    - **invoice_number**: Invoice number (auto-generated if not provided)
    - **issue_date**: Invoice issue date (default: today)
    - **due_date**: Payment due date (required)
    - **currency**: Invoice currency (default: USD)
    - **tax_rate**: Tax percentage (default: 0)
    - **discount_amount**: Discount amount (default: 0)
    - **notes**: Additional notes
    - **terms**: Payment terms and conditions
    - **line_items**: List of invoice line items
    - **time_entry_ids**: Time entries to include (optional)
    """
    try:
        use_case = CreateInvoiceUseCase(repository)
        invoice = await use_case.execute(user_id, request)
        return InvoiceResponse.from_domain(invoice)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)],
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    overdue: bool = Query(False, description="Show only overdue invoices"),
    limit: int = Query(50, ge=1, le=100, description="Number of invoices to return"),
    offset: int = Query(0, ge=0, description="Number of invoices to skip")
):
    """
    List invoices for the authenticated user.
    
    - **client_id**: Filter by specific client
    - **project_id**: Filter by specific project
    - **status**: Filter by invoice status (draft, sent, paid, overdue, cancelled)
    - **start_date**: Filter from this issue date
    - **end_date**: Filter to this issue date
    - **overdue**: Show only overdue invoices
    - **limit**: Maximum number of invoices to return (1-100, default 50)
    - **offset**: Number of invoices to skip for pagination
    """
    try:
        use_case = ListInvoicesUseCase(repository)
        
        if client_id:
            invoices = await use_case.list_by_client(client_id, limit, offset)
            total = await use_case.count_by_client(client_id)
        elif project_id:
            invoices = await use_case.list_by_project(project_id, limit, offset)
            total = await use_case.count_by_project(project_id)
        elif overdue:
            invoices = await use_case.list_overdue(user_id, limit)
            total = len(invoices)
        elif status:
            invoices = await use_case.list_by_status(user_id, status, limit, offset)
            total = await use_case.count_by_status(user_id, status)
        else:
            invoices = await use_case.execute(user_id, start_date, end_date, limit, offset)
            total = await use_case.get_total_count(user_id, start_date, end_date)
        
        return InvoiceListResponse(
            invoices=[InvoiceResponse.from_domain(invoice) for invoice in invoices],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Get a specific invoice by ID.
    
    - **invoice_id**: Invoice ID to retrieve
    """
    try:
        use_case = GetInvoiceUseCase(repository)
        invoice = await use_case.execute(user_id, invoice_id)
        return InvoiceResponse.from_domain(invoice)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    request: UpdateInvoiceRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Update an existing invoice.
    
    - **invoice_id**: Invoice ID to update
    - **due_date**: Updated due date
    - **currency**: Updated currency
    - **tax_rate**: Updated tax rate
    - **discount_amount**: Updated discount
    - **notes**: Updated notes
    - **terms**: Updated payment terms
    - **line_items**: Updated line items
    """
    try:
        use_case = UpdateInvoiceUseCase(repository)
        invoice = await use_case.execute(user_id, invoice_id, request)
        return InvoiceResponse.from_domain(invoice)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )
    except (ValidationError, BusinessRuleViolation) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Delete an invoice (only allowed for draft invoices).
    
    - **invoice_id**: Invoice ID to delete
    """
    try:
        use_case = DeleteInvoiceUseCase(repository)
        await use_case.execute(user_id, invoice_id)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )
    except BusinessRuleViolation as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Send an invoice to the client via email.
    
    - **invoice_id**: Invoice ID to send
    """
    try:
        use_case = SendInvoiceUseCase(repository)
        invoice = await use_case.execute(user_id, invoice_id)
        return InvoiceResponse.from_domain(invoice)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )
    except BusinessRuleViolation as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: int,
    request: InvoicePaymentRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Mark an invoice as paid.
    
    - **invoice_id**: Invoice ID to mark as paid
    - **payment_date**: Date when payment was received
    - **payment_method**: Method of payment (bank transfer, card, etc.)
    - **payment_reference**: Reference number or transaction ID
    - **notes**: Additional payment notes
    """
    try:
        use_case = MarkInvoicePaidUseCase(repository)
        invoice = await use_case.execute(user_id, invoice_id, request)
        return InvoiceResponse.from_domain(invoice)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )
    except BusinessRuleViolation as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{invoice_id}/duplicate", response_model=InvoiceResponse)
async def duplicate_invoice(
    invoice_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)]
):
    """
    Create a duplicate of an existing invoice.
    
    - **invoice_id**: Invoice ID to duplicate
    """
    try:
        use_case = DuplicateInvoiceUseCase(repository)
        invoice = await use_case.execute(user_id, invoice_id)
        return InvoiceResponse.from_domain(invoice)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)],
    template: Optional[str] = Query("professional", description="Template theme"),
    download: bool = Query(True, description="Force download vs display"),
    include_time_entries: bool = Query(True, description="Include time entries")
):
    """
    Generate and download invoice PDF.
    
    - **invoice_id**: Invoice ID to generate PDF for
    - **template**: Template theme (professional, minimal, modern, creative)
    - **download**: Force download vs display in browser
    - **include_time_entries**: Include related time entries
    """
    try:
        # Import here to avoid circular imports
        from app.application.use_cases.generate_pdf_use_case import (
            GenerateInvoicePDFUseCase,
            GenerateInvoicePDFRequest
        )
        from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
        from app.infrastructure.repositories.project_repository import SQLAlchemyProjectRepository
        from app.infrastructure.repositories.time_entry_repository import SQLAlchemyTimeEntryRepository
        from app.infrastructure.db.database import get_db_session
        
        # Get additional repositories
        session = next(get_db_session())
        client_repo = SQLAlchemyClientRepository(session)
        project_repo = SQLAlchemyProjectRepository(session)
        time_entry_repo = SQLAlchemyTimeEntryRepository(session)
        
        # Create use case
        use_case = GenerateInvoicePDFUseCase(
            invoice_repository=repository,
            client_repository=client_repo,
            project_repository=project_repo,
            time_entry_repository=time_entry_repo
        )
        
        # Create request
        request = GenerateInvoicePDFRequest(
            invoice_id=invoice_id,
            template_theme=template,
            include_time_entries=include_time_entries
        )
        
        # Generate PDF
        result = await use_case.execute(user_id, request)
        
        # Return the PDF file
        headers = {}
        if download:
            headers["Content-Disposition"] = f"attachment; filename={result.filename}"
        
        return FileResponse(
            path=result.file_path,
            media_type="application/pdf",
            filename=result.filename,
            headers=headers
        )
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with id {invoice_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF"
        )


@router.get("/reports/summary")
async def get_invoice_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyInvoiceRepository, Depends(get_invoice_repository)],
    start_date: Optional[datetime] = Query(None, description="Summary from date"),
    end_date: Optional[datetime] = Query(None, description="Summary to date"),
    client_id: Optional[int] = Query(None, description="Filter by client ID")
):
    """
    Get invoice summary and statistics.
    
    - **start_date**: Summary from this date
    - **end_date**: Summary to this date
    - **client_id**: Filter by specific client
    """
    try:
        use_case = ListInvoicesUseCase(repository)
        
        # TODO: Implement proper reporting logic
        # This would require additional use cases for generating reports
        return {
            "user_id": user_id,
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "client_id": client_id
            },
            "summary": {
                "total_invoices": 0,
                "total_amount": 0.0,
                "paid_amount": 0.0,
                "outstanding_amount": 0.0,
                "overdue_amount": 0.0,
                "average_payment_time": 0
            },
            "status_breakdown": {
                "draft": 0,
                "sent": 0,
                "paid": 0,
                "overdue": 0,
                "cancelled": 0
            },
            "message": "Invoice reporting not yet fully implemented"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
