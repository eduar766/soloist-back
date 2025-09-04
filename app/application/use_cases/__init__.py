"""
Application layer use cases.
Business logic for the freelancer management system.
"""

from .base_use_case import *
from .client_use_cases import *
from .user_use_cases import *
from .project_use_cases import *
from .task_use_cases import *
from .time_entry_use_cases import *
from .invoice_use_cases import *
from .share_use_cases import *

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
    
    # Project Use Cases
    "CreateProjectUseCase",
    "UpdateProjectUseCase",
    "UpdateProjectStatusUseCase",
    "AddProjectMemberUseCase",
    "UpdateProjectMemberUseCase",
    "GetProjectByIdUseCase",
    "ListProjectsUseCase",
    "SearchProjectsUseCase",
    "DeleteProjectUseCase",
    "ArchiveProjectUseCase",
    "BulkUpdateProjectsUseCase",
    "GetProjectStatsUseCase",
    "GetProjectAnalyticsUseCase",
    
    # Task Use Cases
    "CreateTaskUseCase",
    "UpdateTaskUseCase",
    "UpdateTaskStatusUseCase",
    "AssignTaskUseCase",
    "MoveTaskUseCase",
    "GetTaskByIdUseCase",
    "ListTasksUseCase",
    "SearchTasksUseCase",
    "DeleteTaskUseCase",
    "BulkUpdateTasksUseCase",
    "BulkMoveTasksUseCase",
    "AddTaskCommentUseCase",
    "AddTaskAttachmentUseCase",
    "GetTaskAnalyticsUseCase",
    
    # Time Entry Use Cases
    "StartTimerUseCase",
    "StopTimerUseCase",
    "CreateTimeEntryUseCase",
    "UpdateTimeEntryUseCase",
    "SubmitTimeEntryUseCase",
    "ApproveTimeEntryUseCase",
    "RejectTimeEntryUseCase",
    "GetTimeEntryByIdUseCase",
    "ListTimeEntriesUseCase",
    "SearchTimeEntriesUseCase",
    "DeleteTimeEntryUseCase",
    "BulkUpdateTimeEntriesUseCase",
    "BulkDeleteTimeEntriesUseCase",
    "GetRunningTimerUseCase",
    "GetTimeTrackingAnalyticsUseCase",
    
    # Invoice Use Cases
    "CreateInvoiceUseCase",
    "CreateInvoiceFromTimeUseCase",
    "UpdateInvoiceUseCase",
    "SendInvoiceUseCase",
    "RecordPaymentUseCase",
    "GetInvoiceByIdUseCase",
    "ListInvoicesUseCase",
    "SearchInvoicesUseCase",
    "DeleteInvoiceUseCase",
    "BulkUpdateInvoicesUseCase",
    "BulkSendInvoicesUseCase",
    "GetInvoiceStatsUseCase",
    "GetInvoiceAnalyticsUseCase",
    
    # Share Use Cases
    "CreateShareUseCase",
    "UpdateShareUseCase",
    "AccessSharedResourceUseCase",
    "RevokeShareUseCase",
    "GetShareByIdUseCase",
    "ListSharesUseCase",
    "DeleteShareUseCase",
    "BulkUpdateSharesUseCase",
    "BulkRevokeSharesUseCase",
    "GetShareStatsUseCase",
    "GetShareAnalyticsUseCase",
    "GetShareAccessLogUseCase",
    "CreateShareTemplateUseCase",
]