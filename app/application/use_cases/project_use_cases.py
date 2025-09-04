"""
Project use cases for the application layer.
Implements business logic for project operations.
"""

from typing import List, Optional
from datetime import datetime, date
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.project_dto import (
    CreateProjectRequestDTO, UpdateProjectRequestDTO, UpdateProjectStatusRequestDTO,
    AddProjectMemberRequestDTO, UpdateProjectMemberRequestDTO, ListProjectsRequestDTO,
    SearchProjectsRequestDTO, ProjectTimeRangeRequestDTO, ProjectResponseDTO,
    ProjectSummaryResponseDTO, ProjectStatsResponseDTO, ProjectActivityResponseDTO,
    ProjectReportResponseDTO, BulkUpdateProjectsRequestDTO, ArchiveProjectRequestDTO,
    ProjectAnalyticsResponseDTO, ProjectMemberResponseDTO, ProjectBudgetResponseDTO,
    ProjectTimeStatsDTO
)
from app.domain.models.project import (
    Project, ProjectMember, BillingConfiguration, ProjectStatus, 
    ProjectType, ProjectRole, BillingType
)
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.user_repository import UserRepositoryInterface as UserRepository
from app.domain.services.billing_service import BillingService
# from app.domain.services.project_service import ProjectService
from app.domain.events.base import publish_event
from app.domain.events.project_events import ProjectCreated, ProjectStatusChanged, ProjectCompleted


class CreateProjectUseCase(AuthorizedUseCase, CreateUseCase[CreateProjectRequestDTO, ProjectResponseDTO]):
    """Use case for creating a new project."""
    
    def __init__(
        self, 
        project_repository: ProjectRepository,
        client_repository: ClientRepository,
        user_repository: UserRepository
    ):
        super().__init__()
        self.project_repository = project_repository
        self.client_repository = client_repository
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: CreateProjectRequestDTO) -> ProjectResponseDTO:
        # Verify client exists and user has access
        client = await self.client_repository.find_by_id(request.client_id)
        if not client:
            raise ValueError("Client not found")
        
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Create billing configuration
        billing_config = BillingConfiguration(
            billing_type=request.billing_type,
            hourly_rate=request.hourly_rate,
            fixed_price=request.fixed_price,
            budget_hours=request.budget_hours,
            budget_amount=request.budget_amount,
            auto_create_invoices=request.auto_create_invoices,
            invoice_frequency=request.invoice_frequency
        )
        
        # Create project
        project = Project.create(
            owner_id=self.current_user_id,
            client_id=request.client_id,
            name=request.name,
            description=request.description,
            project_type=request.project_type,
            start_date=request.start_date,
            end_date=request.end_date,
            billing_configuration=billing_config,
            tags=request.tags,
            notes=request.notes
        )
        
        # Add project owner as admin member
        project.add_member(
            user_id=self.current_user_id,
            role=ProjectRole.ADMIN,
            hourly_rate=request.hourly_rate or client.default_hourly_rate,
            can_track_time=True,
            can_create_tasks=True,
            can_manage_members=True
        )
        
        # Save project
        saved_project = await self.project_repository.save(project)
        
        # Publish project created event
        await publish_event(ProjectCreated(
            project_id=saved_project.id,
            client_id=saved_project.client_id,
            user_id=self.current_user_id,
            project_name=saved_project.name,
            project_type=saved_project.project_type.value if saved_project.project_type else None,
            budget=float(saved_project.budget) if saved_project.budget else None,
            currency=saved_project.currency,
            start_date=saved_project.start_date,
            end_date=saved_project.end_date
        ))
        
        return await self._project_to_response_dto(saved_project)


