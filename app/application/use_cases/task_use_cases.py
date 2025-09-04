"""
Task use cases for the application layer.
Implements business logic for task operations.
"""

from typing import List, Optional
from datetime import datetime, date
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.task_dto import (
    CreateTaskRequestDTO, UpdateTaskRequestDTO, UpdateTaskStatusRequestDTO,
    AssignTaskRequestDTO, MoveTaskRequestDTO, ListTasksRequestDTO,
    SearchTasksRequestDTO, TaskTimeRangeRequestDTO, TaskResponseDTO,
    TaskSummaryResponseDTO, TaskActivityResponseDTO, TaskBoardResponseDTO,
    TaskReportResponseDTO, BulkUpdateTasksRequestDTO, BulkMoveTasksRequestDTO,
    TaskAnalyticsResponseDTO, TaskDependencyRequestDTO, TaskDependencyResponseDTO,
    TaskCommentRequestDTO, TaskCommentResponseDTO, TaskAttachmentRequestDTO,
    TaskAttachmentResponseDTO, TaskTimeStatsDTO
)
from app.domain.models.task import (
    Task, TaskComment, TaskAttachment, TaskStatus, 
    TaskPriority, TaskType
)
from app.domain.repositories.task_repository import TaskRepository
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.task_service import TaskService


class CreateTaskUseCase(AuthorizedUseCase, CreateUseCase[CreateTaskRequestDTO, TaskResponseDTO]):
    """Use case for creating a new task."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: CreateTaskRequestDTO) -> TaskResponseDTO:
        # Verify project exists and user has access
        project = await self.project_repository.find_by_id(request.project_id)
        if not project:
            raise ValueError("Project not found")
        
        member = project.get_member(self.current_user_id)
        if not member or not member.can_create_tasks:
            self._require_owner_or_role(project.owner_id, "admin")
        
        # Verify parent task if provided
        if request.parent_task_id:
            parent_task = await self.task_repository.find_by_id(request.parent_task_id)
            if not parent_task or parent_task.project_id != request.project_id:
                raise ValueError("Invalid parent task")
        
        # Verify assignee if provided
        if request.assignee_id:
            assignee_member = project.get_member(request.assignee_id)
            if not assignee_member:
                raise ValueError("Assignee must be a project member")
        
        # Create task
        task = Task.create(
            project_id=request.project_id,
            created_by=self.current_user_id,
            title=request.title,
            description=request.description,
            task_type=request.task_type,
            priority=request.priority,
            status=request.status or TaskStatus.TODO,
            assignee_id=request.assignee_id,
            parent_task_id=request.parent_task_id,
            estimated_hours=request.estimated_hours,
            due_date=request.due_date,
            tags=request.tags,
            custom_fields=request.custom_fields
        )
        
        # Save task
        saved_task = await self.task_repository.save(task)
        
        return await self._task_to_response_dto(saved_task)


class UpdateTaskUseCase(AuthorizedUseCase, UpdateUseCase[UpdateTaskRequestDTO, TaskResponseDTO]):
    """Use case for updating task information."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _check_authorization(self, request: UpdateTaskRequestDTO) -> None:
        if hasattr(request, 'id'):
            task = await self.task_repository.find_by_id(request.id)
            if task:
                project = await self.project_repository.find_by_id(task.project_id)
                if project:
                    member = project.get_member(self.current_user_id)
                    if not member or (not member.can_create_tasks and task.assignee_id != self.current_user_id):
                        self._require_owner_or_role(project.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateTaskRequestDTO) -> TaskResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.id)
        if not task:
            raise ValueError("Task not found")
        
        # Get project for authorization
        project = await self.project_repository.find_by_id(task.project_id)
        
        # Update fields
        if request.title is not None:
            task.title = request.title
        if request.description is not None:
            task.description = request.description
        if request.task_type is not None:
            task.task_type = request.task_type
        if request.priority is not None:
            task.priority = request.priority
        if request.estimated_hours is not None:
            task.estimated_hours = request.estimated_hours
        if request.due_date is not None:
            task.due_date = request.due_date
        if request.tags is not None:
            task.tags = request.tags
        if request.custom_fields is not None:
            task.custom_fields = request.custom_fields
        
        # Handle assignee change
        if request.assignee_id is not None:
            if request.assignee_id and project:
                assignee_member = project.get_member(request.assignee_id)
                if not assignee_member:
                    raise ValueError("Assignee must be a project member")
            task.assign_to(request.assignee_id, assigned_by=self.current_user_id)
        
        # Save task
        saved_task = await self.task_repository.save(task)
        
        return await self._task_to_response_dto(saved_task)


