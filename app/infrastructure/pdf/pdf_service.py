"""
PDF generation service using WeasyPrint and Jinja2.
Handles invoice PDF creation with customizable templates.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import weasyprint
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from app.domain.models.invoice import Invoice
from app.domain.models.client import Client
from app.domain.models.project import Project
from app.domain.models.time_entry import TimeEntry
from app.config import settings


class PDFService:
    """Service for generating PDF documents from templates."""
    
    def __init__(self):
        """Initialize the PDF service with template environment."""
        self.templates_dir = Path(__file__).parent / "templates"
        self.assets_dir = Path(__file__).parent / "assets"
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self._register_filters()
        
        # Font configuration for better rendering
        self.font_config = FontConfiguration()
        
    def _register_filters(self):
        """Register custom Jinja2 filters."""
        
        def currency_format(value: float, currency: str = "USD") -> str:
            """Format currency with proper symbol and decimals."""
            symbols = {
                "USD": "$",
                "EUR": "€", 
                "GBP": "£",
                "CLP": "$",
                "MXN": "$",
                "ARS": "$"
            }
            symbol = symbols.get(currency, currency)
            return f"{symbol}{value:,.2f}"
        
        def duration_format(minutes: int) -> str:
            """Format duration from minutes to hours and minutes."""
            hours = minutes // 60
            mins = minutes % 60
            if hours > 0:
                return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
            return f"{mins}m"
        
        def percentage_format(value: float) -> str:
            """Format percentage value."""
            return f"{value:.1f}%"
        
        self.env.filters['currency'] = currency_format
        self.env.filters['duration'] = duration_format
        self.env.filters['percentage'] = percentage_format
    
    def generate_invoice_pdf(
        self,
        invoice: Invoice,
        client: Client,
        project: Optional[Project] = None,
        time_entries: Optional[list[TimeEntry]] = None,
        company_data: Optional[Dict[str, Any]] = None,
        template_name: str = "invoice_base.html",
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate PDF for an invoice.
        
        Args:
            invoice: Invoice domain model
            client: Client domain model
            project: Optional project domain model
            time_entries: Optional list of time entries
            company_data: Company information for the header
            template_name: Template file name to use
            output_path: Optional custom output path
            
        Returns:
            str: Path to the generated PDF file
        """
        # Prepare template context
        context = self._prepare_invoice_context(
            invoice=invoice,
            client=client,
            project=project,
            time_entries=time_entries,
            company_data=company_data or self._get_default_company_data()
        )
        
        # Load and render template
        template = self.env.get_template(template_name)
        html_content = template.render(**context)
        
        # Generate output path if not provided
        if not output_path:
            output_path = self._generate_output_path(
                f"invoice_{invoice.invoice_number}",
                ".pdf"
            )
        
        # Generate PDF
        html_doc = HTML(string=html_content, base_url=str(self.templates_dir))
        
        # Add custom CSS if exists
        css_path = self.templates_dir / f"{template_name.replace('.html', '.css')}"
        if css_path.exists():
            css = CSS(filename=str(css_path))
            html_doc.write_pdf(output_path, stylesheets=[css], font_config=self.font_config)
        else:
            html_doc.write_pdf(output_path, font_config=self.font_config)
        
        return output_path
    
    def _prepare_invoice_context(
        self,
        invoice: Invoice,
        client: Client,
        project: Optional[Project] = None,
        time_entries: Optional[list[TimeEntry]] = None,
        company_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Prepare template context for invoice rendering."""
        
        # Currency symbols mapping
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£", 
            "CLP": "$",
            "MXN": "$",
            "ARS": "$"
        }
        
        # Status display mapping
        status_display = {
            "draft": "Borrador",
            "sent": "Enviada",
            "paid": "Pagada", 
            "overdue": "Vencida",
            "cancelled": "Cancelada"
        }
        
        context = {
            "invoice": {
                **invoice.to_dict(),
                "currency_symbol": currency_symbols.get(invoice.currency, invoice.currency),
                "status_display": status_display.get(invoice.status, invoice.status.title()),
                "subtotal": invoice.calculate_subtotal(),
                "tax_amount": invoice.calculate_tax_amount(),
                "total_amount": invoice.calculate_total(),
            },
            "client": client.to_dict(),
            "company": company_data,
            "now": datetime.now()
        }
        
        if project:
            context["project"] = project.to_dict()
            
        if time_entries:
            context["time_entries"] = [
                {
                    **entry.to_dict(),
                    "duration_hours": entry.duration_minutes / 60,
                    "total_amount": (entry.duration_minutes / 60) * entry.hourly_rate
                }
                for entry in time_entries
            ]
        
        return context
    
    def _get_default_company_data(self) -> Dict[str, Any]:
        """Get default company data from settings."""
        return {
            "name": getattr(settings, "company_name", "Mi Empresa"),
            "address": getattr(settings, "company_address", ""),
            "city": getattr(settings, "company_city", ""),
            "state": getattr(settings, "company_state", ""),
            "postal_code": getattr(settings, "company_postal_code", ""),
            "country": getattr(settings, "company_country", ""),
            "phone": getattr(settings, "company_phone", ""),
            "email": getattr(settings, "company_email", ""),
            "website": getattr(settings, "company_website", ""),
            "tax_id": getattr(settings, "company_tax_id", ""),
            "tax_id_label": getattr(settings, "company_tax_id_label", "RUT"),
            "logo_url": getattr(settings, "company_logo_url", ""),
            "footer_text": getattr(settings, "company_footer_text", "")
        }
    
    def _generate_output_path(self, filename: str, extension: str) -> str:
        """Generate a temporary output path for the PDF."""
        # Create temp directory for PDFs if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "soloist_pdfs"
        temp_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{filename}_{timestamp}{extension}"
        
        return str(temp_dir / safe_filename)
    
    def generate_quote_pdf(
        self,
        quote_data: Dict[str, Any],
        template_name: str = "quote_base.html",
        output_path: Optional[str] = None
    ) -> str:
        """Generate PDF for a quote/estimate."""
        template = self.env.get_template(template_name)
        html_content = template.render(**quote_data)
        
        if not output_path:
            output_path = self._generate_output_path(
                f"quote_{quote_data.get('quote_number', 'draft')}",
                ".pdf"
            )
        
        HTML(string=html_content).write_pdf(output_path, font_config=self.font_config)
        return output_path
    
    def generate_report_pdf(
        self,
        report_data: Dict[str, Any],
        template_name: str = "report_base.html",
        output_path: Optional[str] = None
    ) -> str:
        """Generate PDF for reports (time tracking, financial, etc.)."""
        template = self.env.get_template(template_name)
        html_content = template.render(**report_data)
        
        if not output_path:
            output_path = self._generate_output_path(
                f"report_{datetime.now().strftime('%Y%m%d')}",
                ".pdf"
            )
        
        HTML(string=html_content).write_pdf(output_path, font_config=self.font_config)
        return output_path
    
    def list_available_templates(self) -> list[str]:
        """List all available PDF templates."""
        templates = []
        for file_path in self.templates_dir.glob("*.html"):
            templates.append(file_path.name)
        return sorted(templates)
    
    def validate_template(self, template_name: str) -> bool:
        """Validate if a template exists and is readable."""
        template_path = self.templates_dir / template_name
        return template_path.exists() and template_path.is_file()


# Singleton instance
pdf_service = PDFService()