"""
Rate limiting decorators and FastAPI dependencies.
"""

import functools
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, status, Depends

from .limiter import RateLimit, RateLimiter, get_rate_limiter, RATE_LIMITS


def rate_limit(
    limit_name: str = 'default',
    rate_limit: Optional[RateLimit] = None,
    key_func: Optional[Callable[[Request], str]] = None,
    error_message: str = "Rate limit exceeded"
):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        limit_name: Name of predefined rate limit from RATE_LIMITS
        rate_limit: Custom RateLimit instance
        key_func: Function to generate rate limit key from request
        error_message: Custom error message
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                # If no request found, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get rate limit configuration
            if rate_limit:
                limit_config = rate_limit
            else:
                limit_config = RATE_LIMITS.get(limit_name, RATE_LIMITS['default'])
            
            # Check rate limit
            limiter = get_rate_limiter()
            status_result = limiter.check_rate_limit(request, limit_config, key_func)
            
            if status_result.retry_after:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message,
                    headers=status_result.to_headers()
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            
            # If response has headers attribute, add rate limit headers
            if hasattr(response, 'headers'):
                response.headers.update(status_result.to_headers())
            
            return response
        
        return wrapper
    return decorator


def create_rate_limit_dependency(
    limit_name: str = 'default',
    rate_limit: Optional[RateLimit] = None,
    key_func: Optional[Callable[[Request], str]] = None,
    error_message: str = "Rate limit exceeded"
):
    """
    Create a FastAPI dependency for rate limiting.
    
    Usage:
        rate_limit_dep = create_rate_limit_dependency('auth')
        
        @app.post("/login")
        async def login(request: Request, _: None = Depends(rate_limit_dep)):
            ...
    """
    async def rate_limit_dependency(request: Request):
        # Get rate limit configuration
        if rate_limit:
            limit_config = rate_limit
        else:
            limit_config = RATE_LIMITS.get(limit_name, RATE_LIMITS['default'])
        
        # Check rate limit
        limiter = get_rate_limiter()
        status_result = limiter.check_rate_limit(request, limit_config, key_func)
        
        if status_result.retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message,
                headers=status_result.to_headers()
            )
        
        return status_result
    
    return rate_limit_dependency


# Predefined dependencies
auth_rate_limit = create_rate_limit_dependency(
    'auth', 
    error_message="Too many authentication attempts. Please try again later."
)

create_rate_limit = create_rate_limit_dependency(
    'create',
    error_message="Too many create operations. Please slow down."
)

upload_rate_limit = create_rate_limit_dependency(
    'upload',
    error_message="Too many uploads. Please wait before uploading again."
)

search_rate_limit = create_rate_limit_dependency(
    'search',
    error_message="Too many search requests. Please wait before searching again."
)

strict_rate_limit = create_rate_limit_dependency(
    'strict',
    error_message="Rate limit exceeded. Please try again later."
)


# Key generation functions
def user_key(request: Request) -> str:
    """Generate rate limit key based on authenticated user."""
    # Get user ID from JWT token or session
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"rate_limit:user:{user_id}:{request.url.path}"
    
    # Fallback to IP-based key
    client_ip = request.client.host if request.client else 'unknown'
    return f"rate_limit:ip:{client_ip}:{request.url.path}"


def ip_key(request: Request) -> str:
    """Generate rate limit key based on client IP."""
    client_ip = request.client.host if request.client else 'unknown'
    return f"rate_limit:ip:{client_ip}:{request.url.path}"


def user_agent_key(request: Request) -> str:
    """Generate rate limit key based on user agent."""
    user_agent = request.headers.get('user-agent', 'unknown')
    client_ip = request.client.host if request.client else 'unknown'
    # Use a hash of user agent to keep key size reasonable
    import hashlib
    agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
    return f"rate_limit:agent:{client_ip}:{agent_hash}:{request.url.path}"


def global_key(request: Request) -> str:
    """Generate global rate limit key (applies to all requests)."""
    return f"rate_limit:global:{request.url.path}"


# User-specific rate limit dependencies
user_auth_rate_limit = create_rate_limit_dependency(
    'auth',
    key_func=user_key,
    error_message="Too many authentication attempts for this account."
)

user_create_rate_limit = create_rate_limit_dependency(
    'create',
    key_func=user_key,
    error_message="Too many create operations for this account."
)

user_search_rate_limit = create_rate_limit_dependency(
    'search',
    key_func=user_key,
    error_message="Too many search requests for this account."
)