class UpdateTaskStatusUseCase(AuthorizedUseCase, UpdateUseCase[UpdateTaskStatusRequestDTO, TaskResponseDTO]):
    """Use case for updating task status."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: UpdateTaskStatusRequestDTO) -> TaskResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member or (not member.can_create_tasks and task.assignee_id != self.current_user_id):
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Update status
        if request.status == TaskStatus.IN_PROGRESS:
            task.start(started_by=self.current_user_id)
        elif request.status == TaskStatus.COMPLETED:
            task.complete(
                completed_by=self.current_user_id, 
                actual_hours=request.actual_hours,
                completion_notes=request.notes
            )
        elif request.status == TaskStatus.BLOCKED:
            task.block(reason=request.notes, blocked_by=self.current_user_id)
        else:
            task.status = request.status
        
        # Save task
        saved_task = await self.task_repository.save(task)
        
        return await self._task_to_response_dto(saved_task)


class AssignTaskUseCase(AuthorizedUseCase, UpdateUseCase[AssignTaskRequestDTO, TaskResponseDTO]):
    """Use case for assigning a task to a user."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: AssignTaskRequestDTO) -> TaskResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member or not member.can_create_tasks:
                self._require_owner_or_role(project.owner_id, "admin")
            
            # Verify assignee is project member
            if request.assignee_id:
                assignee_member = project.get_member(request.assignee_id)
                if not assignee_member:
                    raise ValueError("Assignee must be a project member")
        
        # Assign task
        task.assign_to(request.assignee_id, assigned_by=self.current_user_id)
        
        # Save task
        saved_task = await self.task_repository.save(task)
        
        return await self._task_to_response_dto(saved_task)


class MoveTaskUseCase(AuthorizedUseCase, UpdateUseCase[MoveTaskRequestDTO, TaskResponseDTO]):
    """Use case for moving a task within or between projects."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: MoveTaskRequestDTO) -> TaskResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization for source project
        source_project = await self.project_repository.find_by_id(task.project_id)
        if source_project:
            member = source_project.get_member(self.current_user_id)
            if not member or not member.can_create_tasks:
                self._require_owner_or_role(source_project.owner_id, "admin")
        
        # If moving to different project, check authorization for target project
        if request.target_project_id and request.target_project_id != task.project_id:
            target_project = await self.project_repository.find_by_id(request.target_project_id)
            if not target_project:
                raise ValueError("Target project not found")
            
            target_member = target_project.get_member(self.current_user_id)
            if not target_member or not target_member.can_create_tasks:
                self._require_owner_or_role(target_project.owner_id, "admin")
            
            # Move to different project
            task.move_to_project(request.target_project_id)
            
            # Clear assignee if they're not a member of target project
            if task.assignee_id:
                assignee_member = target_project.get_member(task.assignee_id)
                if not assignee_member:
                    task.assignee_id = None
        
        # Update position and parent
        if request.new_position is not None:
            task.position = request.new_position
        
        if request.new_parent_id is not None:
            if request.new_parent_id:
                parent_task = await self.task_repository.find_by_id(request.new_parent_id)
                if not parent_task or parent_task.project_id != (request.target_project_id or task.project_id):
                    raise ValueError("Invalid parent task")
            task.parent_task_id = request.new_parent_id
        
        # Save task
        saved_task = await self.task_repository.save(task)
        
        return await self._task_to_response_dto(saved_task)


class GetTaskByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, TaskResponseDTO]):
    """Use case for getting task by ID."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, task_id: int) -> TaskResponseDTO:
        task = await self.task_repository.find_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member:
                self._require_owner_or_role(project.owner_id, "admin")
        
        return await self._task_to_response_dto(task)


