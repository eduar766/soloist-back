"""
Advanced rate limiting package for FastAPI applications.
"""

from .limiter import (
    RateLimit, RateLimitStrategy, RateLimitStatus,
    RateLimiter, get_rate_limiter, init_rate_limiter, RATE_LIMITS
)
from .decorators import (
    rate_limit, create_rate_limit_dependency,
    auth_rate_limit, create_rate_limit, upload_rate_limit, 
    search_rate_limit, strict_rate_limit,
    user_auth_rate_limit, user_create_rate_limit, user_search_rate_limit,
    user_key, ip_key, user_agent_key, global_key
)
from .middleware import (
    RateLimitMiddleware, AdaptiveRateLimitMiddleware, DifferentialRateLimitMiddleware
)

__all__ = [
    # Core classes
    'RateLimit',
    'RateLimitStrategy', 
    'RateLimitStatus',
    'RateLimiter',
    
    # Functions
    'get_rate_limiter',
    'init_rate_limiter',
    
    # Predefined limits
    'RATE_LIMITS',
    
    # Decorators
    'rate_limit',
    'create_rate_limit_dependency',
    
    # Dependencies
    'auth_rate_limit',
    'create_rate_limit',
    'upload_rate_limit',
    'search_rate_limit', 
    'strict_rate_limit',
    'user_auth_rate_limit',
    'user_create_rate_limit',
    'user_search_rate_limit',
    
    # Key functions
    'user_key',
    'ip_key',
    'user_agent_key',
    'global_key',
    
    # Middleware
    'RateLimitMiddleware',
    'AdaptiveRateLimitMiddleware',
    'DifferentialRateLimitMiddleware'
]