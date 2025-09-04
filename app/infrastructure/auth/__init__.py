"""
Authentication infrastructure module.
Handles JWT validation, user authentication, and authorization.
"""

from .jwt_handler import JWTHandler
from .supabase_auth import SupabaseAuthService
from .dependencies import (
    get_current_user_id,
    get_current_user_payload,
    get_optional_user_id,
    require_auth,
    require_project_role,
    require_resource_owner,
    require_project_member,
    require_project_admin,
    require_project_owner,
    require_client_owner,
    require_project_owner_only,
    require_invoice_owner,
    require_task_access
)

__all__ = [
    "JWTHandler",
    "SupabaseAuthService",
    "get_current_user_id",
    "get_current_user_payload", 
    "get_optional_user_id",
    "require_auth",
    "require_project_role",
    "require_resource_owner",
    "require_project_member",
    "require_project_admin", 
    "require_project_owner",
    "require_client_owner",
    "require_project_owner_only",
    "require_invoice_owner",
    "require_task_access"
]