class ListTasksUseCase(AuthorizedUseCase, ListUseCase[ListTasksRequestDTO, TaskSummaryResponseDTO]):
    """Use case for listing tasks with filters."""
    
    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository
    
    async def _execute_business_logic(self, request: ListTasksRequestDTO) -> List[TaskSummaryResponseDTO]:
        tasks = await self.task_repository.find_with_filters(
            user_id=self.current_user_id,
            project_id=request.project_id,
            assignee_id=request.assignee_id,
            status=request.status,
            priority=request.priority,
            task_type=request.task_type,
            is_overdue=request.is_overdue,
            has_subtasks=request.has_subtasks,
            parent_task_id=request.parent_task_id,
            tags=request.tags,
            search=request.search,
            due_date_from=request.due_date_from,
            due_date_to=request.due_date_to,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [await self._task_to_summary_dto(task) for task in tasks]


class SearchTasksUseCase(AuthorizedUseCase, SearchUseCase[SearchTasksRequestDTO, TaskSummaryResponseDTO]):
    """Use case for searching tasks."""
    
    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository
    
    async def _execute_business_logic(self, request: SearchTasksRequestDTO) -> List[TaskSummaryResponseDTO]:
        tasks = await self.task_repository.search_tasks(
            user_id=self.current_user_id,
            query=request.query,
            project_id=request.project_id,
            status=request.status,
            priority=request.priority,
            assignee_id=request.assignee_id,
            page=request.page,
            page_size=request.page_size
        )
        
        return [await self._task_to_summary_dto(task) for task in tasks]


class DeleteTaskUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting a task."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, task_id: int) -> bool:
        # Get task
        task = await self.task_repository.find_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member or not member.can_create_tasks:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Check if task has time entries
        stats = await self.task_repository.get_task_stats(task_id)
        if stats and stats.total_hours > 0:
            raise ValueError("Cannot delete task with time entries")
        
        # Delete task and subtasks
        await self.task_repository.delete_with_subtasks(task_id)
        
        return True


class BulkUpdateTasksUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateTasksRequestDTO, dict]):
    """Use case for bulk updating tasks."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: BulkUpdateTasksRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for task_id in request.task_ids:
            try:
                # Get task
                task = await self.task_repository.find_by_id(task_id)
                if not task:
                    results["errors"].append({"id": task_id, "error": "Task not found"})
                    continue
                
                # Check authorization
                project = await self.project_repository.find_by_id(task.project_id)
                if project:
                    member = project.get_member(self.current_user_id)
                    if not member or (not member.can_create_tasks and task.assignee_id != self.current_user_id):
                        results["errors"].append({"id": task_id, "error": "Insufficient permissions"})
                        continue
                
                # Apply updates
                if request.status is not None:
                    task.status = request.status
                if request.priority is not None:
                    task.priority = request.priority
                if request.assignee_id is not None:
                    if request.assignee_id and project:
                        assignee_member = project.get_member(request.assignee_id)
                        if not assignee_member:
                            results["errors"].append({"id": task_id, "error": "Invalid assignee"})
                            continue
                    task.assign_to(request.assignee_id, assigned_by=self.current_user_id)
                if request.tags_to_add:
                    task.add_tags(request.tags_to_add)
                if request.tags_to_remove:
                    task.remove_tags(request.tags_to_remove)
                
                # Save task
                await self.task_repository.save(task)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": task_id, "error": str(e)})
        
        return results


class BulkMoveTasksUseCase(AuthorizedUseCase, BulkUseCase[BulkMoveTasksRequestDTO, dict]):
    """Use case for bulk moving tasks."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_business_logic(self, request: BulkMoveTasksRequestDTO) -> dict:
        results = {"moved": 0, "errors": []}
        
        # Verify target project if moving between projects
        target_project = None
        if request.target_project_id:
            target_project = await self.project_repository.find_by_id(request.target_project_id)
            if not target_project:
                return {"moved": 0, "errors": [{"error": "Target project not found"}]}
            
            target_member = target_project.get_member(self.current_user_id)
            if not target_member or not target_member.can_create_tasks:
                try:
                    self._require_owner_or_role(target_project.owner_id, "admin")
                except Exception as e:
                    return {"moved": 0, "errors": [{"error": str(e)}]}
        
        for task_id in request.task_ids:
            try:
                # Get task
                task = await self.task_repository.find_by_id(task_id)
                if not task:
                    results["errors"].append({"id": task_id, "error": "Task not found"})
                    continue
                
                # Check authorization for source project
                source_project = await self.project_repository.find_by_id(task.project_id)
                if source_project:
                    member = source_project.get_member(self.current_user_id)
                    if not member or not member.can_create_tasks:
                        results["errors"].append({"id": task_id, "error": "Insufficient permissions"})
                        continue
                
                # Move task
                if request.target_project_id and request.target_project_id != task.project_id:
                    task.move_to_project(request.target_project_id)
                    
                    # Clear assignee if not member of target project
                    if task.assignee_id and target_project:
                        assignee_member = target_project.get_member(task.assignee_id)
                        if not assignee_member:
                            task.assignee_id = None
                
                # Update status if provided
                if request.new_status:
                    task.status = request.new_status
                
                # Save task
                await self.task_repository.save(task)
                results["moved"] += 1
                
            except Exception as e:
                results["errors"].append({"id": task_id, "error": str(e)})
        
        return results


