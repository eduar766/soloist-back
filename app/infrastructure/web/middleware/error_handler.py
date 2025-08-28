"""
Global error handler middleware for the FastAPI application.
Catches and formats all exceptions consistently.
"""

import logging
import traceback
from typing import Any, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
import json

from app.config import settings

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle all uncaught exceptions and format error responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and handle any exceptions.
        """
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc)
    
    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Handle different types of exceptions and return appropriate responses.
        """
        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "request_path": request.url.path,
                "request_method": request.method,
                "client_host": request.client.host if request.client else None
            }
        )
        
        # Prepare error response
        error_response = self.format_error_response(exc)
        
        # Add request ID if available
        if hasattr(request.state, "request_id"):
            error_response["request_id"] = request.state.request_id
        
        # In development, add more debug information
        if settings.debug:
            error_response["debug"] = {
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc().split("\n")
            }
        
        return JSONResponse(
            status_code=error_response.get("status_code", 500),
            content=error_response
        )
    
    def format_error_response(self, exc: Exception) -> Dict[str, Any]:
        """
        Format exception into a consistent error response structure.
        """
        # Default error response
        error_response = {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
        
        # Handle specific exception types
        if isinstance(exc, ValueError):
            error_response.update({
                "error": "Bad Request",
                "message": str(exc),
                "status_code": status.HTTP_400_BAD_REQUEST
            })
        elif isinstance(exc, PermissionError):
            error_response.update({
                "error": "Forbidden",
                "message": "You don't have permission to perform this action",
                "status_code": status.HTTP_403_FORBIDDEN
            })
        elif isinstance(exc, FileNotFoundError):
            error_response.update({
                "error": "Not Found",
                "message": str(exc) or "Resource not found",
                "status_code": status.HTTP_404_NOT_FOUND
            })
        elif isinstance(exc, TimeoutError):
            error_response.update({
                "error": "Request Timeout",
                "message": "The request took too long to process",
                "status_code": status.HTTP_408_REQUEST_TIMEOUT
            })
        elif isinstance(exc, json.JSONDecodeError):
            error_response.update({
                "error": "Invalid JSON",
                "message": "The request body contains invalid JSON",
                "status_code": status.HTTP_400_BAD_REQUEST
            })
        
        # You can add more specific exception handlers here
        
        return error_response


class BusinessException(Exception):
    """
    Base exception for business logic errors.
    """
    def __init__(
        self,
        message: str,
        error_code: str = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(BusinessException):
    """Exception raised for validation errors."""
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            **kwargs
        )
        if field:
            self.details["field"] = field


class NotFoundException(BusinessException):
    """Exception raised when a resource is not found."""
    def __init__(self, resource: str, identifier: Any = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id {identifier} not found"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs
        )


class UnauthorizedException(BusinessException):
    """Exception raised for authentication errors."""
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class ForbiddenException(BusinessException):
    """Exception raised for authorization errors."""
    def __init__(self, message: str = "Access forbidden", **kwargs):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs
        )


class ConflictException(BusinessException):
    """Exception raised for conflict errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            **kwargs
        )