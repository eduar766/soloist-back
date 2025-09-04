"""
Authentication dependencies for FastAPI.
Provides authentication and authorization decorators and dependencies.
"""

from typing import Optional, Annotated, Any, Dict
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.infrastructure.auth.jwt_handler import JWTHandler
from app.infrastructure.auth.supabase_auth import SupabaseAuthService
from app.domain.models.base import ValidationError


# Security scheme
security = HTTPBearer()

# Global instances
jwt_handler = JWTHandler()
auth_service = SupabaseAuthService()


def get_jwt_handler() -> JWTHandler:
    """Dependency to get JWT handler."""
    return jwt_handler


def get_auth_service() -> SupabaseAuthService:
    """Dependency to get authentication service."""
    return auth_service


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)]
) -> str:
    """
    FastAPI dependency to get current authenticated user ID.
    
    Args:
        credentials: Bearer token credentials
        jwt_handler: JWT handler instance
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        user_id = jwt_handler.get_user_id(token)
        return user_id
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)]
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user's full token payload.
    
    Args:
        credentials: Bearer token credentials
        jwt_handler: JWT handler instance
        
    Returns:
        Token payload dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        payload = jwt_handler.verify_token(token)
        return payload
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user_id(
    request: Request,
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)]
) -> Optional[str]:
    """
    FastAPI dependency to optionally get authenticated user ID.
    Returns None if no token or invalid token.
    
    Args:
        request: FastAPI request object
        jwt_handler: JWT handler instance
        
    Returns:
        User ID string if authenticated, None otherwise
    """
    try:
        authorization = request.headers.get("authorization")
        if not authorization:
            return None
        
        if not authorization.startswith("Bearer "):
            return None
        
        token = authorization[7:]  # Remove "Bearer " prefix
        user_id = jwt_handler.get_user_id(token)
        return user_id
    except (ValidationError, Exception):
        return None


def require_auth(func):
    """
    Decorator to require authentication for a function.
    Automatically injects user_id as the first parameter.
    
    Usage:
        @require_auth
        async def my_endpoint(user_id: str, ...):
            # user_id is automatically injected
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user_id from dependency injection
        user_id = kwargs.get('user_id') or (args[0] if args else None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return await func(*args, **kwargs)
    return wrapper


class ProjectRoleChecker:
    """Dependency class to check project-level permissions."""
    
    def __init__(self, required_roles: list[str] = None, allow_owner: bool = True):
        """
        Initialize role checker.
        
        Args:
            required_roles: List of required roles (member, admin, etc.)
            allow_owner: Whether project owner automatically has access
        """
        self.required_roles = required_roles or ["member"]
        self.allow_owner = allow_owner
    
    async def __call__(
        self,
        project_id: int,
        user_id: Annotated[str, Depends(get_current_user_id)]
    ) -> str:
        """
        Check if user has required role for project.
        
        Args:
            project_id: Project ID from path parameter
            user_id: Current user ID
            
        Returns:
            User ID if authorized
            
        Raises:
            HTTPException: If not authorized
        """
        # TODO: Implement actual project role checking
        # For now, allow all authenticated users
        # This will be implemented when we have project member tables
        
        # Placeholder implementation:
        # In a real implementation, we would:
        # 1. Query project_members table to get user's role in project
        # 2. Check if user is project owner
        # 3. Verify role matches required_roles
        
        return user_id


def require_project_role(roles: list[str] = None, allow_owner: bool = True):
    """
    Dependency factory for project-level role checking.
    
    Args:
        roles: Required roles for access
        allow_owner: Whether project owner automatically has access
        
    Returns:
        Dependency function
    """
    return ProjectRoleChecker(roles, allow_owner)


# Pre-configured dependencies for common use cases
require_project_member = require_project_role(["member", "admin"])
require_project_admin = require_project_role(["admin"])
require_project_owner = require_project_role([], allow_owner=True)


class ResourceOwnerChecker:
    """Dependency class to check resource ownership."""
    
    def __init__(self, resource_type: str):
        """
        Initialize ownership checker.
        
        Args:
            resource_type: Type of resource (client, project, invoice, etc.)
        """
        self.resource_type = resource_type
    
    async def __call__(
        self,
        resource_id: int,
        user_id: Annotated[str, Depends(get_current_user_id)]
    ) -> str:
        """
        Check if user owns the resource.
        
        Args:
            resource_id: Resource ID from path parameter
            user_id: Current user ID
            
        Returns:
            User ID if authorized
            
        Raises:
            HTTPException: If not authorized
        """
        # TODO: Implement actual ownership checking
        # For now, allow all authenticated users
        # This will be implemented when we have repositories
        
        return user_id


def require_resource_owner(resource_type: str):
    """
    Dependency factory for resource ownership checking.
    
    Args:
        resource_type: Type of resource to check ownership
        
    Returns:
        Dependency function
    """
    return ResourceOwnerChecker(resource_type)


# Pre-configured dependencies for common resources
require_client_owner = require_resource_owner("client")
require_project_owner_only = require_resource_owner("project")
require_invoice_owner = require_resource_owner("invoice")
require_task_access = require_resource_owner("task")  # Tasks use project-level access