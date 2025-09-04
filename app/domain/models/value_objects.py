"""
Value Objects for the domain layer.
Immutable objects that represent values and encapsulate business logic.
"""

from typing import Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CHF = "CHF"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    MXN = "MXN"
    BRL = "BRL"
    ARS = "ARS"
    CLP = "CLP"
    COP = "COP"
    PEN = "PEN"


@dataclass(frozen=True)
class Money:
    """Value object representing money with amount and currency."""
    
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        """Validate the money object after initialization."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        
        # Round to 2 decimal places for most currencies, 0 for JPY
        precision = 0 if self.currency == Currency.JPY else 2
        rounded_amount = self.amount.quantize(
            Decimal('0.01') if precision == 2 else Decimal('1'),
            rounding=ROUND_HALF_UP
        )
        object.__setattr__(self, 'amount', rounded_amount)
    
    @classmethod
    def zero(cls, currency: Currency) -> "Money":
        """Create a zero money object."""
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: Union[Currency, str]) -> "Money":
        """Create Money from float amount."""
        if isinstance(currency, str):
            currency = Currency(currency)
        return cls(Decimal(str(amount)), currency)
    
    @classmethod
    def from_string(cls, amount_str: str, currency: Union[Currency, str]) -> "Money":
        """Create Money from string amount."""
        if isinstance(currency, str):
            currency = Currency(currency)
        return cls(Decimal(amount_str), currency)
    
    def add(self, other: "Money") -> "Money":
        """Add two money objects (must have same currency)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: "Money") -> "Money":
        """Subtract two money objects (must have same currency)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Cannot subtract to negative amount")
        return Money(result_amount, self.currency)
    
    def multiply(self, factor: Union[int, float, Decimal]) -> "Money":
        """Multiply money by a factor."""
        if isinstance(factor, (int, float)):
            factor = Decimal(str(factor))
        return Money(self.amount * factor, self.currency)
    
    def divide(self, divisor: Union[int, float, Decimal]) -> "Money":
        """Divide money by a divisor."""
        if isinstance(divisor, (int, float)):
            divisor = Decimal(str(divisor))
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / divisor, self.currency)
    
    def is_zero(self) -> bool:
        """Check if the amount is zero."""
        return self.amount == 0
    
    def is_greater_than(self, other: "Money") -> bool:
        """Compare if this money is greater than other."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount
    
    def is_less_than(self, other: "Money") -> bool:
        """Compare if this money is less than other."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount
    
    def equals(self, other: "Money") -> bool:
        """Check if two money objects are equal."""
        return self.amount == other.amount and self.currency == other.currency
    
    def to_float(self) -> float:
        """Convert amount to float (use with caution for display only)."""
        return float(self.amount)
    
    def format(self, include_symbol: bool = True) -> str:
        """Format money for display."""
        symbols = {
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.CAD: "C$",
            Currency.AUD: "A$",
            Currency.JPY: "¥",
            Currency.CHF: "CHF ",
            Currency.SEK: "kr",
            Currency.NOK: "kr",
            Currency.DKK: "kr",
            Currency.MXN: "$",
            Currency.BRL: "R$",
            Currency.ARS: "$",
            Currency.CLP: "$",
            Currency.COP: "$",
            Currency.PEN: "S/",
        }
        
        if self.currency == Currency.JPY:
            amount_str = f"{self.amount:,.0f}"
        else:
            amount_str = f"{self.amount:,.2f}"
        
        if include_symbol:
            symbol = symbols.get(self.currency, f"{self.currency.value} ")
            return f"{symbol}{amount_str}"
        else:
            return f"{amount_str} {self.currency.value}"
    
    def __str__(self) -> str:
        return self.format()
    
    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency})"


@dataclass(frozen=True)
class TimeRange:
    """Value object representing a time range with start and end times."""
    
    start: datetime
    end: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate the time range after initialization."""
        if self.end is not None and self.start >= self.end:
            raise ValueError("Start time must be before end time")
    
    @classmethod
    def from_start(cls, start: datetime) -> "TimeRange":
        """Create an ongoing time range (no end time)."""
        return cls(start=start, end=None)
    
    @classmethod
    def from_duration(cls, start: datetime, duration_minutes: int) -> "TimeRange":
        """Create a time range from start time and duration in minutes."""
        if duration_minutes <= 0:
            raise ValueError("Duration must be positive")
        end = start + timedelta(minutes=duration_minutes)
        return cls(start=start, end=end)
    
    def is_ongoing(self) -> bool:
        """Check if the time range is still ongoing (no end time)."""
        return self.end is None
    
    def duration(self) -> Optional[timedelta]:
        """Get the duration of the time range."""
        if self.end is None:
            return None
        return self.end - self.start
    
    def duration_minutes(self) -> Optional[int]:
        """Get the duration in minutes."""
        if self.end is None:
            return None
        duration = self.duration()
        return int(duration.total_seconds() / 60)
    
    def duration_hours(self) -> Optional[float]:
        """Get the duration in hours (decimal)."""
        if self.end is None:
            return None
        duration = self.duration()
        return duration.total_seconds() / 3600
    
    def stop_at(self, end_time: datetime) -> "TimeRange":
        """Create a new time range with an end time."""
        if end_time <= self.start:
            raise ValueError("End time must be after start time")
        return TimeRange(start=self.start, end=end_time)
    
    def overlaps_with(self, other: "TimeRange") -> bool:
        """Check if this time range overlaps with another."""
        if self.is_ongoing() or other.is_ongoing():
            # If either range is ongoing, check if they overlap at the start
            return self.start <= (other.end or datetime.max) and \
                   other.start <= (self.end or datetime.max)
        
        return self.start < other.end and other.start < self.end
    
    def contains_time(self, time: datetime) -> bool:
        """Check if a specific time falls within this range."""
        if self.is_ongoing():
            return time >= self.start
        return self.start <= time <= self.end
    
    def format_duration(self) -> str:
        """Format the duration for display."""
        if self.is_ongoing():
            return "Ongoing"
        
        duration = self.duration()
        total_minutes = int(duration.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def __str__(self) -> str:
        end_str = self.end.strftime("%H:%M") if self.end else "ongoing"
        return f"{self.start.strftime('%Y-%m-%d %H:%M')} - {end_str}"


@dataclass(frozen=True)
class InvoiceNumber:
    """Value object representing an invoice number with format validation."""
    
    value: str
    
    def __post_init__(self):
        """Validate the invoice number format."""
        if not self.value:
            raise ValueError("Invoice number cannot be empty")
        
        if len(self.value) > 50:
            raise ValueError("Invoice number cannot exceed 50 characters")
        
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r'^[A-Za-z0-9\-_]+$', self.value):
            raise ValueError("Invoice number can only contain letters, numbers, hyphens, and underscores")
    
    @classmethod
    def generate_sequential(cls, prefix: str, sequence: int, year: Optional[int] = None) -> "InvoiceNumber":
        """Generate a sequential invoice number."""
        if year:
            value = f"{prefix}-{year}-{sequence:04d}"
        else:
            value = f"{prefix}-{sequence:04d}"
        return cls(value)
    
    @classmethod
    def generate_yearly(cls, prefix: str, year: int, sequence: int) -> "InvoiceNumber":
        """Generate a yearly invoice number (resets each year)."""
        return cls(f"{prefix}{year}{sequence:04d}")
    
    @classmethod
    def from_template(cls, template: str, **kwargs) -> "InvoiceNumber":
        """Generate invoice number from template."""
        try:
            value = template.format(**kwargs)
            return cls(value)
        except KeyError as e:
            raise ValueError(f"Missing template parameter: {e}")
    
    def get_prefix(self) -> Optional[str]:
        """Extract prefix from invoice number."""
        parts = self.value.split('-')
        return parts[0] if len(parts) > 1 else None
    
    def get_sequence(self) -> Optional[int]:
        """Extract sequence number from invoice number."""
        # Try to find the last numeric part
        parts = self.value.split('-')
        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"InvoiceNumber('{self.value}')"


