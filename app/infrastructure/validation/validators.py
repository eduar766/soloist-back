"""
Comprehensive input validation utilities.
Security-focused validators to prevent injection attacks and ensure data integrity.
"""

import re
import html
import urllib.parse
from typing import Any, List, Optional, Dict, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from pydantic import validator, ValidationError
import bleach
import phonenumbers
from phonenumbers import NumberParseException

# Security configurations
ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
ALLOWED_HTML_ATTRIBUTES = {}

# Regex patterns for common validation
PATTERNS = {
    'sql_injection': re.compile(
        r'(\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE)?|INSERT|SELECT|UNION|UPDATE)\b|'
        r'[;\'"\\]|--|\bOR\b|\bAND\b|<script|javascript:|vbscript:|onload|onerror)', 
        re.IGNORECASE
    ),
    'xss_basic': re.compile(r'<[^>]*script[^>]*>|javascript:|vbscript:|onload|onerror|eval\(', re.IGNORECASE),
    'path_traversal': re.compile(r'\.\./|\.\\./', re.IGNORECASE),
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    'url': re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE),
    'currency_code': re.compile(r'^[A-Z]{3}$'),
    'tax_id': re.compile(r'^[A-Z0-9\-]{5,20}$'),
    'postal_code': re.compile(r'^[A-Z0-9\-\s]{3,10}$', re.IGNORECASE),
    'alphanumeric_extended': re.compile(r'^[a-zA-Z0-9\s\-_.]+$'),
    'safe_filename': re.compile(r'^[a-zA-Z0-9\-_.()]+\.[a-zA-Z0-9]{2,10}$')
}


class SecurityValidator:
    """Security-focused validators to prevent injection attacks."""
    
    @staticmethod
    def check_sql_injection(value: str) -> str:
        """Check for potential SQL injection patterns."""
        if not isinstance(value, str):
            return value
            
        if PATTERNS['sql_injection'].search(value):
            raise ValueError("Potentially unsafe input detected")
        return value
    
    @staticmethod
    def check_xss(value: str) -> str:
        """Check for potential XSS patterns."""
        if not isinstance(value, str):
            return value
            
        if PATTERNS['xss_basic'].search(value):
            raise ValueError("Potentially unsafe script content detected")
        return value
    
    @staticmethod
    def check_path_traversal(value: str) -> str:
        """Check for path traversal attempts."""
        if not isinstance(value, str):
            return value
            
        if PATTERNS['path_traversal'].search(value):
            raise ValueError("Path traversal attempt detected")
        return value
    
    @staticmethod
    def sanitize_html(value: str, allowed_tags: List[str] = None) -> str:
        """Sanitize HTML content, removing dangerous tags and attributes."""
        if not isinstance(value, str):
            return value
            
        if allowed_tags is None:
            allowed_tags = ALLOWED_HTML_TAGS
            
        # Use bleach to sanitize HTML
        sanitized = bleach.clean(
            value,
            tags=allowed_tags,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
        
        return sanitized
    
    @staticmethod
    def sanitize_filename(value: str) -> str:
        """Sanitize filename to prevent path traversal and other attacks."""
        if not isinstance(value, str):
            return value
            
        # Remove path traversal patterns
        value = value.replace('../', '').replace('..\\', '')
        
        # Remove dangerous characters
        value = re.sub(r'[<>:"|?*]', '', value)
        
        # Ensure it matches safe filename pattern
        if not PATTERNS['safe_filename'].match(value):
            raise ValueError("Invalid filename format")
            
        return value


class DataValidator:
    """Validators for common data formats and business rules."""
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format with additional security checks."""
        if not isinstance(email, str):
            raise ValueError("Email must be a string")
            
        email = email.strip().lower()
        
        if not PATTERNS['email'].match(email):
            raise ValueError("Invalid email format")
            
        # Check for suspicious patterns
        if any(char in email for char in ['<', '>', '"', '\'']):
            raise ValueError("Email contains invalid characters")
            
        return email
    
    @staticmethod
    def validate_phone(phone: str, region: str = 'US') -> str:
        """Validate phone number using phonenumbers library."""
        if not isinstance(phone, str):
            raise ValueError("Phone must be a string")
            
        try:
            parsed = phonenumbers.parse(phone, region)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
                
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException:
            raise ValueError("Invalid phone number format")
    
    @staticmethod
    def validate_currency_code(code: str) -> str:
        """Validate ISO 4217 currency code."""
        if not isinstance(code, str):
            raise ValueError("Currency code must be a string")
            
        code = code.upper().strip()
        
        if not PATTERNS['currency_code'].match(code):
            raise ValueError("Invalid currency code format")
            
        # List of common valid currency codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD',
            'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW'
        }
        
        if code not in valid_currencies:
            raise ValueError(f"Unsupported currency code: {code}")
            
        return code
    
    @staticmethod
    def validate_decimal_amount(amount: Union[str, float, int, Decimal], min_value: float = 0) -> Decimal:
        """Validate and convert to decimal amount with precision checks."""
        try:
            if isinstance(amount, str):
                # Remove currency symbols and whitespace
                amount = re.sub(r'[$€£¥,\s]', '', amount)
            
            decimal_amount = Decimal(str(amount))
            
            # Check minimum value
            if decimal_amount < Decimal(str(min_value)):
                raise ValueError(f"Amount must be at least {min_value}")
            
            # Check precision (max 2 decimal places for currency)
            if decimal_amount.as_tuple().exponent < -2:
                raise ValueError("Amount cannot have more than 2 decimal places")
                
            # Check for reasonable maximum (prevent integer overflow)
            if decimal_amount > Decimal('999999999.99'):
                raise ValueError("Amount exceeds maximum allowed value")
                
            return decimal_amount
        except InvalidOperation:
            raise ValueError("Invalid amount format")
    
    @staticmethod
    def validate_tax_id(tax_id: str) -> str:
        """Validate tax ID format."""
        if not isinstance(tax_id, str):
            raise ValueError("Tax ID must be a string")
            
        tax_id = tax_id.upper().strip()
        
        if not PATTERNS['tax_id'].match(tax_id):
            raise ValueError("Invalid tax ID format")
            
        return tax_id
    
    @staticmethod
    def validate_postal_code(postal_code: str) -> str:
        """Validate postal code format."""
        if not isinstance(postal_code, str):
            raise ValueError("Postal code must be a string")
            
        postal_code = postal_code.upper().strip()
        
        if not PATTERNS['postal_code'].match(postal_code):
            raise ValueError("Invalid postal code format")
            
        return postal_code
    
    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL format with security checks."""
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
            
        url = url.strip()
        
        if not PATTERNS['url'].match(url):
            raise ValueError("Invalid URL format")
            
        # Additional security checks
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("URL must use HTTP or HTTPS protocol")
            
        return url
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date, max_range_days: int = 365) -> tuple:
        """Validate date range with business rules."""
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise ValueError("Dates must be date objects")
            
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")
            
        # Check range is not too large
        range_days = (end_date - start_date).days
        if range_days > max_range_days:
            raise ValueError(f"Date range cannot exceed {max_range_days} days")
            
        return start_date, end_date