class UpdateProjectUseCase(AuthorizedUseCase, UpdateUseCase[UpdateProjectRequestDTO, ProjectResponseDTO]):
    """Use case for updating project information."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _check_authorization(self, request: UpdateProjectRequestDTO) -> None:
        if hasattr(request, 'id'):
            project = await self.project_repository.find_by_id(request.id)
            if project:
                member = project.get_member(self.current_user_id)
                if not member or not member.can_manage_project:
                    self._require_owner_or_role(project.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateProjectRequestDTO) -> ProjectResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(request.id)
        if not project:
            raise ValueError("Project not found")
        
        # Update fields
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.project_type is not None:
            project.project_type = request.project_type
        if request.start_date is not None:
            project.start_date = request.start_date
        if request.end_date is not None:
            project.end_date = request.end_date
        if request.tags is not None:
            project.tags = request.tags
        if request.notes is not None:
            project.notes = request.notes
        
        # Update billing configuration
        if any([
            request.billing_type is not None,
            request.hourly_rate is not None,
            request.fixed_price is not None,
            request.budget_hours is not None,
            request.budget_amount is not None,
            request.auto_create_invoices is not None,
            request.invoice_frequency is not None
        ]):
            project.update_billing_configuration(
                billing_type=request.billing_type,
                hourly_rate=request.hourly_rate,
                fixed_price=request.fixed_price,
                budget_hours=request.budget_hours,
                budget_amount=request.budget_amount,
                auto_create_invoices=request.auto_create_invoices,
                invoice_frequency=request.invoice_frequency
            )
        
        # Save project
        saved_project = await self.project_repository.save(project)
        
        return await self._project_to_response_dto(saved_project)


class UpdateProjectStatusUseCase(AuthorizedUseCase, UpdateUseCase[UpdateProjectStatusRequestDTO, ProjectResponseDTO]):
    """Use case for updating project status."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: UpdateProjectStatusRequestDTO) -> ProjectResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(request.id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member or not member.can_manage_project:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Store old status for event
        old_status = project.status.value
        
        # Update status
        if request.status == ProjectStatus.COMPLETED:
            project.complete(completion_notes=request.notes)
        elif request.status == ProjectStatus.ON_HOLD:
            project.put_on_hold(reason=request.notes)
        elif request.status == ProjectStatus.CANCELLED:
            project.cancel(reason=request.notes)
        else:
            project.status = request.status
        
        # Save project
        saved_project = await self.project_repository.save(project)
        
        # Publish project status changed event
        await publish_event(ProjectStatusChanged(
            project_id=saved_project.id,
            client_id=saved_project.client_id,
            user_id=self.current_user_id,
            project_name=saved_project.name,
            old_status=old_status,
            new_status=saved_project.status.value,
            status_reason=request.notes
        ))
        
        # If project completed, also publish completion event
        if request.status == ProjectStatus.COMPLETED:
            await publish_event(ProjectCompleted(
                project_id=saved_project.id,
                client_id=saved_project.client_id,
                user_id=self.current_user_id,
                project_name=saved_project.name,
                completion_date=saved_project.completed_at or datetime.now(),
                total_hours=None,  # Would need to calculate from time entries
                total_cost=None,   # Would need to calculate from billing
                currency=saved_project.currency
            ))
        
        return await self._project_to_response_dto(saved_project)


