"""
Task repository interface.
Defines the contract for task data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.domain.models.task import Task, TaskStatus, TaskPriority, TaskType


class TaskRepository(ABC):
    """
    Repository interface for Task entity.
    Defines all operations needed for task data persistence.
    """

    @abstractmethod
    async def save(self, task: Task) -> Task:
        """
        Save a task entity.
        Returns the saved task with updated timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, task_id: int) -> Optional[Task]:
        """
        Find a task by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def find_by_project_id(self, project_id: int) -> List[Task]:
        """
        Find all tasks for a specific project.
        """
        pass

    @abstractmethod
    async def find_by_assigned_user(self, user_id: str) -> List[Task]:
        """
        Find all tasks assigned to a specific user.
        """
        pass

    @abstractmethod
    async def find_by_created_by(self, user_id: str) -> List[Task]:
        """
        Find all tasks created by a specific user.
        """
        pass

    @abstractmethod
    async def find_by_status(self, project_id: int, status: TaskStatus) -> List[Task]:
        """
        Find all tasks with a specific status in a project.
        """
        pass

    @abstractmethod
    async def find_by_priority(self, project_id: int, priority: TaskPriority) -> List[Task]:
        """
        Find all tasks with a specific priority in a project.
        """
        pass

    @abstractmethod
    async def find_by_type(self, project_id: int, task_type: TaskType) -> List[Task]:
        """
        Find all tasks with a specific type in a project.
        """
        pass

    @abstractmethod
    async def find_overdue_tasks(self, user_id: str) -> List[Task]:
        """
        Find all overdue tasks assigned to a user.
        """
        pass

    @abstractmethod
    async def find_due_soon(self, user_id: str, days: int = 3) -> List[Task]:
        """
        Find tasks due within the specified number of days.
        """
        pass

    @abstractmethod
    async def find_active_tasks(self, user_id: str) -> List[Task]:
        """
        Find all active (in progress) tasks for a user.
        """
        pass

    @abstractmethod
    async def find_unassigned_tasks(self, project_id: int) -> List[Task]:
        """
        Find all unassigned tasks in a project.
        """
        pass

    @abstractmethod
    async def find_by_parent_task(self, parent_task_id: int) -> List[Task]:
        """
        Find all subtasks of a parent task.
        """
        pass

    @abstractmethod
    async def find_root_tasks(self, project_id: int) -> List[Task]:
        """
        Find all root tasks (tasks without parent) in a project.
        """
        pass

    @abstractmethod
    async def search(
        self,
        project_id: int,
        query: str,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Task]:
        """
        Search tasks by query string, optionally filtered.
        Searches in title, description, and comments.
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Task]:
        """
        Find tasks within a date range (by due date).
        """
        pass

    @abstractmethod
    async def find_by_tags(self, project_id: int, tags: List[str]) -> List[Task]:
        """
        Find tasks that have any of the specified tags.
        """
        pass

    @abstractmethod
    async def find_watched_by_user(self, user_id: str) -> List[Task]:
        """
        Find all tasks watched by a specific user.
        """
        pass

    @abstractmethod
    async def get_kanban_board(self, project_id: int) -> Dict[str, List[Task]]:
        """
        Get tasks organized by status for Kanban board display.
        Returns dict with status as key and ordered list of tasks as value.
        """
        pass

    @abstractmethod
    async def update_board_positions(
        self,
        project_id: int,
        status: TaskStatus,
        task_positions: List[Dict[str, Any]]
    ) -> None:
        """
        Update task positions on Kanban board for a specific status.
        task_positions: List of {task_id, position}
        """
        pass

    @abstractmethod
    async def move_task_to_status(
        self,
        task_id: int,
        new_status: TaskStatus,
        position: int
    ) -> None:
        """
        Move a task to a new status and position on the board.
        """
        pass

    @abstractmethod
    async def get_task_statistics(self, project_id: int) -> Dict[str, Any]:
        """
        Get task statistics for a project.
        Includes count by status, priority, assignee, etc.
        """
        pass

    @abstractmethod
    async def get_user_task_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get task statistics for a user across all projects.
        """
        pass

    @abstractmethod
    async def get_time_tracking_summary(
        self,
        task_id: int
    ) -> Dict[str, Any]:
        """
        Get time tracking summary for a task.
        Includes estimated vs actual hours, time entries, etc.
        """
        pass

    @abstractmethod
    async def add_time_to_task(self, task_id: int, hours: float) -> None:
        """
        Add time to a task's actual hours.
        """
        pass

    @abstractmethod
    async def set_task_time(self, task_id: int, hours: float) -> None:
        """
        Set the total actual hours for a task.
        """
        pass

    @abstractmethod
    async def delete(self, task_id: int) -> bool:
        """
        Delete a task by ID.
        Returns True if deleted, False if not found.
        Also deletes all subtasks.
        """
        pass

    @abstractmethod
    async def delete_subtasks(self, parent_task_id: int) -> int:
        """
        Delete all subtasks of a parent task.
        Returns number of subtasks deleted.
        """
        pass

    @abstractmethod
    async def exists(self, task_id: int) -> bool:
        """
        Check if a task exists by ID.
        """
        pass

    @abstractmethod
    async def count_by_project(
        self,
        project_id: int,
        status: Optional[TaskStatus] = None
    ) -> int:
        """
        Count tasks in a project, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def count_by_assignee(
        self,
        user_id: str,
        status: Optional[TaskStatus] = None
    ) -> int:
        """
        Count tasks assigned to a user, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def find_recently_created(
        self,
        project_id: int,
        days: int = 7,
        limit: int = 10
    ) -> List[Task]:
        """
        Find recently created tasks in a project.
        """
        pass

    @abstractmethod
    async def find_recently_updated(
        self,
        project_id: int,
        days: int = 7,
        limit: int = 10
    ) -> List[Task]:
        """
        Find recently updated tasks in a project.
        """
        pass

    @abstractmethod
    async def find_recently_completed(
        self,
        project_id: int,
        days: int = 7,
        limit: int = 10
    ) -> List[Task]:
        """
        Find recently completed tasks in a project.
        """
        pass

    @abstractmethod
    async def find_stale_tasks(
        self,
        project_id: int,
        days_inactive: int = 30
    ) -> List[Task]:
        """
        Find tasks that haven't been updated for specified days.
        """
        pass

    @abstractmethod
    async def bulk_update_status(
        self,
        task_ids: List[int],
        new_status: TaskStatus,
        updated_by: str
    ) -> int:
        """
        Bulk update status for multiple tasks.
        Returns number of tasks updated.
        """
        pass

    @abstractmethod
    async def bulk_assign_tasks(
        self,
        task_ids: List[int],
        assignee_id: str,
        assigned_by: str
    ) -> int:
        """
        Bulk assign multiple tasks to a user.
        Returns number of tasks assigned.
        """
        pass

    @abstractmethod
    async def bulk_update_priority(
        self,
        task_ids: List[int],
        priority: TaskPriority
    ) -> int:
        """
        Bulk update priority for multiple tasks.
        Returns number of tasks updated.
        """
        pass

    @abstractmethod
    async def get_completion_rate(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> float:
        """
        Get task completion rate for a project in a date range.
        Returns percentage (0-100).
        """
        pass

    @abstractmethod
    async def get_velocity_metrics(
        self,
        project_id: int,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Get velocity metrics for a project over specified weeks.
        Includes tasks completed per week, average completion time, etc.
        """
        pass

    @abstractmethod
    async def find_blocked_tasks(self, project_id: int) -> List[Task]:
        """
        Find all blocked tasks in a project.
        """
        pass

    @abstractmethod
    async def archive_completed_tasks(
        self,
        project_id: int,
        days_completed: int = 90
    ) -> int:
        """
        Archive tasks that have been completed for specified days.
        Returns number of tasks archived.
        """
        pass

    @abstractmethod
    async def get_burndown_data(
        self,
        project_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get burndown chart data for a project.
        Returns list of {date, remaining_tasks, completed_tasks}.
        """
        pass