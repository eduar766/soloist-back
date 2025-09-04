"""
Advanced rate limiting implementation with Redis backend.
"""

import time
import json
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
    RedisType = redis.Redis
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    RedisType = Any  # Fallback type for when redis is not available

from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    burst: Optional[int] = None  # Allow bursts up to this limit
    
    def __post_init__(self):
        if self.burst is None:
            self.burst = self.requests


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(self.reset_time)
        }
        if self.retry_after:
            headers['Retry-After'] = str(self.retry_after)
        return headers


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development."""
    
    def __init__(self):
        self.requests = {}
        self.reset_times = {}
    
    def is_allowed(self, key: str, rate_limit: RateLimit) -> RateLimitStatus:
        """Check if request is allowed under rate limit."""
        current_time = int(time.time())
        window_start = current_time - (current_time % rate_limit.window)
        
        # Clean up old entries
        if key in self.reset_times and self.reset_times[key] <= current_time:
            self.requests.pop(key, None)
            self.reset_times.pop(key, None)
        
        # Initialize or get current count
        if key not in self.requests:
            self.requests[key] = 0
            self.reset_times[key] = window_start + rate_limit.window
        
        current_count = self.requests[key]
        
        if current_count >= rate_limit.requests:
            return RateLimitStatus(
                limit=rate_limit.requests,
                remaining=0,
                reset_time=self.reset_times[key],
                retry_after=self.reset_times[key] - current_time
            )
        
        # Increment counter
        self.requests[key] += 1
        
        return RateLimitStatus(
            limit=rate_limit.requests,
            remaining=rate_limit.requests - (current_count + 1),
            reset_time=self.reset_times[key]
        )


class RedisRateLimiter:
    """Redis-based rate limiter with sliding window."""
    
    def __init__(self, redis_client: RedisType):
        self.redis = redis_client
    
    def is_allowed(self, key: str, rate_limit: RateLimit) -> RateLimitStatus:
        """Check if request is allowed under rate limit."""
        if rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._sliding_window(key, rate_limit)
        elif rate_limit.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._token_bucket(key, rate_limit)
        else:
            return self._fixed_window(key, rate_limit)
    
    def _fixed_window(self, key: str, rate_limit: RateLimit) -> RateLimitStatus:
        """Fixed window rate limiting."""
        current_time = int(time.time())
        window = current_time - (current_time % rate_limit.window)
        
        pipe = self.redis.pipeline()
        window_key = f"{key}:{window}"
        
        pipe.incr(window_key)
        pipe.expire(window_key, rate_limit.window)
        results = pipe.execute()
        
        current_count = results[0]
        reset_time = window + rate_limit.window
        
        if current_count > rate_limit.requests:
            return RateLimitStatus(
                limit=rate_limit.requests,
                remaining=0,
                reset_time=reset_time,
                retry_after=reset_time - current_time
            )
        
        return RateLimitStatus(
            limit=rate_limit.requests,
            remaining=max(0, rate_limit.requests - current_count),
            reset_time=reset_time
        )
    
    def _sliding_window(self, key: str, rate_limit: RateLimit) -> RateLimitStatus:
        """Sliding window rate limiting using sorted sets."""
        current_time = time.time()
        window_start = current_time - rate_limit.window
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, rate_limit.window)
        
        results = pipe.execute()
        current_count = results[1]
        
        reset_time = int(current_time + rate_limit.window)
        
        if current_count >= rate_limit.requests:
            # Remove the request we just added since it's not allowed
            self.redis.zrem(key, str(current_time))
            
            return RateLimitStatus(
                limit=rate_limit.requests,
                remaining=0,
                reset_time=reset_time,
                retry_after=rate_limit.window
            )
        
        return RateLimitStatus(
            limit=rate_limit.requests,
            remaining=rate_limit.requests - current_count - 1,
            reset_time=reset_time
        )
    
    def _token_bucket(self, key: str, rate_limit: RateLimit) -> RateLimitStatus:
        """Token bucket rate limiting."""
        current_time = time.time()
        bucket_key = f"{key}:bucket"
        
        # Get current bucket state
        bucket_data = self.redis.get(bucket_key)
        
        if bucket_data:
            bucket = json.loads(bucket_data)
            last_refill = bucket['last_refill']
            tokens = bucket['tokens']
        else:
            last_refill = current_time
            tokens = rate_limit.burst
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        tokens_to_add = int(time_elapsed * (rate_limit.requests / rate_limit.window))
        tokens = min(rate_limit.burst, tokens + tokens_to_add)
        
        reset_time = int(current_time + rate_limit.window)
        
        if tokens < 1:
            # Not enough tokens
            return RateLimitStatus(
                limit=rate_limit.requests,
                remaining=0,
                reset_time=reset_time,
                retry_after=int((1 - tokens) * (rate_limit.window / rate_limit.requests))
            )
        
        # Consume a token
        tokens -= 1
        
        # Save bucket state
        bucket_data = {
            'tokens': tokens,
            'last_refill': current_time
        }
        self.redis.setex(bucket_key, rate_limit.window * 2, json.dumps(bucket_data))
        
        return RateLimitStatus(
            limit=rate_limit.requests,
            remaining=int(tokens),
            reset_time=reset_time
        )


class RateLimiter:
    """Main rate limiter class that handles both Redis and in-memory backends."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.limiter = InMemoryRateLimiter()
        
        if redis_url and REDIS_AVAILABLE and redis:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.limiter = RedisRateLimiter(self.redis_client)
                logger.info("Using Redis rate limiter")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, using in-memory limiter: {e}")
        else:
            logger.info("Using in-memory rate limiter")
    
    def check_rate_limit(self, request: Request, rate_limit: RateLimit, 
                        key_func: Optional[callable] = None) -> RateLimitStatus:
        """Check if request is within rate limit."""
        if key_func:
            key = key_func(request)
        else:
            key = self._default_key(request)
        
        return self.limiter.is_allowed(key, rate_limit)
    
    def _default_key(self, request: Request) -> str:
        """Generate default key from request."""
        client_ip = request.client.host if request.client else 'unknown'
        path = request.url.path
        return f"rate_limit:{client_ip}:{path}"


# Predefined rate limits
RATE_LIMITS = {
    'default': RateLimit(requests=100, window=60),  # 100 requests per minute
    'strict': RateLimit(requests=30, window=60),    # 30 requests per minute
    'lenient': RateLimit(requests=300, window=60),  # 300 requests per minute
    'auth': RateLimit(requests=5, window=60),       # 5 login attempts per minute
    'create': RateLimit(requests=20, window=60),    # 20 creates per minute
    'upload': RateLimit(requests=10, window=60),    # 10 uploads per minute
    'search': RateLimit(requests=50, window=60),    # 50 searches per minute
    'api': RateLimit(requests=1000, window=3600),   # 1000 requests per hour
}


# Global rate limiter instance
rate_limiter = None


def init_rate_limiter(redis_url: Optional[str] = None):
    """Initialize global rate limiter."""
    global rate_limiter
    rate_limiter = RateLimiter(redis_url)
    return rate_limiter


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    return rate_limiter