class AddProjectMemberUseCase(AuthorizedUseCase, CreateUseCase[AddProjectMemberRequestDTO, ProjectMemberResponseDTO]):
    """Use case for adding a member to a project."""
    
    def __init__(
        self, 
        project_repository: ProjectRepository,
        user_repository: UserRepository
    ):
        super().__init__()
        self.project_repository = project_repository
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: AddProjectMemberRequestDTO) -> ProjectMemberResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(request.project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member or not member.can_manage_members:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Verify user exists
        user = await self.user_repository.find_by_id(request.user_id)
        if not user:
            raise ValueError("User not found")
        
        # Add member
        project.add_member(
            user_id=request.user_id,
            role=request.role,
            hourly_rate=request.hourly_rate,
            can_track_time=request.can_track_time,
            can_create_tasks=request.can_create_tasks,
            can_manage_members=request.can_manage_members
        )
        
        # Save project
        saved_project = await self.project_repository.save(project)
        
        # Return member response
        added_member = saved_project.get_member(request.user_id)
        return ProjectMemberResponseDTO(
            user_id=added_member.user_id,
            user_name=user.full_name,
            user_email=user.email,
            role=added_member.role,
            hourly_rate=added_member.hourly_rate,
            can_track_time=added_member.can_track_time,
            can_create_tasks=added_member.can_create_tasks,
            can_manage_members=added_member.can_manage_members,
            can_manage_project=added_member.can_manage_project,
            joined_at=added_member.joined_at,
            is_active=added_member.is_active
        )


class UpdateProjectMemberUseCase(AuthorizedUseCase, UpdateUseCase[UpdateProjectMemberRequestDTO, ProjectMemberResponseDTO]):
    """Use case for updating a project member."""
    
    def __init__(
        self, 
        project_repository: ProjectRepository,
        user_repository: UserRepository
    ):
        super().__init__()
        self.project_repository = project_repository
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: UpdateProjectMemberRequestDTO) -> ProjectMemberResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(request.project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member or not member.can_manage_members:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Update member
        project.update_member(
            user_id=request.user_id,
            role=request.role,
            hourly_rate=request.hourly_rate,
            can_track_time=request.can_track_time,
            can_create_tasks=request.can_create_tasks,
            can_manage_members=request.can_manage_members
        )
        
        # Save project
        saved_project = await self.project_repository.save(project)
        
        # Get user info
        user = await self.user_repository.find_by_id(request.user_id)
        
        # Return member response
        updated_member = saved_project.get_member(request.user_id)
        return ProjectMemberResponseDTO(
            user_id=updated_member.user_id,
            user_name=user.full_name if user else "",
            user_email=user.email if user else "",
            role=updated_member.role,
            hourly_rate=updated_member.hourly_rate,
            can_track_time=updated_member.can_track_time,
            can_create_tasks=updated_member.can_create_tasks,
            can_manage_members=updated_member.can_manage_members,
            can_manage_project=updated_member.can_manage_project,
            joined_at=updated_member.joined_at,
            is_active=updated_member.is_active
        )


class GetProjectByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, ProjectResponseDTO]):
    """Use case for getting project by ID."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, project_id: int) -> ProjectResponseDTO:
        project = await self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member:
            self._require_owner_or_role(project.owner_id, "admin")
        
        return await self._project_to_response_dto(project)


class ListProjectsUseCase(AuthorizedUseCase, ListUseCase[ListProjectsRequestDTO, ProjectSummaryResponseDTO]):
    """Use case for listing projects with filters."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: ListProjectsRequestDTO) -> List[ProjectSummaryResponseDTO]:
        projects = await self.project_repository.find_with_filters(
            owner_id=self.current_user_id if request.include_member_projects else self.current_user_id,
            member_user_id=self.current_user_id if request.include_member_projects else None,
            client_id=request.client_id,
            status=request.status,
            project_type=request.project_type,
            billing_type=request.billing_type,
            is_overbudget=request.is_overbudget,
            is_overdue=request.is_overdue,
            has_active_tasks=request.has_active_tasks,
            tags=request.tags,
            search=request.search,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [await self._project_to_summary_dto(project) for project in projects]


class SearchProjectsUseCase(AuthorizedUseCase, SearchUseCase[SearchProjectsRequestDTO, ProjectSummaryResponseDTO]):
    """Use case for searching projects."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: SearchProjectsRequestDTO) -> List[ProjectSummaryResponseDTO]:
        projects = await self.project_repository.search_projects(
            user_id=self.current_user_id,
            query=request.query,
            client_id=request.client_id,
            status=request.status,
            project_type=request.project_type,
            page=request.page,
            page_size=request.page_size
        )
        
        return [await self._project_to_summary_dto(project) for project in projects]


class DeleteProjectUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting a project."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, project_id: int) -> bool:
        # Get project
        project = await self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        self._require_owner_or_role(project.owner_id, "admin")
        
        # Check if project has time entries or invoices
        stats = await self.project_repository.get_project_stats(project_id)
        if stats and (stats.total_hours > 0 or stats.total_invoiced > 0):
            raise ValueError("Cannot delete project with time entries or invoices")
        
        # Delete project
        await self.project_repository.delete(project_id)
        
        return True


class ArchiveProjectUseCase(AuthorizedUseCase, UpdateUseCase[ArchiveProjectRequestDTO, bool]):
    """Use case for archiving a project."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: ArchiveProjectRequestDTO) -> bool:
        # Get project
        project = await self.project_repository.find_by_id(request.id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member or not member.can_manage_project:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Archive project
        project.archive(reason=request.reason)
        
        # Save project
        await self.project_repository.save(project)
        
        return True


class BulkUpdateProjectsUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateProjectsRequestDTO, dict]):
    """Use case for bulk updating projects."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: BulkUpdateProjectsRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for project_id in request.project_ids:
            try:
                # Get project
                project = await self.project_repository.find_by_id(project_id)
                if not project:
                    results["errors"].append({"id": project_id, "error": "Project not found"})
                    continue
                
                # Check authorization
                member = project.get_member(self.current_user_id)
                if not member and project.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": project_id, "error": "Insufficient permissions"})
                    continue
                
                # Apply updates
                if request.status is not None:
                    project.status = request.status
                if request.tags_to_add:
                    project.add_tags(request.tags_to_add)
                if request.tags_to_remove:
                    project.remove_tags(request.tags_to_remove)
                if request.billing_type is not None and project.billing_configuration:
                    project.billing_configuration.billing_type = request.billing_type
                
                # Save project
                await self.project_repository.save(project)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": project_id, "error": str(e)})
        
        return results


class GetProjectStatsUseCase(AuthorizedUseCase, GetByIdUseCase[int, ProjectStatsResponseDTO]):
    """Use case for getting project statistics."""
    
    def __init__(self, project_repository: ProjectRepository):
        super().__init__()
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, project_id: int) -> ProjectStatsResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Get stats
        stats = await self.project_repository.get_project_stats(project_id)
        
        return ProjectStatsResponseDTO(
            project_id=project.id,
            project_name=project.name,
            total_tasks=stats.total_tasks if stats else 0,
            completed_tasks=stats.completed_tasks if stats else 0,
            active_tasks=stats.active_tasks if stats else 0,
            overdue_tasks=stats.overdue_tasks if stats else 0,
            total_hours=stats.total_hours if stats else 0.0,
            billable_hours=stats.billable_hours if stats else 0.0,
            non_billable_hours=stats.non_billable_hours if stats else 0.0,
            total_invoiced=stats.total_invoiced if stats else 0.0,
            total_paid=stats.total_paid if stats else 0.0,
            outstanding_balance=stats.outstanding_balance if stats else 0.0,
            budget_utilization=stats.budget_utilization if stats else 0.0,
            is_overbudget=stats.is_overbudget if stats else False,
            is_overdue=project.is_overdue,
            completion_percentage=stats.completion_percentage if stats else 0.0,
            avg_task_completion_time=stats.avg_task_completion_time if stats else None,
            last_activity=stats.last_activity if stats else None
        )


class GetProjectAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[int, ProjectAnalyticsResponseDTO]):
    """Use case for getting project analytics."""
    
    def __init__(
        self, 
        project_repository: ProjectRepository
        # project_service: ProjectService
    ):
        super().__init__()
        self.project_repository = project_repository
        # self.project_service = project_service
    
    async def _execute_business_logic(self, project_id: int) -> ProjectAnalyticsResponseDTO:
        # Get project
        project = await self.project_repository.find_by_id(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Check authorization
        member = project.get_member(self.current_user_id)
        if not member:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Get analytics
        analytics = await self.project_service.get_project_analytics(project_id)
        
        return ProjectAnalyticsResponseDTO(
            project_id=project.id,
            project_name=project.name,
            time_analytics=analytics.time_analytics,
            budget_analytics=analytics.budget_analytics,
            task_analytics=analytics.task_analytics,
            member_analytics=analytics.member_analytics,
            invoice_analytics=analytics.invoice_analytics,
            productivity_metrics=analytics.productivity_metrics,
            risk_indicators=analytics.risk_indicators
        )


    async def _project_to_response_dto(self, project: Project) -> ProjectResponseDTO:
        """Convert Project domain model to response DTO."""
        # Get client info
        client = await self.client_repository.find_by_id(project.client_id) if hasattr(self, 'client_repository') else None
        
        # Convert members
        members = []
        for member in project.members:
            user = await self.user_repository.find_by_id(member.user_id) if hasattr(self, 'user_repository') else None
            members.append(ProjectMemberResponseDTO(
                user_id=member.user_id,
                user_name=user.full_name if user else "",
                user_email=user.email if user else "",
                role=member.role,
                hourly_rate=member.hourly_rate,
                can_track_time=member.can_track_time,
                can_create_tasks=member.can_create_tasks,
                can_manage_members=member.can_manage_members,
                can_manage_project=member.can_manage_project,
                joined_at=member.joined_at,
                is_active=member.is_active
            ))
        
        # Get stats
        stats = await self.project_repository.get_project_stats(project.id)
        project_stats = None
        if stats:
            project_stats = ProjectStatsResponseDTO(
                project_id=project.id,
                project_name=project.name,
                total_tasks=stats.total_tasks,
                completed_tasks=stats.completed_tasks,
                active_tasks=stats.active_tasks,
                overdue_tasks=stats.overdue_tasks,
                total_hours=stats.total_hours,
                billable_hours=stats.billable_hours,
                non_billable_hours=stats.non_billable_hours,
                total_invoiced=stats.total_invoiced,
                total_paid=stats.total_paid,
                outstanding_balance=stats.outstanding_balance,
                budget_utilization=stats.budget_utilization,
                is_overbudget=stats.is_overbudget,
                is_overdue=project.is_overdue,
                completion_percentage=stats.completion_percentage,
                avg_task_completion_time=stats.avg_task_completion_time,
                last_activity=stats.last_activity
            )
        
        return ProjectResponseDTO(
            id=project.id,
            owner_id=project.owner_id,
            client_id=project.client_id,
            client_name=client.name if client else "",
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            status=project.status,
            start_date=project.start_date,
            end_date=project.end_date,
            billing_configuration=project.billing_configuration,
            members=members,
            stats=project_stats,
            tags=project.tags,
            notes=project.notes,
            is_active=project.is_active,
            is_archived=project.is_archived,
            is_overdue=project.is_overdue,
            can_be_deleted=project.can_be_deleted,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    async def _project_to_summary_dto(self, project: Project) -> ProjectSummaryResponseDTO:
        """Convert Project domain model to summary DTO."""
        # Get client info
        client = await self.client_repository.find_by_id(project.client_id) if hasattr(self, 'client_repository') else None
        
        return ProjectSummaryResponseDTO(
            id=project.id,
            name=project.name,
            client_name=client.name if client else "",
            status=project.status,
            project_type=project.project_type,
            billing_type=project.billing_configuration.billing_type if project.billing_configuration else None,
            total_tasks=0,  # Will be populated by repository query
            active_tasks=0,  # Will be populated by repository query
            completion_percentage=0.0,  # Will be populated by repository query
            total_hours=0.0,  # Will be populated by repository query
            budget_utilization=0.0,  # Will be populated by repository query
            is_overbudget=False,  # Will be populated by repository query
            is_overdue=project.is_overdue,
            last_activity=None,  # Will be populated by repository query
            start_date=project.start_date,
            end_date=project.end_date
        )