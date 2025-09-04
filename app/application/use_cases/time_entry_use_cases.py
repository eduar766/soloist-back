"""
Time Entry use cases for the application layer.
Implements business logic for time tracking operations.
"""

from typing import List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.time_entry_dto import (
    StartTimerRequestDTO, StopTimerRequestDTO, CreateTimeEntryRequestDTO,
    UpdateTimeEntryRequestDTO, SubmitTimeEntryRequestDTO, ApproveTimeEntryRequestDTO,
    RejectTimeEntryRequestDTO, ListTimeEntriesRequestDTO, SearchTimeEntriesRequestDTO,
    TimeEntryReportRequestDTO, RunningTimerResponseDTO, TimeEntryResponseDTO,
    TimeEntrySummaryResponseDTO, TimeEntryStatsResponseDTO, TimeEntryReportResponseDTO,
    DailyTimeStatsDTO, BulkUpdateTimeEntriesRequestDTO, BulkDeleteTimeEntriesRequestDTO,
    TimeTrackingAnalyticsResponseDTO, ExportTimeEntriesRequestDTO
)
from app.domain.models.time_entry import (
    TimeEntry, TimeEntryStatus, TimeEntryType
)
from app.domain.repositories.time_entry_repository import TimeEntryRepository
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.task_repository import TaskRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.time_tracking_service import TimeTrackingService


