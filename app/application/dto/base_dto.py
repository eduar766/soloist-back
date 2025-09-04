"""
Base DTOs for the application layer.
Provides common patterns for request/response data transfer objects.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime, date
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict, validator
from enum import Enum


class BaseDTO(BaseModel):
    """Base DTO with common configuration."""
    
    model_config = ConfigDict(
        # Allow population by field name or alias
        populate_by_name=True,
        # Convert enum values to their values
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True,
        # Allow extra fields for flexibility
        extra="forbid",
        # JSON encoders for custom types
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
    )


class RequestDTO(BaseDTO):
    """Base class for request DTOs."""
    pass


class ResponseDTO(BaseDTO):
    """Base class for response DTOs."""
    
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateRequestDTO(RequestDTO):
    """Base class for creation request DTOs."""
    pass


class UpdateRequestDTO(RequestDTO):
    """Base class for update request DTOs."""
    pass


class ListRequestDTO(RequestDTO):
    """Base class for list request DTOs with pagination."""
    
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(default=None, max_length=255, description="Search query")
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


T = TypeVar('T')

class ListResponseDTO(ResponseDTO, Generic[T]):
    """Base class for paginated list responses."""
    
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "ListResponseDTO[T]":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class FilterRequestDTO(ListRequestDTO):
    """Base class for filtered list requests."""
    
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters to apply")
    date_from: Optional[date] = Field(default=None, description="Filter from date")
    date_to: Optional[date] = Field(default=None, description="Filter to date")
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Validate that date_to is after date_from."""
        if v and values.get('date_from') and v < values['date_from']:
            raise ValueError('date_to must be after date_from')
        return v


class SearchRequestDTO(ListRequestDTO):
    """DTO for search requests."""
    
    query: str = Field(min_length=1, max_length=255, description="Search query")
    search_fields: Optional[List[str]] = Field(default=None, description="Fields to search in")
    exact_match: bool = Field(default=False, description="Whether to use exact matching")


class BulkRequestDTO(RequestDTO):
    """Base class for bulk operation requests."""
    
    ids: List[int] = Field(min_items=1, max_items=100, description="List of IDs to process")


class BulkResponseDTO(ResponseDTO):
    """Base class for bulk operation responses."""
    
    success_count: int = Field(description="Number of successful operations")
    error_count: int = Field(description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors")
    
    @classmethod
    def create(cls, success_count: int, errors: List[Dict[str, Any]]) -> "BulkResponseDTO":
        """Create a bulk response."""
        return cls(
            success_count=success_count,
            error_count=len(errors),
            errors=errors
        )


class HealthCheckResponseDTO(BaseDTO):
    """Health check response DTO."""
    
    status: str = Field(description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: Optional[str] = Field(default=None, description="Application version")
    dependencies: Optional[Dict[str, str]] = Field(default=None, description="Dependency statuses")


class ErrorResponseDTO(BaseDTO):
    """Error response DTO."""
    
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracing")


class ValidationErrorResponseDTO(ErrorResponseDTO):
    """Validation error response DTO."""
    
    field_errors: List[Dict[str, str]] = Field(description="Field-specific validation errors")


class StatsResponseDTO(ResponseDTO):
    """Base class for statistics responses."""
    
    period_start: Optional[date] = Field(default=None, description="Statistics period start")
    period_end: Optional[date] = Field(default=None, description="Statistics period end")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When stats were generated")


# Common field patterns
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OwnerMixin(BaseModel):
    """Mixin for ownership fields."""
    
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None


class TagsMixin(BaseModel):
    """Mixin for tags fields."""
    
    tags: List[str] = Field(default_factory=list, max_items=20, description="Tags")


class NotesMixin(BaseModel):
    """Mixin for notes field."""
    
    notes: Optional[str] = Field(default=None, max_length=2000, description="Notes")


# Enums for common status values
class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class ExportFormat(str, Enum):
    """Export format options."""
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"


# Utility functions
def to_dict(obj: Any, exclude_none: bool = True) -> Dict[str, Any]:
    """Convert object to dictionary, optionally excluding None values."""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump(exclude_none=exclude_none)
    elif hasattr(obj, 'dict'):
        return obj.dict(exclude_none=exclude_none)
    else:
        return obj.__dict__


def from_domain_entity(entity: Any, dto_class: type) -> Any:
    """Convert domain entity to DTO."""
    if hasattr(entity, 'to_dict'):
        data = entity.to_dict()
    else:
        data = entity.__dict__
    
    return dto_class(**data)


def to_domain_dict(dto: BaseDTO, exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convert DTO to dictionary suitable for domain entity creation."""
    exclude_fields = exclude_fields or ['id', 'created_at', 'updated_at']
    data = dto.model_dump(exclude_none=True)
    
    for field in exclude_fields:
        data.pop(field, None)
    
    return data