class AddTaskCommentUseCase(AuthorizedUseCase, CreateUseCase[TaskCommentRequestDTO, TaskCommentResponseDTO]):
    """Use case for adding a comment to a task."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: TaskCommentRequestDTO) -> TaskCommentResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Add comment
        comment = task.add_comment(
            author_id=self.current_user_id,
            content=request.content,
            is_internal=request.is_internal
        )
        
        # Save task
        await self.task_repository.save(task)
        
        # Get author info
        author = await self.user_repository.find_by_id(self.current_user_id)
        
        return TaskCommentResponseDTO(
            id=comment.id,
            task_id=task.id,
            author_id=comment.author_id,
            author_name=author.full_name if author else "",
            content=comment.content,
            is_internal=comment.is_internal,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )


class AddTaskAttachmentUseCase(AuthorizedUseCase, CreateUseCase[TaskAttachmentRequestDTO, TaskAttachmentResponseDTO]):
    """Use case for adding an attachment to a task."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
    
    async def _execute_command_logic(self, request: TaskAttachmentRequestDTO) -> TaskAttachmentResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(request.task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Add attachment
        attachment = task.add_attachment(
            uploaded_by=self.current_user_id,
            filename=request.filename,
            file_path=request.file_path,
            file_size=request.file_size,
            mime_type=request.mime_type,
            description=request.description
        )
        
        # Save task
        await self.task_repository.save(task)
        
        return TaskAttachmentResponseDTO(
            id=attachment.id,
            task_id=task.id,
            filename=attachment.filename,
            file_path=attachment.file_path,
            file_size=attachment.file_size,
            mime_type=attachment.mime_type,
            description=attachment.description,
            uploaded_by=attachment.uploaded_by,
            uploaded_at=attachment.uploaded_at
        )


class GetTaskAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[int, TaskAnalyticsResponseDTO]):
    """Use case for getting task analytics."""
    
    def __init__(
        self, 
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        task_service: TaskService
    ):
        super().__init__()
        self.task_repository = task_repository
        self.project_repository = project_repository
        self.task_service = task_service
    
    async def _execute_business_logic(self, task_id: int) -> TaskAnalyticsResponseDTO:
        # Get task
        task = await self.task_repository.find_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check authorization
        project = await self.project_repository.find_by_id(task.project_id)
        if project:
            member = project.get_member(self.current_user_id)
            if not member:
                self._require_owner_or_role(project.owner_id, "admin")
        
        # Get analytics
        analytics = await self.task_service.get_task_analytics(task_id)
        
        return TaskAnalyticsResponseDTO(
            task_id=task.id,
            task_title=task.title,
            completion_metrics=analytics.completion_metrics,
            time_metrics=analytics.time_metrics,
            assignment_history=analytics.assignment_history,
            status_transitions=analytics.status_transitions,
            dependency_impact=analytics.dependency_impact,
            performance_indicators=analytics.performance_indicators
        )


    async def _task_to_response_dto(self, task: Task) -> TaskResponseDTO:
        """Convert Task domain model to response DTO."""
        # Get project info
        project = await self.project_repository.find_by_id(task.project_id) if hasattr(self, 'project_repository') else None
        
        # Get assignee info
        assignee = await self.user_repository.find_by_id(task.assignee_id) if task.assignee_id and hasattr(self, 'user_repository') else None
        
        # Get created by info
        created_by = await self.user_repository.find_by_id(task.created_by) if hasattr(self, 'user_repository') else None
        
        # Convert comments
        comments = []
        for comment in task.comments:
            author = await self.user_repository.find_by_id(comment.author_id) if hasattr(self, 'user_repository') else None
            comments.append(TaskCommentResponseDTO(
                id=comment.id,
                task_id=task.id,
                author_id=comment.author_id,
                author_name=author.full_name if author else "",
                content=comment.content,
                is_internal=comment.is_internal,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            ))
        
        # Convert attachments
        attachments = []
        for attachment in task.attachments:
            attachments.append(TaskAttachmentResponseDTO(
                id=attachment.id,
                task_id=task.id,
                filename=attachment.filename,
                file_path=attachment.file_path,
                file_size=attachment.file_size,
                mime_type=attachment.mime_type,
                description=attachment.description,
                uploaded_by=attachment.uploaded_by,
                uploaded_at=attachment.uploaded_at
            ))
        
        # Get subtasks
        subtasks = []
        for subtask in task.subtasks:
            subtasks.append(await self._task_to_summary_dto(subtask))
        
        # Get time stats
        stats = await self.task_repository.get_task_stats(task.id) if hasattr(self, 'task_repository') else None
        time_stats = None
        if stats:
            time_stats = TaskTimeStatsDTO(
                total_hours=stats.total_hours,
                billable_hours=stats.billable_hours,
                estimated_vs_actual=stats.estimated_vs_actual,
                time_efficiency=stats.time_efficiency
            )
        
        return TaskResponseDTO(
            id=task.id,
            project_id=task.project_id,
            project_name=project.name if project else "",
            parent_task_id=task.parent_task_id,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            assignee_id=task.assignee_id,
            assignee_name=assignee.full_name if assignee else None,
            created_by=task.created_by,
            created_by_name=created_by.full_name if created_by else "",
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours,
            due_date=task.due_date,
            completed_at=task.completed_at,
            position=task.position,
            tags=task.tags,
            custom_fields=task.custom_fields,
            comments=comments,
            attachments=attachments,
            subtasks=subtasks,
            time_stats=time_stats,
            is_overdue=task.is_overdue,
            can_be_completed=task.can_be_completed,
            blocked_reason=task.blocked_reason,
            completion_notes=task.completion_notes,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
    
    async def _task_to_summary_dto(self, task: Task) -> TaskSummaryResponseDTO:
        """Convert Task domain model to summary DTO."""
        # Get assignee info
        assignee = await self.user_repository.find_by_id(task.assignee_id) if task.assignee_id and hasattr(self, 'user_repository') else None
        
        return TaskSummaryResponseDTO(
            id=task.id,
            project_id=task.project_id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            task_type=task.task_type,
            assignee_id=task.assignee_id,
            assignee_name=assignee.full_name if assignee else None,
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours,
            due_date=task.due_date,
            is_overdue=task.is_overdue,
            has_subtasks=len(task.subtasks) > 0,
            subtask_count=len(task.subtasks),
            completion_percentage=task.completion_percentage,
            tags=task.tags,
            created_at=task.created_at,
            updated_at=task.updated_at
        )