class BusinessValidator:
    """Validators for business-specific rules."""
    
    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate project name with business rules."""
        if not isinstance(name, str):
            raise ValueError("Project name must be a string")
            
        name = name.strip()
        
        if len(name) < 1:
            raise ValueError("Project name is required")
        if len(name) > 255:
            raise ValueError("Project name is too long")
            
        # Security checks
        SecurityValidator.check_sql_injection(name)
        SecurityValidator.check_xss(name)
        
        return name
    
    @staticmethod
    def validate_client_name(name: str) -> str:
        """Validate client name with business rules."""
        if not isinstance(name, str):
            raise ValueError("Client name must be a string")
            
        name = name.strip()
        
        if len(name) < 1:
            raise ValueError("Client name is required")
        if len(name) > 255:
            raise ValueError("Client name is too long")
            
        # Security checks
        SecurityValidator.check_sql_injection(name)
        SecurityValidator.check_xss(name)
        
        return name
    
    @staticmethod
    def validate_task_title(title: str) -> str:
        """Validate task title with business rules."""
        if not isinstance(title, str):
            raise ValueError("Task title must be a string")
            
        title = title.strip()
        
        if len(title) < 1:
            raise ValueError("Task title is required")
        if len(title) > 500:
            raise ValueError("Task title is too long")
            
        # Security checks
        SecurityValidator.check_sql_injection(title)
        SecurityValidator.check_xss(title)
        
        return title
    
    @staticmethod
    def validate_hourly_rate(rate: Union[str, float, int, Decimal]) -> Decimal:
        """Validate hourly rate with business rules."""
        rate_decimal = DataValidator.validate_decimal_amount(rate, min_value=0)
        
        # Check maximum reasonable hourly rate
        if rate_decimal > Decimal('10000.00'):
            raise ValueError("Hourly rate exceeds reasonable maximum")
            
        return rate_decimal
    
    @staticmethod
    def validate_payment_terms(terms: str) -> str:
        """Validate payment terms."""
        if not isinstance(terms, str):
            raise ValueError("Payment terms must be a string")
            
        valid_terms = [
            'IMMEDIATE', 'NET_15', 'NET_30', 'NET_45', 'NET_60', 'NET_90', 'CUSTOM'
        ]
        
        if terms not in valid_terms:
            raise ValueError(f"Payment terms must be one of: {', '.join(valid_terms)}")
            
        return terms


def create_comprehensive_validator(*validators):
    """Create a comprehensive validator that applies multiple validation functions."""
    def validator_func(value: Any) -> Any:
        for validate in validators:
            value = validate(value)
        return value
    return validator_func


# Pre-configured common validators
safe_string_validator = create_comprehensive_validator(
    SecurityValidator.check_sql_injection,
    SecurityValidator.check_xss,
    SecurityValidator.check_path_traversal
)

safe_html_validator = create_comprehensive_validator(
    SecurityValidator.check_sql_injection,
    SecurityValidator.sanitize_html
)

secure_email_validator = create_comprehensive_validator(
    SecurityValidator.check_sql_injection,
    DataValidator.validate_email
)

secure_url_validator = create_comprehensive_validator(
    SecurityValidator.check_sql_injection,
    SecurityValidator.check_xss,
    DataValidator.validate_url
)