"""
Project repository interface.
Defines the contract for project data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.domain.models.project import Project, ProjectStatus, ProjectType, ProjectRole


class ProjectRepository(ABC):
    """
    Repository interface for Project aggregate.
    Defines all operations needed for project data persistence.
    """

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """
        Save a project entity.
        Returns the saved project with updated version and timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, project_id: int) -> Optional[Project]:
        """
        Find a project by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def find_by_owner_id(self, owner_id: str) -> List[Project]:
        """
        Find all projects owned by a specific user.
        """
        pass

    @abstractmethod
    async def find_by_client_id(self, client_id: int) -> List[Project]:
        """
        Find all projects for a specific client.
        """
        pass

    @abstractmethod
    async def find_by_member(self, user_id: str) -> List[Project]:
        """
        Find all projects where the user is a member (any role).
        """
        pass

    @abstractmethod
    async def find_by_member_role(self, user_id: str, role: ProjectRole) -> List[Project]:
        """
        Find all projects where the user has a specific role.
        """
        pass

    @abstractmethod
    async def find_by_status(self, owner_id: str, status: ProjectStatus) -> List[Project]:
        """
        Find all projects with a specific status for an owner.
        """
        pass

    @abstractmethod
    async def find_by_type(self, owner_id: str, project_type: ProjectType) -> List[Project]:
        """
        Find all projects with a specific type for an owner.
        """
        pass

    @abstractmethod
    async def find_active_projects(self, user_id: str) -> List[Project]:
        """
        Find all active projects where the user is a member.
        """
        pass

    @abstractmethod
    async def find_overdue_projects(self, user_id: str) -> List[Project]:
        """
        Find all projects that are past their deadline.
        """
        pass

    @abstractmethod
    async def find_over_budget(self, owner_id: str) -> List[Project]:
        """
        Find all projects that are over budget.
        """
        pass

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        status: Optional[ProjectStatus] = None,
        client_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Search projects by query string, optionally filtered.
        Searches in name, description, and other text fields.
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        owner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Project]:
        """
        Find projects within a date range (by start/end dates).
        """
        pass

    @abstractmethod
    async def find_by_deadline_range(
        self,
        owner_id: str,
        from_date: date,
        to_date: date
    ) -> List[Project]:
        """
        Find projects with deadlines within a date range.
        """
        pass

    @abstractmethod
    async def find_by_tags(self, owner_id: str, tags: List[str]) -> List[Project]:
        """
        Find projects that have any of the specified tags.
        """
        pass

    @abstractmethod
    async def get_project_statistics(self, project_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a project.
        Includes task count, time tracked, budget usage, etc.
        """
        pass

    @abstractmethod
    async def update_statistics(self, project_id: int, stats: Dict[str, Any]) -> None:
        """
        Update computed statistics for a project.
        Called when related entities (tasks, time entries) change.
        """
        pass

    @abstractmethod
    async def get_team_members(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all team members for a project with their details.
        """
        pass

    @abstractmethod
    async def add_team_member(
        self,
        project_id: int,
        user_id: str,
        role: ProjectRole,
        hourly_rate: Optional[float] = None,
        added_by: str = None
    ) -> None:
        """
        Add a team member to a project.
        """
        pass

    @abstractmethod
    async def remove_team_member(self, project_id: int, user_id: str) -> None:
        """
        Remove a team member from a project.
        """
        pass

    @abstractmethod
    async def update_member_role(
        self,
        project_id: int,
        user_id: str,
        new_role: ProjectRole
    ) -> None:
        """
        Update a team member's role in a project.
        """
        pass

    @abstractmethod
    async def user_has_access(self, project_id: int, user_id: str) -> bool:
        """
        Check if a user has access to a project.
        """
        pass

    @abstractmethod
    async def user_has_role(
        self,
        project_id: int,
        user_id: str,
        required_role: ProjectRole
    ) -> bool:
        """
        Check if a user has a specific role or higher in a project.
        """
        pass

    @abstractmethod
    async def delete(self, project_id: int) -> bool:
        """
        Delete a project by ID.
        Returns True if deleted, False if not found.
        Only allowed for projects with no time entries or invoices.
        """
        pass

    @abstractmethod
    async def exists(self, project_id: int) -> bool:
        """
        Check if a project exists by ID.
        """
        pass

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None
    ) -> int:
        """
        Count projects for an owner, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def count_by_client(self, client_id: int) -> int:
        """
        Count projects for a specific client.
        """
        pass

    @abstractmethod
    async def find_recently_created(
        self,
        owner_id: str,
        days: int = 30,
        limit: int = 10
    ) -> List[Project]:
        """
        Find recently created projects within the specified number of days.
        """
        pass

    @abstractmethod
    async def find_recently_updated(
        self,
        owner_id: str,
        days: int = 7,
        limit: int = 10
    ) -> List[Project]:
        """
        Find recently updated projects within the specified number of days.
        """
        pass

    @abstractmethod
    async def find_completing_soon(
        self,
        owner_id: str,
        days: int = 7
    ) -> List[Project]:
        """
        Find projects with deadlines in the next N days.
        """
        pass

    @abstractmethod
    async def get_revenue_by_project(
        self,
        owner_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get revenue breakdown by project for a date range.
        Returns list of {project_id, project_name, revenue, hours}.
        """
        pass

    @abstractmethod
    async def get_time_tracking_summary(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get time tracking summary for a project.
        Includes total hours, billable hours, by team member, etc.
        """
        pass

    @abstractmethod
    async def get_budget_usage_report(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed budget usage report for a project.
        Includes spent vs budget, breakdown by category, forecasting.
        """
        pass

    @abstractmethod
    async def archive_completed_projects(
        self,
        owner_id: str,
        days_completed: int = 90
    ) -> int:
        """
        Archive projects that have been completed for specified days.
        Returns number of projects archived.
        """
        pass

    @abstractmethod
    async def bulk_update_status(
        self,
        owner_id: str,
        project_ids: List[int],
        new_status: ProjectStatus
    ) -> int:
        """
        Bulk update status for multiple projects.
        Returns number of projects updated.
        """
        pass

    @abstractmethod
    async def find_similar_projects(
        self,
        project_id: int,
        limit: int = 5
    ) -> List[Project]:
        """
        Find similar projects based on client, type, and other factors.
        Used for analytics and recommendations.
        """
        pass

    @abstractmethod
    async def get_project_health_score(self, project_id: int) -> Dict[str, Any]:
        """
        Calculate project health score based on various metrics.
        Includes budget, timeline, team activity, etc.
        """
        pass

    @abstractmethod
    async def find_projects_needing_attention(
        self,
        owner_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find projects that need attention (overdue, over budget, inactive).
        Returns list with project info and reason for attention.
        """
        pass