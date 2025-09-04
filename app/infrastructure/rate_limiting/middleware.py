"""
Rate limiting middleware for FastAPI applications.
"""

import re
from typing import Dict, List, Pattern, Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .limiter import RateLimit, RateLimiter, get_rate_limiter, RATE_LIMITS


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for applying rate limits to endpoints."""
    
    def __init__(
        self,
        app,
        default_limit: str = 'default',
        path_limits: Optional[Dict[str, str]] = None,
        exclude_paths: Optional[List[str]] = None,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.path_limits = path_limits or {}
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
        self.key_func = key_func
        
        # Compile regex patterns for path matching
        self.path_patterns = {}
        for path_pattern, limit_name in self.path_limits.items():
            self.path_patterns[re.compile(path_pattern)] = limit_name
        
        # Compile exclude patterns
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting to requests."""
        
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Determine rate limit for this path
        limit_name = self._get_limit_for_path(request.url.path)
        rate_limit_config = RATE_LIMITS.get(limit_name, RATE_LIMITS['default'])
        
        # Check rate limit
        limiter = get_rate_limiter()
        status_result = limiter.check_rate_limit(request, rate_limit_config, self.key_func)
        
        if status_result.retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers=status_result.to_headers()
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for header_name, header_value in status_result.to_headers().items():
            response.headers[header_name] = header_value
        
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting."""
        return any(pattern.match(path) for pattern in self.exclude_patterns)
    
    def _get_limit_for_path(self, path: str) -> str:
        """Get rate limit name for the given path."""
        for pattern, limit_name in self.path_patterns.items():
            if pattern.match(path):
                return limit_name
        return self.default_limit


class AdaptiveRateLimitMiddleware(BaseHTTPMiddleware):
    """Adaptive rate limiting middleware that adjusts limits based on system load."""
    
    def __init__(
        self,
        app,
        base_limit: str = 'default',
        load_threshold: float = 0.8,
        adaptive_factor: float = 0.5
    ):
        super().__init__(app)
        self.base_limit = base_limit
        self.load_threshold = load_threshold
        self.adaptive_factor = adaptive_factor
        self.request_times = []
        self.max_samples = 100
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply adaptive rate limiting."""
        import time
        
        start_time = time.time()
        
        # Calculate system load based on recent response times
        system_load = self._calculate_system_load()
        
        # Adjust rate limit based on system load
        rate_limit_config = self._get_adaptive_rate_limit(system_load)
        
        # Check rate limit
        limiter = get_rate_limiter()
        status_result = limiter.check_rate_limit(request, rate_limit_config)
        
        if status_result.retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded - system under high load",
                headers=status_result.to_headers()
            )
        
        # Process request
        response = await call_next(request)
        
        # Record response time
        response_time = time.time() - start_time
        self._record_response_time(response_time)
        
        # Add rate limit headers with adaptive info
        headers = status_result.to_headers()
        headers['X-RateLimit-Load'] = f"{system_load:.2f}"
        
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response
    
    def _calculate_system_load(self) -> float:
        """Calculate system load based on recent response times."""
        if not self.request_times:
            return 0.0
        
        # Calculate average response time
        avg_response_time = sum(self.request_times) / len(self.request_times)
        
        # Convert to load score (higher response time = higher load)
        # Normalize to 0-1 range (assuming 1 second is high load)
        load = min(avg_response_time, 1.0)
        
        return load
    
    def _record_response_time(self, response_time: float):
        """Record response time for load calculation."""
        self.request_times.append(response_time)
        
        # Keep only recent samples
        if len(self.request_times) > self.max_samples:
            self.request_times.pop(0)
    
    def _get_adaptive_rate_limit(self, system_load: float) -> RateLimit:
        """Get rate limit adjusted for system load."""
        base_config = RATE_LIMITS[self.base_limit]
        
        if system_load > self.load_threshold:
            # Reduce rate limit when system is under high load
            adjusted_requests = int(base_config.requests * self.adaptive_factor)
            return RateLimit(
                requests=max(1, adjusted_requests),
                window=base_config.window,
                strategy=base_config.strategy
            )
        
        return base_config


class DifferentialRateLimitMiddleware(BaseHTTPMiddleware):
    """Differential rate limiting based on request characteristics."""
    
    def __init__(
        self,
        app,
        authenticated_limit: str = 'lenient',
        unauthenticated_limit: str = 'strict',
        premium_limit: str = 'api',
        method_limits: Optional[Dict[str, str]] = None
    ):
        super().__init__(app)
        self.authenticated_limit = authenticated_limit
        self.unauthenticated_limit = unauthenticated_limit
        self.premium_limit = premium_limit
        self.method_limits = method_limits or {
            'GET': 'lenient',
            'POST': 'default',
            'PUT': 'default',
            'DELETE': 'strict'
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply differential rate limiting."""
        
        # Determine appropriate rate limit
        limit_name = self._determine_rate_limit(request)
        rate_limit_config = RATE_LIMITS.get(limit_name, RATE_LIMITS['default'])
        
        # Generate key based on user authentication
        key_func = self._get_key_function(request)
        
        # Check rate limit
        limiter = get_rate_limiter()
        status_result = limiter.check_rate_limit(request, rate_limit_config, key_func)
        
        if status_result.retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers=status_result.to_headers()
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        headers = status_result.to_headers()
        headers['X-RateLimit-Policy'] = limit_name
        
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response
    
    def _determine_rate_limit(self, request: Request) -> str:
        """Determine appropriate rate limit based on request characteristics."""
        
        # Check if user is authenticated
        is_authenticated = self._is_authenticated(request)
        
        # Check if user has premium access
        is_premium = self._is_premium_user(request)
        
        # Check HTTP method
        method_limit = self.method_limits.get(request.method, 'default')
        
        if is_premium:
            return self.premium_limit
        elif is_authenticated:
            return self.authenticated_limit
        else:
            # Use the more restrictive of unauthenticated or method-specific limit
            unauthenticated_config = RATE_LIMITS[self.unauthenticated_limit]
            method_config = RATE_LIMITS[method_limit]
            
            if unauthenticated_config.requests <= method_config.requests:
                return self.unauthenticated_limit
            else:
                return method_limit
    
    def _is_authenticated(self, request: Request) -> bool:
        """Check if request is from authenticated user."""
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return True
        
        # Check for user_id in request state (set by auth middleware)
        return hasattr(request.state, 'user_id') and request.state.user_id is not None
    
    def _is_premium_user(self, request: Request) -> bool:
        """Check if user has premium access."""
        # Check for premium flag in request state
        return hasattr(request.state, 'is_premium') and request.state.is_premium
    
    def _get_key_function(self, request: Request) -> Callable[[Request], str]:
        """Get key function based on authentication status."""
        if self._is_authenticated(request):
            return lambda req: f"rate_limit:user:{getattr(req.state, 'user_id', 'unknown')}:{req.url.path}"
        else:
            return lambda req: f"rate_limit:ip:{req.client.host if req.client else 'unknown'}:{req.url.path}"