"""
Base use case classes for the application layer.
Provides common patterns and structure for use case implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic, List
from dataclasses import dataclass
from datetime import datetime

from app.domain.models.base import DomainException, ValidationError, BusinessRuleViolation


T = TypeVar('T')
R = TypeVar('R')


@dataclass
class UseCaseResult(Generic[T]):
    """Result wrapper for use case operations."""
    
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, data: T, metadata: Optional[Dict[str, Any]] = None) -> "UseCaseResult[T]":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error_result(
        cls, 
        error: str, 
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "UseCaseResult[T]":
        """Create an error result."""
        return cls(
            success=False, 
            error=error, 
            error_code=error_code,
            metadata=metadata
        )
    
    @classmethod
    def from_exception(cls, exc: Exception) -> "UseCaseResult[T]":
        """Create error result from exception."""
        if isinstance(exc, ValidationError):
            return cls.error_result(exc.message, "VALIDATION_ERROR")
        elif isinstance(exc, BusinessRuleViolation):
            return cls.error_result(exc.message, "BUSINESS_RULE_VIOLATION")
        elif isinstance(exc, DomainException):
            return cls.error_result(exc.message, exc.code)
        else:
            return cls.error_result(str(exc), "UNKNOWN_ERROR")


class BaseUseCase(ABC, Generic[T, R]):
    """
    Base class for all use cases.
    Provides common structure and error handling.
    """
    
    def __init__(self):
        self.execution_start: Optional[datetime] = None
        self.execution_end: Optional[datetime] = None
    
    async def execute(self, request: T) -> UseCaseResult[R]:
        """
        Execute the use case with proper error handling and logging.
        """
        self.execution_start = datetime.utcnow()
        
        try:
            # Validate input
            await self._validate_request(request)
            
            # Execute business logic
            result = await self._execute_business_logic(request)
            
            self.execution_end = datetime.utcnow()
            execution_time = (self.execution_end - self.execution_start).total_seconds()
            
            return UseCaseResult.success_result(
                result,
                metadata={
                    "execution_time_seconds": execution_time,
                    "executed_at": self.execution_end.isoformat()
                }
            )
        
        except Exception as exc:
            self.execution_end = datetime.utcnow()
            execution_time = (self.execution_end - self.execution_start).total_seconds()
            
            error_result = UseCaseResult.from_exception(exc)
            error_result.metadata = {
                "execution_time_seconds": execution_time,
                "failed_at": self.execution_end.isoformat(),
                "exception_type": type(exc).__name__
            }
            
            return error_result
    
    async def _validate_request(self, request: T) -> None:
        """
        Validate the request. Override in subclasses if needed.
        """
        if hasattr(request, 'model_validate'):
            # Pydantic models
            request.model_validate(request.model_dump())
        elif hasattr(request, 'validate'):
            # Custom validation
            request.validate()
    
    @abstractmethod
    async def _execute_business_logic(self, request: T) -> R:
        """
        Execute the core business logic. Must be implemented by subclasses.
        """
        pass


class QueryUseCase(BaseUseCase[T, R]):
    """
    Base class for query use cases (read operations).
    """
    
    async def _validate_request(self, request: T) -> None:
        """Validate query request."""
        await super()._validate_request(request)
        # Add query-specific validations if needed


class CommandUseCase(BaseUseCase[T, R]):
    """
    Base class for command use cases (write operations).
    Includes transaction handling and event publishing.
    """
    
    def __init__(self):
        super().__init__()
        self.events: List[Any] = []
    
    async def _validate_request(self, request: T) -> None:
        """Validate command request."""
        await super()._validate_request(request)
        # Add command-specific validations if needed
    
    async def _execute_business_logic(self, request: T) -> R:
        """
        Execute command with transaction handling.
        """
        # Start transaction (implementation depends on your DB layer)
        try:
            result = await self._execute_command_logic(request)
            
            # Publish domain events
            await self._publish_events()
            
            # Commit transaction
            return result
            
        except Exception:
            # Rollback transaction
            raise
    
    @abstractmethod
    async def _execute_command_logic(self, request: T) -> R:
        """Execute the command logic. Must be implemented by subclasses."""
        pass
    
    async def _publish_events(self) -> None:
        """Publish collected domain events."""
        # Implementation depends on your event bus
        for event in self.events:
            # await event_publisher.publish(event)
            pass
        
        self.events.clear()


class BulkUseCase(BaseUseCase[T, R]):
    """
    Base class for bulk operations.
    """
    
    def __init__(self, max_batch_size: int = 100):
        super().__init__()
        self.max_batch_size = max_batch_size
    
    async def _validate_request(self, request: T) -> None:
        """Validate bulk request."""
        await super()._validate_request(request)
        
        # Check batch size
        if hasattr(request, 'items') and len(request.items) > self.max_batch_size:
            raise ValidationError(f"Batch size cannot exceed {self.max_batch_size}")


class PaginatedQueryUseCase(QueryUseCase[T, R]):
    """
    Base class for paginated query use cases.
    """
    
    def __init__(self, default_page_size: int = 20, max_page_size: int = 100):
        super().__init__()
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size
    
    async def _validate_request(self, request: T) -> None:
        """Validate paginated request."""
        await super()._validate_request(request)
        
        if hasattr(request, 'page_size'):
            if request.page_size > self.max_page_size:
                raise ValidationError(f"Page size cannot exceed {self.max_page_size}")
            if request.page_size < 1:
                raise ValidationError("Page size must be positive")


# Specific use case patterns
class CreateUseCase(CommandUseCase[T, R]):
    """Base class for entity creation use cases."""
    pass


class UpdateUseCase(CommandUseCase[T, R]):
    """Base class for entity update use cases."""
    pass


class DeleteUseCase(CommandUseCase[T, R]):
    """Base class for entity deletion use cases."""
    pass


class GetByIdUseCase(QueryUseCase[T, R]):
    """Base class for get-by-id use cases."""
    
    async def _validate_request(self, request: T) -> None:
        """Validate get-by-id request."""
        await super()._validate_request(request)
        
        if hasattr(request, 'id') and request.id <= 0:
            raise ValidationError("ID must be positive")


class ListUseCase(PaginatedQueryUseCase[T, R]):
    """Base class for list use cases."""
    pass


class SearchUseCase(PaginatedQueryUseCase[T, R]):
    """Base class for search use cases."""
    
    async def _validate_request(self, request: T) -> None:
        """Validate search request."""
        await super()._validate_request(request)
        
        if hasattr(request, 'query'):
            if not request.query or not request.query.strip():
                raise ValidationError("Search query cannot be empty")
            if len(request.query) < 2:
                raise ValidationError("Search query must be at least 2 characters")


# Authorization mixin
class AuthorizedUseCase(BaseUseCase[T, R]):
    """
    Mixin for use cases that require authorization.
    """
    
    def __init__(self):
        super().__init__()
        self.current_user_id: Optional[str] = None
        self.current_user_roles: List[str] = []
    
    def set_current_user(self, user_id: str, roles: List[str]):
        """Set the current user context."""
        self.current_user_id = user_id
        self.current_user_roles = roles
    
    async def _validate_request(self, request: T) -> None:
        """Validate request with authorization check."""
        await super()._validate_request(request)
        
        if not self.current_user_id:
            raise ValidationError("User authentication required")
        
        await self._check_authorization(request)
    
    async def _check_authorization(self, request: T) -> None:
        """Check if the current user is authorized. Override in subclasses."""
        pass
    
    def _require_role(self, required_role: str) -> None:
        """Check if user has required role."""
        if required_role not in self.current_user_roles:
            raise BusinessRuleViolation(f"Role '{required_role}' required")
    
    def _require_owner_or_role(self, resource_owner_id: str, required_role: str) -> None:
        """Check if user is owner or has required role."""
        if self.current_user_id != resource_owner_id and required_role not in self.current_user_roles:
            raise BusinessRuleViolation("Insufficient permissions")


# Utility functions
def handle_use_case_errors(func):
    """Decorator for additional error handling."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log error, send notifications, etc.
            raise
    return wrapper


class UseCaseContext:
    """Context object for use case execution."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.user_roles = user_roles or []
        self.request_id = request_id
        self.metadata = metadata or {}
        self.execution_start = datetime.utcnow()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context."""
        self.metadata[key] = value
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.user_roles