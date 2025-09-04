"""
Application layer DTOs.
Data Transfer Objects for API requests and responses.
"""

from .base_dto import *
from .client_dto import *
from .user_dto import *

__all__ = [
    # Base DTOs
    "BaseDTO",
    "RequestDTO", 
    "ResponseDTO",
    "CreateRequestDTO",
    "UpdateRequestDTO",
    "ListRequestDTO",
    "FilterRequestDTO",
    "SearchRequestDTO",
    "BulkRequestDTO",
    "BulkResponseDTO",
    "ListResponseDTO",
    "HealthCheckResponseDTO",
    "ErrorResponseDTO",
    "ValidationErrorResponseDTO",
    "StatsResponseDTO",
    "TimestampMixin",
    "OwnerMixin",
    "TagsMixin",
    "NotesMixin",
    "SortOrder",
    "ExportFormat",
    
    # Client DTOs
    "ContactInfoRequestDTO",
    "ContactInfoResponseDTO",
    "CreateClientRequestDTO",
    "UpdateClientRequestDTO", 
    "UpdateClientBillingRequestDTO",
    "ListClientsRequestDTO",
    "SearchClientsRequestDTO",
    "ClientStatsResponseDTO",
    "ClientResponseDTO",
    "ClientSummaryResponseDTO",
    "ClientActivityResponseDTO",
    "ClientRevenueResponseDTO",
    "BulkUpdateClientsRequestDTO",
    "ArchiveClientRequestDTO",
    "ClientAnalyticsResponseDTO",
    "ClientHealthScoreResponseDTO",
    
    # User DTOs
    "CreateUserRequestDTO",
    "UpdateUserRequestDTO",
    "UpdateUserPreferencesRequestDTO",
    "UpdateBillingInfoRequestDTO",
    "ChangePasswordRequestDTO",
    "ListUsersRequestDTO",
    "UserPreferencesResponseDTO",
    "UserStatsResponseDTO",
    "UserResponseDTO",
    "UserProfileResponseDTO",
    "AuthUserResponseDTO",
    "LoginRequestDTO",
    "RegisterRequestDTO",
    "RefreshTokenRequestDTO",
    "ForgotPasswordRequestDTO",
    "ResetPasswordRequestDTO",
    "VerifyEmailRequestDTO",
    "UserActivityResponseDTO",
    "UserProductivityResponseDTO",
    "UserTimeTrackingStatsDTO",
]