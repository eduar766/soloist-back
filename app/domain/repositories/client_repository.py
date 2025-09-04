"""
Client repository interface.
Defines the contract for client data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.models.client import Client, ClientStatus, PaymentTerms


class ClientRepository(ABC):
    """
    Repository interface for Client aggregate.
    Defines all operations needed for client data persistence.
    """

    @abstractmethod
    async def save(self, client: Client) -> Client:
        """
        Save a client entity.
        Returns the saved client with updated version and timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, client_id: int) -> Optional[Client]:
        """
        Find a client by its ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def find_by_owner_id(self, owner_id: str) -> List[Client]:
        """
        Find all clients owned by a specific user.
        """
        pass

    @abstractmethod
    async def find_by_name(self, owner_id: str, name: str) -> Optional[Client]:
        """
        Find a client by name within an owner's clients.
        Used to check for duplicate names.
        """
        pass

    @abstractmethod
    async def find_by_email(self, owner_id: str, email: str) -> Optional[Client]:
        """
        Find a client by email within an owner's clients.
        """
        pass

    @abstractmethod
    async def find_by_status(self, owner_id: str, status: ClientStatus) -> List[Client]:
        """
        Find all clients with a specific status for an owner.
        """
        pass

    @abstractmethod
    async def find_by_payment_terms(self, owner_id: str, payment_terms: PaymentTerms) -> List[Client]:
        """
        Find all clients with specific payment terms for an owner.
        """
        pass

    @abstractmethod
    async def search(
        self,
        owner_id: str,
        query: str,
        status: Optional[ClientStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Client]:
        """
        Search clients by query string, optionally filtered by status and tags.
        Searches in name, company, email, and other text fields.
        """
        pass

    @abstractmethod
    async def find_with_outstanding_balance(self, owner_id: str) -> List[Client]:
        """
        Find all clients with outstanding balance greater than zero.
        """
        pass

    @abstractmethod
    async def find_with_active_projects(self, owner_id: str) -> List[Client]:
        """
        Find all clients that have active projects.
        """
        pass

    @abstractmethod
    async def get_client_statistics(self, client_id: int) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a client.
        Includes project count, revenue, hours, etc.
        """
        pass

    @abstractmethod
    async def update_statistics(self, client_id: int, stats: Dict[str, Any]) -> None:
        """
        Update computed statistics for a client.
        Called when related entities (projects, invoices) change.
        """
        pass

    @abstractmethod
    async def delete(self, client_id: int) -> bool:
        """
        Delete a client by ID.
        Returns True if deleted, False if not found.
        Only allowed for clients with no projects or outstanding balance.
        """
        pass

    @abstractmethod
    async def exists(self, client_id: int) -> bool:
        """
        Check if a client exists by ID.
        """
        pass

    @abstractmethod
    async def count_by_owner(self, owner_id: str, status: Optional[ClientStatus] = None) -> int:
        """
        Count clients for an owner, optionally filtered by status.
        """
        pass

    @abstractmethod
    async def find_recently_created(
        self, 
        owner_id: str, 
        days: int = 30, 
        limit: int = 10
    ) -> List[Client]:
        """
        Find recently created clients within the specified number of days.
        """
        pass

    @abstractmethod
    async def find_recently_updated(
        self, 
        owner_id: str, 
        days: int = 7, 
        limit: int = 10
    ) -> List[Client]:
        """
        Find recently updated clients within the specified number of days.
        """
        pass

    @abstractmethod
    async def find_by_tags(self, owner_id: str, tags: List[str]) -> List[Client]:
        """
        Find clients that have any of the specified tags.
        """
        pass

    @abstractmethod
    async def find_overdue_clients(self, owner_id: str) -> List[Client]:
        """
        Find clients with overdue invoices.
        """
        pass

    @abstractmethod
    async def get_revenue_by_client(
        self, 
        owner_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get revenue breakdown by client for a date range.
        Returns list of {client_id, client_name, revenue, invoice_count}.
        """
        pass

    @abstractmethod
    async def archive_inactive_clients(
        self, 
        owner_id: str, 
        days_inactive: int = 365
    ) -> int:
        """
        Archive clients that haven't had activity for specified days.
        Returns number of clients archived.
        """
        pass

    @abstractmethod
    async def bulk_update_payment_terms(
        self, 
        owner_id: str, 
        client_ids: List[int], 
        payment_terms: PaymentTerms
    ) -> int:
        """
        Bulk update payment terms for multiple clients.
        Returns number of clients updated.
        """
        pass

    @abstractmethod
    async def find_duplicate_names(self, owner_id: str) -> List[Dict[str, Any]]:
        """
        Find clients with duplicate names for an owner.
        Returns list of {name, client_ids, count}.
        """
        pass

    @abstractmethod
    async def get_client_activity_summary(
        self, 
        client_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a client in the last N days.
        Includes projects created, tasks completed, time tracked, etc.
        """
        pass