@dataclass(frozen=True)
class Email:
    """Value object representing a validated email address."""
    
    address: str
    
    def __post_init__(self):
        """Validate the email address using basic regex."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.address):
            raise ValueError(f"Invalid email address: {self.address}")
    
    @classmethod
    def from_string(cls, email_str: str) -> "Email":
        """Create Email from string."""
        return cls(email_str.strip().lower())
    
    def local_part(self) -> str:
        """Get the local part (before @) of the email."""
        return self.address.split('@')[0]
    
    def domain_part(self) -> str:
        """Get the domain part (after @) of the email."""
        return self.address.split('@')[1]
    
    def is_same_domain(self, other: "Email") -> bool:
        """Check if two emails have the same domain."""
        return self.domain_part() == other.domain_part()
    
    def mask_for_display(self) -> str:
        """Mask email for privacy (show first 2 chars and domain)."""
        local = self.local_part()
        domain = self.domain_part()
        
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        else:
            return f"{local[:2]}***@{domain}"
    
    def __str__(self) -> str:
        return self.address
    
    def __repr__(self) -> str:
        return f"Email('{self.address}')"


@dataclass(frozen=True)
class PhoneNumber:
    """Value object representing a phone number."""
    
    number: str
    country_code: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize the phone number."""
        # Remove all non-digit characters except +
        normalized = re.sub(r'[^\d+]', '', self.number)
        
        if not normalized:
            raise ValueError("Phone number cannot be empty")
        
        if len(normalized) < 7:
            raise ValueError("Phone number too short")
        
        if len(normalized) > 15:
            raise ValueError("Phone number too long")
        
        # Basic validation for international format
        if normalized.startswith('+'):
            if len(normalized) < 8:
                raise ValueError("International phone number too short")
        
        object.__setattr__(self, 'number', normalized)
    
    @classmethod
    def from_string(cls, phone_str: str, country_code: Optional[str] = None) -> "PhoneNumber":
        """Create PhoneNumber from string."""
        return cls(phone_str.strip(), country_code)
    
    def is_international(self) -> bool:
        """Check if phone number is in international format."""
        return self.number.startswith('+')
    
    def format_for_display(self) -> str:
        """Format phone number for display."""
        if self.is_international():
            # Format international numbers
            if len(self.number) == 12:  # US format: +1XXXXXXXXXX
                return f"{self.number[:2]} ({self.number[2:5]}) {self.number[5:8]}-{self.number[8:]}"
            else:
                return self.number
        else:
            # Format domestic numbers
            if len(self.number) == 10:  # US format: XXXXXXXXXX
                return f"({self.number[:3]}) {self.number[3:6]}-{self.number[6:]}"
            else:
                return self.number
    
    def __str__(self) -> str:
        return self.format_for_display()
    
    def __repr__(self) -> str:
        return f"PhoneNumber('{self.number}', '{self.country_code}')"


