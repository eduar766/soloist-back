"""
Custom Pydantic field types with enhanced validation.
"""

from typing import Any, Optional
from decimal import Decimal
from pydantic import Field, validator
from pydantic.fields import FieldInfo

from .validators import (
    SecurityValidator, DataValidator, BusinessValidator,
    safe_string_validator, secure_email_validator, secure_url_validator
)


def SafeStringField(
    default: Any = ...,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    **kwargs
) -> FieldInfo:
    """Create a safe string field with XSS and SQL injection protection."""
    field = Field(
        default=default,
        min_length=min_length,
        max_length=max_length,
        **kwargs
    )
    
    # Add custom validator
    field.validators = [safe_string_validator]
    return field


def SecureEmailField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a secure email field with enhanced validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [secure_email_validator]
    return field


def SecureUrlField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a secure URL field with protocol validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [secure_url_validator]
    return field


def CurrencyField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a currency code field with ISO 4217 validation."""
    field = Field(
        default=default,
        min_length=3,
        max_length=3,
        **kwargs
    )
    
    field.validators = [DataValidator.validate_currency_code]
    return field


def DecimalAmountField(
    default: Any = ...,
    min_value: float = 0,
    **kwargs
) -> FieldInfo:
    """Create a decimal amount field with precision validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    def validate_amount(value):
        return DataValidator.validate_decimal_amount(value, min_value)
    
    field.validators = [validate_amount]
    return field


def PhoneField(
    default: Any = ...,
    region: str = 'US',
    **kwargs
) -> FieldInfo:
    """Create a phone number field with international validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    def validate_phone(value):
        if value is None:
            return value
        return DataValidator.validate_phone(value, region)
    
    field.validators = [validate_phone]
    return field


def TaxIdField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a tax ID field with format validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [DataValidator.validate_tax_id]
    return field


def PostalCodeField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a postal code field with format validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [DataValidator.validate_postal_code]
    return field


def SafeFilenameField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a safe filename field with path traversal protection."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [SecurityValidator.sanitize_filename]
    return field


def ProjectNameField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a project name field with business validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [BusinessValidator.validate_project_name]
    return field


def ClientNameField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a client name field with business validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [BusinessValidator.validate_client_name]
    return field


def TaskTitleField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a task title field with business validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [BusinessValidator.validate_task_title]
    return field


def HourlyRateField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create an hourly rate field with business validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [BusinessValidator.validate_hourly_rate]
    return field


def PaymentTermsField(
    default: Any = ...,
    **kwargs
) -> FieldInfo:
    """Create a payment terms field with business validation."""
    field = Field(
        default=default,
        **kwargs
    )
    
    field.validators = [BusinessValidator.validate_payment_terms]
    return field


def SanitizedHtmlField(
    default: Any = ...,
    allowed_tags: Optional[list] = None,
    **kwargs
) -> FieldInfo:
    """Create a sanitized HTML field."""
    field = Field(
        default=default,
        **kwargs
    )
    
    def sanitize_html(value):
        if value is None:
            return value
        return SecurityValidator.sanitize_html(value, allowed_tags)
    
    field.validators = [sanitize_html]
    return field