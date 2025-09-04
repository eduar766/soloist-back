"""Time Entry repository interface.
Defines the contract for time entry data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.domain.models.time_entry import TimeEntry, TimeEntryStatus, TimeEntryType


class TimeEntryRepository(ABC):
    """
    Repository interface for TimeEntry entity.
    Defines all operations needed for time entry data persistence.
    """

    @abstractmethod
    async def save(self, time_entry: TimeEntry) -> TimeEntry:
        """
        Save a time entry entity.
        Returns the saved time entry with updated timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, entry_id: int) -> Optional[TimeEntry]:
        """
        Find a time entry by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> List[TimeEntry]:
        """
        Find all time entries for a specific user.
        """
        pass

    @abstractmethod
    async def find_by_project_id(self, project_id: int) -> List[TimeEntry]:
        """
        Find all time entries for a specific project.
        """
        pass

    @abstractmethod
    async def find_by_task_id(self, task_id: int) -> List[TimeEntry]:
        """
        Find all time entries for a specific task.
        """
        pass

    @abstractmethod
    async def find_by_user_and_project(
        self, 
        user_id: str, 
        project_id: int
    ) -> List[TimeEntry]:
        """
        Find all time entries for a user in a specific project.
        """
        pass

    @abstractmethod
    async def find_by_status(self, user_id: str, status: TimeEntryStatus) -> List[TimeEntry]:
        """
        Find all time entries with a specific status for a user.
        """
        pass

    @abstractmethod
    async def find_running_timers(self, user_id: str) -> List[TimeEntry]:
        """
        Find all running timers for a user.
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None
    ) -> List[TimeEntry]:
        """
        Find time entries within a date range for a user.
        Optionally filter by project.
        """
        pass

    @abstractmethod
    async def find_billable_entries(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[TimeEntry]:
        """
        Find all billable time entries for a project.
        Optionally filter by date range.
        """
        pass

    @abstractmethod
    async def find_unbilled_entries(
        self,
        project_id: int,
        user_id: Optional[str] = None
    ) -> List[TimeEntry]:
        """
        Find all billable but not yet invoiced time entries.
        Optionally filter by user.
        """
        pass

    @abstractmethod
    async def find_entries_for_invoice(
        self,
        project_id: int,
        start_date: date,
        end_date: date,
        user_ids: Optional[List[str]] = None
    ) -> List[TimeEntry]:
        """
        Find time entries that should be included in an invoice.
        Filters for approved, billable, uninvoiced entries.
        """
        pass

    @abstractmethod
    async def find_pending_approval(
        self,
        project_id: int,
        user_id: Optional[str] = None
    ) -> List[TimeEntry]:
        """
        Find time entries pending approval.
        """
        pass

    @abstractmethod
    async def find_by_type(self, user_id: str, entry_type: TimeEntryType) -> List[TimeEntry]:
        """
        Find all time entries of a specific type for a user.
        """
        pass

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        project_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[TimeEntryStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TimeEntry]:
        """
        Search time entries by description and other text fields.
        """
        pass

    @abstractmethod
    async def get_time_summary(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get time tracking summary for a user in a date range.
        Includes total hours, billable hours, by project, etc.
        """
        pass

    @abstractmethod
    async def get_project_time_summary(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get time tracking summary for a project.
        Includes total hours by user, task, billable status, etc.
        """
        pass

    @abstractmethod
    async def get_daily_hours(
        self,
        user_id: str,
        date: date
    ) -> Dict[str, Any]:
        """
        Get total hours worked by a user on a specific date.
        Includes breakdown by project and billable status.
        """
        pass

    @abstractmethod
    async def get_weekly_hours(
        self,
        user_id: str,
        start_date: date
    ) -> Dict[str, Any]:
        """
        Get weekly hours summary starting from the given date.
        Returns 7 days of data.
        """
        pass

    @abstractmethod
    async def mark_as_invoiced(
        self,
        entry_ids: List[int],
        invoice_id: int
    ) -> int:
        """
        Mark multiple time entries as invoiced.
        Returns number of entries updated.
        """
        pass

    @abstractmethod
    async def bulk_approve_entries(
        self,
        entry_ids: List[int],
        approved_by: str
    ) -> int:
        """
        Bulk approve multiple time entries.
        Returns number of entries approved.
        """
        pass

    @abstractmethod
    async def bulk_reject_entries(
        self,
        entry_ids: List[int],
        rejected_by: str,
        reason: str
    ) -> int:
        """
        Bulk reject multiple time entries.
        Returns number of entries rejected.
        """
        pass

    @abstractmethod
    async def stop_all_running_timers(self, user_id: str) -> List[int]:
        """
        Stop all running timers for a user.
        Returns list of stopped entry IDs.
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: int) -> bool:
        """
        Delete a time entry by ID.
        Returns True if deleted, False if not found.
        Only allowed for non-invoiced entries.
        """
        pass

    @abstractmethod
    async def exists(self, entry_id: int) -> bool:
        """
        Check if a time entry exists by ID.
        """
        pass

    @abstractmethod
    async def count_by_user(
        self,
        user_id: str,
        status: Optional[TimeEntryStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """
        Count time entries for a user, optionally filtered.
        """
        pass

    @abstractmethod
    async def count_by_project(
        self,
        project_id: int,
        status: Optional[TimeEntryStatus] = None
    ) -> int:
        """
        Count time entries for a project, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def get_longest_entries(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[TimeEntry]:
        """
        Get the longest time entries for a user.
        """
        pass

    @abstractmethod
    async def find_overlapping_entries(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[TimeEntry]:
        """
        Find time entries that overlap with the given time range.
        Used to detect conflicts.
        """
        pass

    @abstractmethod
    async def get_time_distribution(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get time distribution analysis for a user.
        Includes hours by project, task type, day of week, etc.
        """
        pass

    @abstractmethod
    async def find_entries_without_description(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[TimeEntry]:
        """
        Find time entries that lack descriptions.
        Used for data quality checks.
        """
        pass

    @abstractmethod
    async def get_productivity_metrics(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get productivity metrics for a user.
        Includes average session length, most productive hours, etc.
        """
        pass

    @abstractmethod
    async def archive_old_entries(
        self,
        user_id: str,
        older_than_days: int = 365
    ) -> int:
        """
        Archive time entries older than specified days.
        Returns number of entries archived.
        """
        pass

    @abstractmethod
    async def get_billable_hours_report(
        self,
        project_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get billable hours report for a project.
        Groups by user and provides totals.
        """
        pass

    @abstractmethod
    async def find_suspicious_entries(
        self,
        project_id: int,
        threshold_hours: float = 12.0
    ) -> List[TimeEntry]:
        """
        Find potentially suspicious time entries.
        E.g., entries longer than threshold or with unusual patterns.
        """
        pass

    @abstractmethod
    async def get_utilization_rate(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        target_hours_per_day: float = 8.0
    ) -> Dict[str, Any]:
        """
        Calculate utilization rate for a user.
        Compares actual hours vs target hours.
        """
        pass