@dataclass(frozen=True)
class Address:
    """Value object representing a physical address."""
    
    street: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    
    def __post_init__(self):
        """Validate the address components."""
        if not self.street.strip():
            raise ValueError("Street address is required")
        
        if not self.city.strip():
            raise ValueError("City is required")
        
        if len(self.country) != 2:
            raise ValueError("Country code must be 2 characters")
        
        # Clean up the fields
        object.__setattr__(self, 'street', self.street.strip())
        object.__setattr__(self, 'city', self.city.strip())
        object.__setattr__(self, 'country', self.country.upper())
        
        if self.state:
            object.__setattr__(self, 'state', self.state.strip())
        if self.postal_code:
            object.__setattr__(self, 'postal_code', self.postal_code.strip())
    
    def format_single_line(self) -> str:
        """Format address as single line."""
        parts = [self.street, self.city]
        
        if self.state:
            parts.append(self.state)
        
        if self.postal_code:
            parts.append(self.postal_code)
        
        parts.append(self.country)
        
        return ", ".join(parts)
    
    def format_multi_line(self) -> str:
        """Format address as multiple lines."""
        lines = [self.street, self.city]
        
        state_postal = []
        if self.state:
            state_postal.append(self.state)
        if self.postal_code:
            state_postal.append(self.postal_code)
        
        if state_postal:
            lines.append(" ".join(state_postal))
        
        lines.append(self.country)
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return self.format_single_line()
    
    def __repr__(self) -> str:
        return f"Address(street='{self.street}', city='{self.city}', state='{self.state}', postal_code='{self.postal_code}', country='{self.country}')"