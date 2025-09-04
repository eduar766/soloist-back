"""
Email template loader and renderer.
Handles Jinja2 templates for professional email notifications.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from datetime import datetime
import locale

logger = logging.getLogger(__name__)


class EmailTemplateLoader:
    """Loads and renders email templates using Jinja2."""
    
    def __init__(self):
        """Initialize template loader with email templates directory."""
        self.templates_dir = Path(__file__).parent / "templates"
        
        # Ensure templates directory exists
        self.templates_dir.mkdir(exist_ok=True)
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        
        # Register custom filters
        self._register_filters()
    
    def _register_filters(self):
        """Register custom Jinja2 filters for email templates."""
        
        @self.env.filter("currency")
        def format_currency(value, currency="USD", locale_code="es_CL"):
            """Format currency value."""
            try:
                if currency == "USD":
                    return f"${value:,.2f} USD"
                elif currency == "CLP":
                    return f"${value:,.0f} CLP"
                else:
                    return f"{value:,.2f} {currency}"
            except:
                return str(value)
        
        @self.env.filter("date")
        def format_date(value, format="%d/%m/%Y"):
            """Format date value."""
            try:
                if isinstance(value, str):
                    # Parse ISO date string
                    date_obj = datetime.fromisoformat(value.replace("Z", "+00:00"))
                elif isinstance(value, datetime):
                    date_obj = value
                else:
                    return str(value)
                
                return date_obj.strftime(format)
            except:
                return str(value)
        
        @self.env.filter("time")
        def format_time(value, format="%H:%M"):
            """Format time value."""
            try:
                if isinstance(value, str):
                    time_obj = datetime.fromisoformat(value.replace("Z", "+00:00"))
                elif isinstance(value, datetime):
                    time_obj = value
                else:
                    return str(value)
                
                return time_obj.strftime(format)
            except:
                return str(value)
        
        @self.env.filter("duration")
        def format_duration(minutes):
            """Format duration in minutes to hours and minutes."""
            try:
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                if hours > 0:
                    return f"{hours}h {mins}m"
                else:
                    return f"{mins}m"
            except:
                return str(minutes)
        
        @self.env.filter("capitalize_words")
        def capitalize_words(value):
            """Capitalize each word."""
            return str(value).title()
    
    async def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context.
        
        Args:
            template_name: Name of template file (e.g., 'invoice_sent.html')
            context: Template context variables
            
        Returns:
            Rendered template content
        """
        try:
            # Add default context variables
            enhanced_context = {
                **context,
                "current_year": datetime.now().year,
                "current_date": datetime.now().strftime("%d/%m/%Y"),
                "app_name": "Sistema de Gestión Freelancer"
            }
            
            # Load and render template
            template = self.env.get_template(template_name)
            rendered = template.render(**enhanced_context)
            
            logger.debug(f"Successfully rendered template: {template_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            # Return fallback template
            return self._get_fallback_template(template_name, context)
    
    def _get_fallback_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Get fallback template when main template fails."""
        
        subject = context.get("subject", "Notificación")
        recipient = context.get("recipient_name", "Usuario")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Hola {recipient},</h2>
                <p>Ha ocurrido un error al cargar la plantilla de email ({template_name}).</p>
                <p>Por favor contacta con soporte si necesitas asistencia.</p>
                <br>
                <p>Saludos cordiales,<br>
                Sistema de Gestión Freelancer</p>
            </div>
        </body>
        </html>
        """
    
    def template_exists(self, template_name: str) -> bool:
        """Check if template file exists."""
        template_path = self.templates_dir / template_name
        return template_path.exists()
    
    def list_templates(self) -> list[str]:
        """List all available email templates."""
        templates = []
        for file_path in self.templates_dir.glob("*.html"):
            templates.append(file_path.name)
        return templates
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a specific template."""
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            return {"exists": False}
        
        stat = template_path.stat()
        
        return {
            "exists": True,
            "name": template_name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(template_path)
        }