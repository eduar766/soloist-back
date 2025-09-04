"""
Template management system for PDF generation.
Handles template customization, theme switching, and dynamic configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TemplateTheme(Enum):
    """Available template themes."""
    PROFESSIONAL = "professional"
    MINIMAL = "minimal"
    MODERN = "modern"
    CREATIVE = "creative"


@dataclass
class CompanyProfile:
    """Company profile configuration for PDF templates."""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    tax_id_label: str = "Tax ID"
    logo_url: Optional[str] = None
    footer_text: Optional[str] = None
    primary_color: str = "#2c3e50"
    secondary_color: str = "#34495e"
    accent_color: str = "#3498db"


@dataclass
class TemplateSettings:
    """Template customization settings."""
    theme: TemplateTheme = TemplateTheme.PROFESSIONAL
    font_family: str = "Helvetica"
    font_size: int = 11
    show_logo: bool = True
    show_company_details: bool = True
    show_tax_info: bool = True
    include_payment_terms: bool = True
    include_notes_section: bool = True
    currency_position: str = "before"  # "before" or "after"
    date_format: str = "%d/%m/%Y"
    number_format: str = "INV-{:04d}"
    custom_css: Optional[str] = None


class TemplateManager:
    """Manages PDF templates and customization."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager."""
        self.templates_dir = templates_dir or (Path(__file__).parent / "templates")
        self.config_dir = Path(__file__).parent / "config"
        self.config_dir.mkdir(exist_ok=True)
        
        # Template mappings
        self.template_files = {
            TemplateTheme.PROFESSIONAL: "invoice_base.html",
            TemplateTheme.MINIMAL: "invoice_minimal.html",
            TemplateTheme.MODERN: "invoice_modern.html",
            TemplateTheme.CREATIVE: "invoice_creative.html"
        }
        
    def get_company_profile(self, user_id: str) -> CompanyProfile:
        """Get company profile for a user."""
        config_file = self.config_dir / f"company_{user_id}.json"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return CompanyProfile(**data)
        
        # Return default profile
        return CompanyProfile(name="Mi Empresa")
    
    def save_company_profile(self, user_id: str, profile: CompanyProfile) -> None:
        """Save company profile for a user."""
        config_file = self.config_dir / f"company_{user_id}.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(profile), f, indent=2, ensure_ascii=False)
    
    def get_template_settings(self, user_id: str) -> TemplateSettings:
        """Get template settings for a user."""
        config_file = self.config_dir / f"template_{user_id}.json"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert theme string back to enum
                if 'theme' in data:
                    data['theme'] = TemplateTheme(data['theme'])
                return TemplateSettings(**data)
        
        # Return default settings
        return TemplateSettings()
    
    def save_template_settings(self, user_id: str, settings: TemplateSettings) -> None:
        """Save template settings for a user."""
        config_file = self.config_dir / f"template_{user_id}.json"
        
        data = asdict(settings)
        # Convert enum to string for JSON serialization
        data['theme'] = settings.theme.value
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_template_file(self, theme: TemplateTheme) -> str:
        """Get template filename for a theme."""
        return self.template_files.get(theme, self.template_files[TemplateTheme.PROFESSIONAL])
    
    def list_available_themes(self) -> List[Dict[str, Any]]:
        """List all available template themes."""
        return [
            {
                "value": theme.value,
                "name": theme.value.title(),
                "description": self._get_theme_description(theme),
                "preview_url": f"/api/templates/preview/{theme.value}"
            }
            for theme in TemplateTheme
        ]
    
    def _get_theme_description(self, theme: TemplateTheme) -> str:
        """Get description for a theme."""
        descriptions = {
            TemplateTheme.PROFESSIONAL: "Diseño clásico y profesional con información completa",
            TemplateTheme.MINIMAL: "Diseño limpio y minimalista con elementos esenciales",
            TemplateTheme.MODERN: "Diseño moderno con elementos visuales actuales",
            TemplateTheme.CREATIVE: "Diseño creativo con elementos distintivos"
        }
        return descriptions.get(theme, "Plantilla personalizada")
    
    def generate_custom_css(self, settings: TemplateSettings, profile: CompanyProfile) -> str:
        """Generate custom CSS based on settings and profile."""
        css_vars = {
            "primary_color": profile.primary_color,
            "secondary_color": profile.secondary_color,
            "accent_color": profile.accent_color,
            "font_family": settings.font_family,
            "font_size": f"{settings.font_size}pt"
        }
        
        custom_css = f"""
        :root {{
            --primary-color: {css_vars['primary_color']};
            --secondary-color: {css_vars['secondary_color']};
            --accent-color: {css_vars['accent_color']};
            --font-family: '{css_vars['font_family']}';
            --font-size: {css_vars['font_size']};
        }}
        
        body {{
            font-family: var(--font-family);
            font-size: var(--font-size);
        }}
        
        .company-name, .invoice-title h1 {{
            color: var(--primary-color);
        }}
        
        .section-title {{
            color: var(--primary-color);
            border-bottom-color: var(--accent-color);
        }}
        
        .items-table th {{
            background-color: {self._lighten_color(profile.primary_color, 0.9)};
            color: var(--primary-color);
        }}
        
        .totals-table .total-row {{
            border-color: var(--primary-color);
            color: var(--primary-color);
        }}
        """
        
        # Hide elements based on settings
        if not settings.show_logo:
            custom_css += "\n.company-logo { display: none; }"
            
        if not settings.show_company_details:
            custom_css += "\n.company-details { display: none; }"
            
        if not settings.show_tax_info:
            custom_css += "\n.tax-info { display: none; }"
        
        # Add custom CSS if provided
        if settings.custom_css:
            custom_css += f"\n\n/* Custom CSS */\n{settings.custom_css}"
        
        return custom_css
    
    def _lighten_color(self, hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Lighten
        lightened = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        
        # Convert back to hex
        return f"#{lightened[0]:02x}{lightened[1]:02x}{lightened[2]:02x}"
    
    def export_template_config(self, user_id: str) -> Dict[str, Any]:
        """Export complete template configuration for a user."""
        company_profile = self.get_company_profile(user_id)
        template_settings = self.get_template_settings(user_id)
        
        return {
            "company_profile": asdict(company_profile),
            "template_settings": {
                **asdict(template_settings),
                "theme": template_settings.theme.value
            },
            "exported_at": "2024-01-01T00:00:00Z"  # Would be datetime.now().isoformat()
        }
    
    def import_template_config(self, user_id: str, config: Dict[str, Any]) -> None:
        """Import template configuration for a user."""
        if "company_profile" in config:
            profile = CompanyProfile(**config["company_profile"])
            self.save_company_profile(user_id, profile)
        
        if "template_settings" in config:
            settings_data = config["template_settings"].copy()
            if "theme" in settings_data:
                settings_data["theme"] = TemplateTheme(settings_data["theme"])
            settings = TemplateSettings(**settings_data)
            self.save_template_settings(user_id, settings)
    
    def create_template_preview_data(self, theme: TemplateTheme) -> Dict[str, Any]:
        """Create sample data for template preview."""
        from datetime import datetime, timedelta
        
        return {
            "invoice": {
                "invoice_number": "INV-0001",
                "issue_date": datetime.now(),
                "due_date": datetime.now() + timedelta(days=30),
                "status": "sent",
                "status_display": "Enviada",
                "currency": "USD",
                "currency_symbol": "$",
                "subtotal": 1500.00,
                "tax_rate": 19.0,
                "tax_amount": 285.00,
                "total_amount": 1785.00,
                "notes": "Gracias por su confianza en nuestros servicios.",
                "payment_terms": "Pago a 30 días. Transferencia bancaria preferida.",
                "line_items": [
                    {
                        "description": "Desarrollo de aplicación web",
                        "details": "Frontend y backend completo",
                        "quantity": 40.0,
                        "unit_price": 35.00,
                        "total_amount": 1400.00
                    },
                    {
                        "description": "Consultoría técnica",
                        "details": "Asesoría en arquitectura",
                        "quantity": 4.0,
                        "unit_price": 25.00,
                        "total_amount": 100.00
                    }
                ]
            },
            "client": {
                "name": "Empresa Cliente S.A.",
                "contact": "contacto@cliente.com",
                "address": "Av. Principal 123",
                "city": "Santiago",
                "country": "Chile",
                "tax_id": "12.345.678-9"
            },
            "company": {
                "name": "Mi Empresa SpA",
                "address": "Av. Providencia 456",
                "city": "Santiago",
                "country": "Chile",
                "phone": "+56 2 1234 5678",
                "email": "contacto@miempresa.com",
                "website": "www.miempresa.com",
                "tax_id": "98.765.432-1",
                "tax_id_label": "RUT",
                "primary_color": "#2c3e50"
            },
            "project": {
                "name": "Proyecto Web Cliente"
            },
            "now": datetime.now()
        }


# Singleton instance
template_manager = TemplateManager()