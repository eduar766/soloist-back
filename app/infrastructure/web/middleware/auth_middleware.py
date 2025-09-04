"""
Authentication middleware for FastAPI.
Handles JWT token validation and user context injection.
"""

from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

from app.infrastructure.auth.jwt_handler import JWTHandler
from app.domain.models.base import ValidationError


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication."""
    
    def __init__(self, app, jwt_handler: Optional[JWTHandler] = None):
        super().__init__(app)
        self.jwt_handler = jwt_handler or JWTHandler()
        
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-otp",
            "/api/v1/auth/generate-test-token",
            "/health",
            "/metrics"
        }
        
        # Endpoints that start with these prefixes are public
        self.public_prefixes = [
            "/shares/",  # Shared resources accessible via token
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware."""
        start_time = time.time()
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            response = await call_next(request)
            return response
        
        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            return self._create_auth_error("Missing authorization header")
        
        try:
            # Validate token and extract user info
            payload = self.jwt_handler.verify_token(token)
            user_id = payload.get('sub')
            
            if not user_id:
                return self._create_auth_error("Invalid token: missing user ID")
            
            # Inject user context into request state
            request.state.user_id = user_id
            request.state.user_email = payload.get('email')
            request.state.user_role = payload.get('role')
            request.state.token_payload = payload
            
            # Process the request
            response = await call_next(request)
            
            # Add timing headers for monitoring
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except ValidationError as e:
            return self._create_auth_error(str(e))
        except Exception as e:
            return self._create_auth_error(f"Authentication error: {str(e)}")
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authentication."""
        # Exact match for public endpoints
        if path in self.public_endpoints:
            return True
        
        # Check public prefixes
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header[7:]  # Remove "Bearer " prefix
    
    def _create_auth_error(self, detail: str) -> JSONResponse:
        """Create standardized authentication error response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": detail,
                "type": "authentication_error"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that optionally authenticates users but doesn't require it."""
    
    def __init__(self, app, jwt_handler: Optional[JWTHandler] = None):
        super().__init__(app)
        self.jwt_handler = jwt_handler or JWTHandler()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with optional authentication."""
        # Always try to extract and validate token
        token = self._extract_token(request)
        
        if token:
            try:
                payload = self.jwt_handler.verify_token(token)
                user_id = payload.get('sub')
                
                if user_id:
                    # Inject user context if token is valid
                    request.state.user_id = user_id
                    request.state.user_email = payload.get('email')
                    request.state.user_role = payload.get('role')
                    request.state.token_payload = payload
                    request.state.authenticated = True
                else:
                    request.state.authenticated = False
            except (ValidationError, Exception):
                # Invalid token, but don't fail - just mark as unauthenticated
                request.state.authenticated = False
        else:
            # No token provided
            request.state.authenticated = False
        
        # Always process the request
        response = await call_next(request)
        return response
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        return auth_header[7:]  # Remove "Bearer " prefix


def get_user_from_request(request: Request) -> Optional[dict]:
    """
    Helper function to extract user information from request state.
    Can be used in endpoints to get current user info.
    """
    if not hasattr(request.state, 'user_id'):
        return None
    
    return {
        'user_id': getattr(request.state, 'user_id', None),
        'email': getattr(request.state, 'user_email', None),
        'role': getattr(request.state, 'user_role', None),
        'authenticated': getattr(request.state, 'authenticated', False)
    }


def require_authenticated_user(request: Request) -> str:
    """
    Helper function to get authenticated user ID or raise HTTPException.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_id