class StartTimerUseCase(AuthorizedUseCase, CreateUseCase[StartTimerRequestDTO, RunningTimerResponseDTO]):
    """Use case for starting a timer."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository,
        time_tracking_service: TimeTrackingService
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
        self.task_repository = task_repository
        self.time_tracking_service = time_tracking_service
    
    async def _execute_command_logic(self, request: StartTimerRequestDTO) -> RunningTimerResponseDTO:
        # Verify project and access
        project = await self.project_repository.find_by_id(request.project_id)
        if not project:
            raise ValueError("Project not found")
        
        member = project.get_member(self.current_user_id)
        if not member or not member.can_track_time:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Verify task if provided
        task = None
        if request.task_id:
            task = await self.task_repository.find_by_id(request.task_id)
            if not task or task.project_id != request.project_id:
                raise ValueError("Task not found or not in the specified project")
        
        # Stop any running timer for this user
        running_timer = await self.time_entry_repository.find_running_timer(self.current_user_id)
        if running_timer:
            await self.time_tracking_service.stop_timer(running_timer.id, self.current_user_id)
        
        # Create and start timer
        time_entry = TimeEntry.create_and_start(
            user_id=self.current_user_id,
            project_id=request.project_id,
            task_id=request.task_id,
            description=request.description,
            entry_type=request.entry_type or TimeEntryType.WORK,
            billable=request.billable if request.billable is not None else True,
            hourly_rate=request.hourly_rate or member.hourly_rate
        )
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return RunningTimerResponseDTO(
            id=saved_entry.id,
            project_id=saved_entry.project_id,
            project_name=project.name,
            task_id=saved_entry.task_id,
            task_title=task.title if task else None,
            description=saved_entry.description,
            started_at=saved_entry.started_at,
            elapsed_time=saved_entry.elapsed_time,
            is_billable=saved_entry.billable,
            hourly_rate=saved_entry.hourly_rate
        )


class StopTimerUseCase(AuthorizedUseCase, UpdateUseCase[StopTimerRequestDTO, TimeEntryResponseDTO]):
    """Use case for stopping a timer."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        time_tracking_service: TimeTrackingService
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.time_tracking_service = time_tracking_service
    
    async def _execute_command_logic(self, request: StopTimerRequestDTO) -> TimeEntryResponseDTO:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(request.id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        if time_entry.user_id != self.current_user_id:
            raise ValueError("Can only stop your own timer")
        
        # Stop timer
        time_entry.stop(
            description=request.description or time_entry.description,
            billable=request.billable if request.billable is not None else time_entry.billable
        )
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class CreateTimeEntryUseCase(AuthorizedUseCase, CreateUseCase[CreateTimeEntryRequestDTO, TimeEntryResponseDTO]):
    """Use case for creating a manual time entry."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
        self.task_repository = task_repository
    
    async def _execute_command_logic(self, request: CreateTimeEntryRequestDTO) -> TimeEntryResponseDTO:
        # Verify project and access
        project = await self.project_repository.find_by_id(request.project_id)
        if not project:
            raise ValueError("Project not found")
        
        member = project.get_member(self.current_user_id)
        if not member or not member.can_track_time:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Verify task if provided
        if request.task_id:
            task = await self.task_repository.find_by_id(request.task_id)
            if not task or task.project_id != request.project_id:
                raise ValueError("Task not found or not in the specified project")
        
        # Validate time range
        if request.started_at >= request.ended_at:
            raise ValueError("Start time must be before end time")
        
        # Check for overlapping entries
        overlapping = await self.time_entry_repository.find_overlapping_entries(
            self.current_user_id, request.started_at, request.ended_at
        )
        if overlapping:
            raise ValueError("Time entry overlaps with existing entry")
        
        # Create time entry
        time_entry = TimeEntry.create_manual(
            user_id=self.current_user_id,
            project_id=request.project_id,
            task_id=request.task_id,
            description=request.description,
            started_at=request.started_at,
            ended_at=request.ended_at,
            entry_type=request.entry_type or TimeEntryType.WORK,
            billable=request.billable if request.billable is not None else True,
            hourly_rate=request.hourly_rate or member.hourly_rate
        )
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class UpdateTimeEntryUseCase(AuthorizedUseCase, UpdateUseCase[UpdateTimeEntryRequestDTO, TimeEntryResponseDTO]):
    """Use case for updating a time entry."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
        self.task_repository = task_repository
    
    async def _execute_command_logic(self, request: UpdateTimeEntryRequestDTO) -> TimeEntryResponseDTO:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(request.id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        if time_entry.user_id != self.current_user_id:
            project = await self.project_repository.find_by_id(time_entry.project_id)
            if project:
                member = project.get_member(self.current_user_id)
                if not member or not member.can_manage_project:
                    self._require_owner_or_role(project.owner_id, "admin")
        
        # Check if entry is editable
        if time_entry.status in [TimeEntryStatus.APPROVED, TimeEntryStatus.INVOICED]:
            raise ValueError("Cannot edit approved or invoiced time entries")
        
        # Verify task if provided
        if request.task_id is not None:
            if request.task_id:
                task = await self.task_repository.find_by_id(request.task_id)
                if not task or task.project_id != time_entry.project_id:
                    raise ValueError("Task not found or not in the same project")
        
        # Update fields
        if request.description is not None:
            time_entry.description = request.description
        if request.started_at is not None and request.ended_at is not None:
            if request.started_at >= request.ended_at:
                raise ValueError("Start time must be before end time")
            
            # Check for overlapping entries (excluding current entry)
            overlapping = await self.time_entry_repository.find_overlapping_entries(
                time_entry.user_id, request.started_at, request.ended_at, exclude_id=time_entry.id
            )
            if overlapping:
                raise ValueError("Time entry overlaps with existing entry")
            
            time_entry.update_time_range(request.started_at, request.ended_at)
        
        if request.task_id is not None:
            time_entry.task_id = request.task_id
        if request.entry_type is not None:
            time_entry.entry_type = request.entry_type
        if request.billable is not None:
            time_entry.billable = request.billable
        if request.hourly_rate is not None:
            time_entry.hourly_rate = request.hourly_rate
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class SubmitTimeEntryUseCase(AuthorizedUseCase, UpdateUseCase[SubmitTimeEntryRequestDTO, TimeEntryResponseDTO]):
    """Use case for submitting time entries for approval."""
    
    def __init__(self, time_entry_repository: TimeEntryRepository):
        super().__init__()
        self.time_entry_repository = time_entry_repository
    
    async def _execute_command_logic(self, request: SubmitTimeEntryRequestDTO) -> TimeEntryResponseDTO:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(request.id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        if time_entry.user_id != self.current_user_id:
            raise ValueError("Can only submit your own time entries")
        
        # Submit for approval
        time_entry.submit_for_approval(notes=request.notes)
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class ApproveTimeEntryUseCase(AuthorizedUseCase, UpdateUseCase[ApproveTimeEntryRequestDTO, TimeEntryResponseDTO]):
    """Use case for approving time entries."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: ApproveTimeEntryRequestDTO) -> TimeEntryResponseDTO:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(request.id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(time_entry.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member or not member.can_manage_project:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Approve time entry
        time_entry.approve(
            approved_by=self.current_user_id,
            approved_hours=request.approved_hours,
            notes=request.notes
        )
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class RejectTimeEntryUseCase(AuthorizedUseCase, UpdateUseCase[RejectTimeEntryRequestDTO, TimeEntryResponseDTO]):
    """Use case for rejecting time entries."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: RejectTimeEntryRequestDTO) -> TimeEntryResponseDTO:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(request.id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(time_entry.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member or not member.can_manage_project:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Reject time entry
        time_entry.reject(
            rejected_by=self.current_user_id,
            reason=request.reason
        )
        
        # Save time entry
        saved_entry = await self.time_entry_repository.save(time_entry)
        
        return await self._time_entry_to_response_dto(saved_entry)


class GetTimeEntryByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, TimeEntryResponseDTO]):
    """Use case for getting time entry by ID."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, time_entry_id: int) -> TimeEntryResponseDTO:
        time_entry = await self.time_entry_repository.find_by_id(time_entry_id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        if time_entry.user_id != self.current_user_id:
            project = await self.project_repository.find_by_id(time_entry.project_id)
            if project:
                member = project.get_member(self.current_user_id)
                if not member:
                    self._require_owner_or_role(project.owner_id, "admin")
        
        return await self._time_entry_to_response_dto(time_entry)


class ListTimeEntriesUseCase(AuthorizedUseCase, ListUseCase[ListTimeEntriesRequestDTO, TimeEntrySummaryResponseDTO]):
    """Use case for listing time entries with filters."""
    
    def __init__(self, time_entry_repository: TimeEntryRepository):
        super().__init__()
        self.time_entry_repository = time_entry_repository
    
    async def _execute_business_logic(self, request: ListTimeEntriesRequestDTO) -> List[TimeEntrySummaryResponseDTO]:
        # Determine user filter based on request
        user_id = None
        if request.user_id:
            # TODO: Check if current user can view other user's entries
            user_id = request.user_id
        else:
            user_id = self.current_user_id
        
        time_entries = await self.time_entry_repository.find_with_filters(
            user_id=user_id,
            project_id=request.project_id,
            client_id=request.client_id,
            task_id=request.task_id,
            status=request.status,
            entry_type=request.entry_type,
            billable=request.billable,
            date_from=request.date_from,
            date_to=request.date_to,
            search=request.search,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [await self._time_entry_to_summary_dto(entry) for entry in time_entries]


class SearchTimeEntriesUseCase(AuthorizedUseCase, SearchUseCase[SearchTimeEntriesRequestDTO, TimeEntrySummaryResponseDTO]):
    """Use case for searching time entries."""
    
    def __init__(self, time_entry_repository: TimeEntryRepository):
        super().__init__()
        self.time_entry_repository = time_entry_repository
    
    async def _execute_business_logic(self, request: SearchTimeEntriesRequestDTO) -> List[TimeEntrySummaryResponseDTO]:
        time_entries = await self.time_entry_repository.search_time_entries(
            user_id=self.current_user_id,
            query=request.query,
            project_id=request.project_id,
            status=request.status,
            billable=request.billable,
            date_from=request.date_from,
            date_to=request.date_to,
            page=request.page,
            page_size=request.page_size
        )
        
        return [await self._time_entry_to_summary_dto(entry) for entry in time_entries]


class DeleteTimeEntryUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting a time entry."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, time_entry_id: int) -> bool:
        # Get time entry
        time_entry = await self.time_entry_repository.find_by_id(time_entry_id)
        if not time_entry:
            raise ValueError("Time entry not found")
        
        # Check authorization
        if time_entry.user_id != self.current_user_id:
            project = await self.project_repository.find_by_id(time_entry.project_id)
            if project:
                member = project.get_member(self.current_user_id)
                if not member or not member.can_manage_project:
                    self._require_owner_or_role(project.owner_id, "admin")
        
        # Check if entry can be deleted
        if time_entry.status == TimeEntryStatus.INVOICED:
            raise ValueError("Cannot delete invoiced time entries")
        
        # Delete time entry
        await self.time_entry_repository.delete(time_entry_id)
        
        return True


class BulkUpdateTimeEntriesUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateTimeEntriesRequestDTO, dict]):
    """Use case for bulk updating time entries."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: BulkUpdateTimeEntriesRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for entry_id in request.time_entry_ids:
            try:
                # Get time entry
                time_entry = await self.time_entry_repository.find_by_id(entry_id)
                if not time_entry:
                    results["errors"].append({"id": entry_id, "error": "Time entry not found"})
                    continue
                
                # Check authorization
                if time_entry.user_id != self.current_user_id:
                    project = await self.project_repository.find_by_id(time_entry.project_id)
                    if project:
                        member = project.get_member(self.current_user_id)
                        if not member or not member.can_manage_project:
                            results["errors"].append({"id": entry_id, "error": "Insufficient permissions"})
                            continue
                
                # Check if entry is editable
                if time_entry.status in [TimeEntryStatus.APPROVED, TimeEntryStatus.INVOICED]:
                    results["errors"].append({"id": entry_id, "error": "Cannot edit approved or invoiced entries"})
                    continue
                
                # Apply updates
                if request.billable is not None:
                    time_entry.billable = request.billable
                if request.entry_type is not None:
                    time_entry.entry_type = request.entry_type
                if request.status is not None:
                    if request.status == TimeEntryStatus.SUBMITTED:
                        time_entry.submit_for_approval()
                    else:
                        time_entry.status = request.status
                
                # Save time entry
                await self.time_entry_repository.save(time_entry)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": entry_id, "error": str(e)})
        
        return results


class BulkDeleteTimeEntriesUseCase(AuthorizedUseCase, BulkUseCase[BulkDeleteTimeEntriesRequestDTO, dict]):
    """Use case for bulk deleting time entries."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: BulkDeleteTimeEntriesRequestDTO) -> dict:
        results = {"deleted": 0, "errors": []}
        
        for entry_id in request.time_entry_ids:
            try:
                # Get time entry
                time_entry = await self.time_entry_repository.find_by_id(entry_id)
                if not time_entry:
                    results["errors"].append({"id": entry_id, "error": "Time entry not found"})
                    continue
                
                # Check authorization
                if time_entry.user_id != self.current_user_id:
                    project = await self.project_repository.find_by_id(time_entry.project_id)
                    if project:
                        member = project.get_member(self.current_user_id)
                        if not member or not member.can_manage_project:
                            results["errors"].append({"id": entry_id, "error": "Insufficient permissions"})
                            continue
                
                # Check if entry can be deleted
                if time_entry.status == TimeEntryStatus.INVOICED:
                    results["errors"].append({"id": entry_id, "error": "Cannot delete invoiced entries"})
                    continue
                
                # Delete time entry
                await self.time_entry_repository.delete(entry_id)
                results["deleted"] += 1
                
            except Exception as e:
                results["errors"].append({"id": entry_id, "error": str(e)})
        
        return results


class GetRunningTimerUseCase(AuthorizedUseCase, GetByIdUseCase[int, RunningTimerResponseDTO]):
    """Use case for getting the current running timer for a user."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.project_repository = project_repository
        self.task_repository = task_repository
    
    async def _execute_business_logic(self, user_id: int) -> RunningTimerResponseDTO:
        # Check authorization
        if user_id != self.current_user_id:
            raise ValueError("Can only view your own running timer")
        
        # Get running timer
        running_timer = await self.time_entry_repository.find_running_timer(user_id)
        if not running_timer:
            raise ValueError("No running timer found")
        
        # Get additional info
        project = await self.project_repository.find_by_id(running_timer.project_id)
        task = None
        if running_timer.task_id:
            task = await self.task_repository.find_by_id(running_timer.task_id)
        
        return RunningTimerResponseDTO(
            id=running_timer.id,
            project_id=running_timer.project_id,
            project_name=project.name if project else "",
            task_id=running_timer.task_id,
            task_title=task.title if task else None,
            description=running_timer.description,
            started_at=running_timer.started_at,
            elapsed_time=running_timer.elapsed_time,
            is_billable=running_timer.billable,
            hourly_rate=running_timer.hourly_rate
        )


class GetTimeTrackingAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[int, TimeTrackingAnalyticsResponseDTO]):
    """Use case for getting time tracking analytics."""
    
    def __init__(
        self, 
        time_entry_repository: TimeEntryRepository,
        time_tracking_service: TimeTrackingService
    ):
        super().__init__()
        self.time_entry_repository = time_entry_repository
        self.time_tracking_service = time_tracking_service
    
    async def _execute_business_logic(self, user_id: int) -> TimeTrackingAnalyticsResponseDTO:
        # Check authorization
        if user_id != self.current_user_id:
            # TODO: Check if user has permission to view analytics for other users
            pass
        
        # Get analytics
        analytics = await self.time_tracking_service.get_user_analytics(
            user_id, 
            days_back=30  # TODO: Make this configurable
        )
        
        return TimeTrackingAnalyticsResponseDTO(
            user_id=user_id,
            period_days=30,
            total_hours=analytics.total_hours,
            billable_hours=analytics.billable_hours,
            non_billable_hours=analytics.non_billable_hours,
            total_earnings=analytics.total_earnings,
            avg_hourly_rate=analytics.avg_hourly_rate,
            daily_stats=analytics.daily_stats,
            project_breakdown=analytics.project_breakdown,
            task_breakdown=analytics.task_breakdown,
            time_patterns=analytics.time_patterns,
            efficiency_metrics=analytics.efficiency_metrics
        )


    async def _time_entry_to_response_dto(self, time_entry: TimeEntry) -> TimeEntryResponseDTO:
        """Convert TimeEntry domain model to response DTO."""
        # Get project info
        project = await self.project_repository.find_by_id(time_entry.project_id) if hasattr(self, 'project_repository') else None
        
        # Get task info
        task = None
        if time_entry.task_id and hasattr(self, 'task_repository'):
            task = await self.task_repository.find_by_id(time_entry.task_id)
        
        # Get user info
        user = None
        if hasattr(self, 'user_repository'):
            user = await self.user_repository.find_by_id(time_entry.user_id)
        
        # Get approver info
        approved_by_user = None
        if time_entry.approved_by and hasattr(self, 'user_repository'):
            approved_by_user = await self.user_repository.find_by_id(time_entry.approved_by)
        
        return TimeEntryResponseDTO(
            id=time_entry.id,
            user_id=time_entry.user_id,
            user_name=user.full_name if user else "",
            project_id=time_entry.project_id,
            project_name=project.name if project else "",
            task_id=time_entry.task_id,
            task_title=task.title if task else None,
            description=time_entry.description,
            started_at=time_entry.started_at,
            ended_at=time_entry.ended_at,
            duration_hours=time_entry.duration_hours,
            billable=time_entry.billable,
            hourly_rate=time_entry.hourly_rate,
            total_amount=time_entry.total_amount,
            entry_type=time_entry.entry_type,
            status=time_entry.status,
            submitted_at=time_entry.submitted_at,
            approved_at=time_entry.approved_at,
            approved_by=time_entry.approved_by,
            approved_by_name=approved_by_user.full_name if approved_by_user else None,
            approved_hours=time_entry.approved_hours,
            rejected_at=time_entry.rejected_at,
            rejected_by=time_entry.rejected_by,
            rejection_reason=time_entry.rejection_reason,
            notes=time_entry.notes,
            is_running=time_entry.is_running,
            elapsed_time=time_entry.elapsed_time,
            can_edit=time_entry.can_edit,
            can_delete=time_entry.can_delete,
            created_at=time_entry.created_at,
            updated_at=time_entry.updated_at
        )
    
    async def _time_entry_to_summary_dto(self, time_entry: TimeEntry) -> TimeEntrySummaryResponseDTO:
        """Convert TimeEntry domain model to summary DTO."""
        # Get project info
        project = await self.project_repository.find_by_id(time_entry.project_id) if hasattr(self, 'project_repository') else None
        
        # Get task info
        task = None
        if time_entry.task_id and hasattr(self, 'task_repository'):
            task = await self.task_repository.find_by_id(time_entry.task_id)
        
        return TimeEntrySummaryResponseDTO(
            id=time_entry.id,
            project_id=time_entry.project_id,
            project_name=project.name if project else "",
            task_id=time_entry.task_id,
            task_title=task.title if task else None,
            description=time_entry.description,
            date=time_entry.started_at.date(),
            duration_hours=time_entry.duration_hours,
            billable=time_entry.billable,
            hourly_rate=time_entry.hourly_rate,
            total_amount=time_entry.total_amount,
            status=time_entry.status,
            entry_type=time_entry.entry_type,
            is_running=time_entry.is_running,
            created_at=time_entry.created_at
        )