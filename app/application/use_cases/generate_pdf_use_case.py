"""
Use case for generating PDF documents (invoices, quotes, reports).
Handles PDF generation with template customization and storage.
"""

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from app.domain.models.base import EntityNotFoundError, ValidationError
from app.domain.repositories.invoice_repository import InvoiceRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.time_entry_repository import TimeEntryRepository
from app.infrastructure.pdf.pdf_service import pdf_service
from app.infrastructure.pdf.template_manager import template_manager, TemplateTheme
from app.application.dto.base import BaseRequest, BaseResponse


class GenerateInvoicePDFRequest(BaseRequest):
    """Request for generating invoice PDF."""
    invoice_id: int
    template_theme: Optional[str] = "professional"
    include_time_entries: bool = True
    custom_company_data: Optional[Dict[str, Any]] = None
    output_filename: Optional[str] = None


class GenerateInvoicePDFResponse(BaseResponse):
    """Response with PDF generation result."""
    file_path: str
    filename: str
    file_size: int
    generated_at: datetime
    template_used: str


class GenerateInvoicePDFUseCase:
    """Use case for generating invoice PDFs."""
    
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        client_repository: ClientRepository,
        project_repository: ProjectRepository,
        time_entry_repository: Optional[TimeEntryRepository] = None
    ):
        self.invoice_repository = invoice_repository
        self.client_repository = client_repository
        self.project_repository = project_repository
        self.time_entry_repository = time_entry_repository
    
    async def execute(self, user_id: str, request: GenerateInvoicePDFRequest) -> GenerateInvoicePDFResponse:
        """Execute PDF generation for an invoice."""
        
        # Get invoice and validate ownership
        invoice = await self.invoice_repository.find_by_id(request.invoice_id)
        if not invoice:
            raise EntityNotFoundError(f"Invoice with id {request.invoice_id} not found")
        
        if invoice.owner_id != user_id:
            raise ValidationError("Access denied to this invoice")
        
        # Get related entities
        client = await self.client_repository.find_by_id(invoice.client_id)
        if not client:
            raise EntityNotFoundError("Client not found for this invoice")
        
        project = None
        if invoice.project_id:
            project = await self.project_repository.find_by_id(invoice.project_id)
        
        # Get time entries if requested
        time_entries = []
        if request.include_time_entries and self.time_entry_repository:
            time_entries = await self.time_entry_repository.find_by_invoice_id(invoice.id)
        
        # Get user's template settings and company profile
        template_settings = template_manager.get_template_settings(user_id)
        company_profile = template_manager.get_company_profile(user_id)
        
        # Override template theme if specified in request
        if request.template_theme:
            try:
                theme = TemplateTheme(request.template_theme)
                template_settings.theme = theme
            except ValueError:
                raise ValidationError(f"Invalid template theme: {request.template_theme}")
        
        # Prepare company data
        company_data = request.custom_company_data or company_profile.__dict__
        
        # Get template file
        template_file = template_manager.get_template_file(template_settings.theme)
        
        # Generate custom output path if specified
        output_path = None
        if request.output_filename:
            output_path = self._generate_custom_output_path(request.output_filename)
        
        try:
            # Generate PDF
            pdf_path = pdf_service.generate_invoice_pdf(
                invoice=invoice,
                client=client,
                project=project,
                time_entries=time_entries,
                company_data=company_data,
                template_name=template_file,
                output_path=output_path
            )
            
            # Get file information
            file_path = Path(pdf_path)
            file_size = file_path.stat().st_size
            
            return GenerateInvoicePDFResponse(
                file_path=pdf_path,
                filename=file_path.name,
                file_size=file_size,
                generated_at=datetime.now(),
                template_used=template_settings.theme.value
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to generate PDF: {str(e)}")
    
    def _generate_custom_output_path(self, filename: str) -> str:
        """Generate custom output path with proper extension."""
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        # Create temp directory
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "soloist_pdfs"
        temp_dir.mkdir(exist_ok=True)
        
        return str(temp_dir / filename)


class GenerateReportPDFRequest(BaseRequest):
    """Request for generating report PDF."""
    report_type: str  # "time_summary", "financial", "project_summary"
    project_id: Optional[int] = None
    client_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    template_theme: str = "professional"
    include_charts: bool = True
    group_by: Optional[str] = None  # "day", "week", "month", "project", "task"


class GenerateReportPDFResponse(BaseResponse):
    """Response with report PDF generation result."""
    file_path: str
    filename: str
    file_size: int
    generated_at: datetime
    report_type: str
    records_included: int


class GenerateReportPDFUseCase:
    """Use case for generating report PDFs."""
    
    def __init__(
        self,
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository,
        client_repository: ClientRepository
    ):
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
        self.client_repository = client_repository
    
    async def execute(self, user_id: str, request: GenerateReportPDFRequest) -> GenerateReportPDFResponse:
        """Execute report PDF generation."""
        
        # Validate report type
        valid_types = ["time_summary", "financial", "project_summary"]
        if request.report_type not in valid_types:
            raise ValidationError(f"Invalid report type. Must be one of: {valid_types}")
        
        # Prepare report data based on type
        if request.report_type == "time_summary":
            report_data = await self._prepare_time_summary_data(user_id, request)
        elif request.report_type == "financial":
            report_data = await self._prepare_financial_data(user_id, request)
        elif request.report_type == "project_summary":
            report_data = await self._prepare_project_summary_data(user_id, request)
        
        # Generate filename
        filename = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            # Generate PDF using report template
            template_name = f"report_{request.report_type}.html"
            
            pdf_path = pdf_service.generate_report_pdf(
                report_data=report_data,
                template_name=template_name
            )
            
            # Get file information
            file_path = Path(pdf_path)
            file_size = file_path.stat().st_size
            
            return GenerateReportPDFResponse(
                file_path=pdf_path,
                filename=file_path.name,
                file_size=file_size,
                generated_at=datetime.now(),
                report_type=request.report_type,
                records_included=report_data.get("total_records", 0)
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to generate report PDF: {str(e)}")
    
    async def _prepare_time_summary_data(self, user_id: str, request: GenerateReportPDFRequest) -> Dict[str, Any]:
        """Prepare data for time summary report."""
        # Get time entries based on filters
        time_entries = await self.time_entry_repository.find_by_user_and_date_range(
            user_id=user_id,
            start_date=request.start_date,
            end_date=request.end_date,
            project_id=request.project_id
        )
        
        # Calculate summaries
        total_hours = sum(entry.duration_minutes / 60 for entry in time_entries)
        billable_hours = sum(entry.duration_minutes / 60 for entry in time_entries if entry.is_billable)
        total_earnings = sum(
            (entry.duration_minutes / 60) * entry.hourly_rate 
            for entry in time_entries if entry.is_billable
        )
        
        # Group data if requested
        grouped_data = []
        if request.group_by:
            # Implementation would depend on grouping logic
            pass
        
        return {
            "report_title": "Resumen de Tiempo Trabajado",
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date or datetime.now()
            },
            "summary": {
                "total_hours": total_hours,
                "billable_hours": billable_hours,
                "total_earnings": total_earnings,
                "entries_count": len(time_entries)
            },
            "entries": [entry.to_dict() for entry in time_entries],
            "grouped_data": grouped_data,
            "generated_at": datetime.now(),
            "total_records": len(time_entries)
        }
    
    async def _prepare_financial_data(self, user_id: str, request: GenerateReportPDFRequest) -> Dict[str, Any]:
        """Prepare data for financial report."""
        # This would require invoice repository and payment data
        return {
            "report_title": "Reporte Financiero",
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date or datetime.now()
            },
            "summary": {
                "total_invoiced": 0,
                "total_paid": 0,
                "outstanding": 0
            },
            "generated_at": datetime.now(),
            "total_records": 0
        }
    
    async def _prepare_project_summary_data(self, user_id: str, request: GenerateReportPDFRequest) -> Dict[str, Any]:
        """Prepare data for project summary report."""
        if not request.project_id:
            raise ValidationError("project_id is required for project summary reports")
        
        project = await self.project_repository.find_by_id(request.project_id)
        if not project or project.owner_id != user_id:
            raise EntityNotFoundError("Project not found")
        
        return {
            "report_title": f"Resumen del Proyecto: {project.name}",
            "project": project.to_dict(),
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date or datetime.now()
            },
            "generated_at": datetime.now(),
            "total_records": 1
        }