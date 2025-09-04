"""
Application layer use cases.
Business logic for the freelancer management system.
"""

from .base_use_case import *
from .client_use_cases import *
from .user_use_cases import *

__all__ = [
    # Base Use Cases
    "BaseUseCase",
    "QueryUseCase", 
    "CommandUseCase",
    "BulkUseCase",
    "PaginatedQueryUseCase",
    "CreateUseCase",
    "UpdateUseCase", 
    "DeleteUseCase",
    "GetByIdUseCase",
    "ListUseCase",
    "SearchUseCase",
    "AuthorizedUseCase",
    "UseCaseResult",
    "UseCaseContext",
    "handle_use_case_errors",
    
    # Client Use Cases
    "CreateClientUseCase",
    "UpdateClientUseCase",
    "UpdateClientBillingUseCase", 
    "GetClientByIdUseCase",
    "ListClientsUseCase",
    "SearchClientsUseCase",
    "DeleteClientUseCase",
    "ArchiveClientUseCase",
    "BulkUpdateClientsUseCase",
    "GetClientActivityUseCase",
    "GetClientAnalyticsUseCase",
    
    # User Use Cases
    "CreateUserUseCase",
    "UpdateUserUseCase",
    "UpdateUserPreferencesUseCase",
    "UpdateBillingInfoUseCase",
    "ChangePasswordUseCase",
    "GetUserByIdUseCase",
    "ListUsersUseCase",
    "LoginUseCase",
    "RegisterUseCase",
    "RefreshTokenUseCase",
    "GetUserStatsUseCase",
]