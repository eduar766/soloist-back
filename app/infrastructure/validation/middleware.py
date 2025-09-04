"""
Request validation middleware for comprehensive input validation.
"""

import json
import logging
from typing import Any, Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .validators import SecurityValidator

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to perform additional security validation on requests."""
    
    def __init__(self, app, enable_logging: bool = True):
        super().__init__(app)
        self.enable_logging = enable_logging
        
        # Paths that should be excluded from validation
        self.excluded_paths = {
            '/health', '/metrics', '/docs', '/redoc', '/openapi.json'
        }
        
        # Maximum allowed request size (in bytes)
        self.max_request_size = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through validation middleware."""
        
        # Skip validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        try:
            # Validate request size
            self._validate_request_size(request)
            
            # Validate headers
            await self._validate_headers(request)
            
            # Validate body if present
            if request.method in ['POST', 'PUT', 'PATCH']:
                await self._validate_request_body(request)
            
            # Validate query parameters
            self._validate_query_params(request)
            
        except ValueError as e:
            logger.warning(f"Validation failed for {request.url.path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Validation error for {request.url.path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request validation failed"
            )
        
        response = await call_next(request)
        return response
    
    def _validate_request_size(self, request: Request) -> None:
        """Validate request size to prevent DoS attacks."""
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_request_size:
            raise ValueError(f"Request size exceeds maximum allowed size")
    
    async def _validate_headers(self, request: Request) -> None:
        """Validate request headers for security issues."""
        headers = request.headers
        
        # Check for suspicious user agents
        user_agent = headers.get('user-agent', '')
        if self._is_suspicious_user_agent(user_agent):
            raise ValueError("Suspicious user agent detected")
        
        # Validate content type for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = headers.get('content-type', '')
            if not self._is_valid_content_type(content_type):
                raise ValueError("Invalid content type")
        
        # Check for injection attempts in headers
        for header_name, header_value in headers.items():
            if isinstance(header_value, str):
                SecurityValidator.check_sql_injection(header_value)
                SecurityValidator.check_xss(header_value)
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate request body for security issues."""
        try:
            # Get the raw body
            body = await request.body()
            if not body:
                return
            
            # Try to parse as JSON if content-type indicates JSON
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    json_data = json.loads(body)
                    self._validate_json_data(json_data)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format")
            else:
                # For other content types, check raw body
                body_str = body.decode('utf-8', errors='ignore')
                SecurityValidator.check_sql_injection(body_str)
                SecurityValidator.check_xss(body_str)
                
        except UnicodeDecodeError:
            raise ValueError("Invalid request body encoding")
    
    def _validate_json_data(self, data: Any) -> None:
        """Recursively validate JSON data for security issues."""
        if isinstance(data, dict):
            for key, value in data.items():
                # Validate keys
                if isinstance(key, str):
                    SecurityValidator.check_sql_injection(key)
                    SecurityValidator.check_xss(key)
                
                # Recursively validate values
                self._validate_json_data(value)
                
        elif isinstance(data, list):
            for item in data:
                self._validate_json_data(item)
                
        elif isinstance(data, str):
            SecurityValidator.check_sql_injection(data)
            SecurityValidator.check_xss(data)
            SecurityValidator.check_path_traversal(data)
    
    def _validate_query_params(self, request: Request) -> None:
        """Validate query parameters for security issues."""
        for param_name, param_value in request.query_params.items():
            SecurityValidator.check_sql_injection(param_name)
            SecurityValidator.check_sql_injection(param_value)
            SecurityValidator.check_xss(param_name)
            SecurityValidator.check_xss(param_value)
            SecurityValidator.check_path_traversal(param_value)
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent looks suspicious."""
        suspicious_patterns = [
            'sqlmap', 'nmap', 'nikto', 'burp', 'zap', 'metasploit',
            'curl', 'wget', 'python-requests', 'bot', 'crawler', 'spider'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    def _is_valid_content_type(self, content_type: str) -> bool:
        """Check if content type is valid and allowed."""
        allowed_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
            'text/plain'
        ]
        
        return any(allowed_type in content_type for allowed_type in allowed_types)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Check request size and reject if too large."""
        content_length = request.headers.get('content-length')
        
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request size {content_length} exceeds maximum allowed size {self.max_size}"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header"
                )
        
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    def __init__(self, app):
        super().__init__(app)
        
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        return response


class IPRateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple IP-based rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
        self.last_reset = {}
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting based on client IP."""
        import time
        
        client_ip = request.client.host if request.client else 'unknown'
        current_time = time.time()
        current_minute = int(current_time // 60)
        
        # Reset counter if minute has changed
        if client_ip not in self.last_reset or self.last_reset[client_ip] != current_minute:
            self.request_counts[client_ip] = 0
            self.last_reset[client_ip] = current_minute
        
        # Increment request count
        self.request_counts[client_ip] += 1
        
        # Check if limit exceeded
        if self.request_counts[client_ip] > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        response = await call_next(request)
        return response