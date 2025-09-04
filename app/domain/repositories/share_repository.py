"""
Share repository interface.
Defines the contract for share data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.models.share import Share, ShareStatus, ShareType


class ShareRepository(ABC):
    """
    Repository interface for Share aggregate.
    Defines all operations needed for share data persistence.
    """

    @abstractmethod
    async def save(self, share: Share) -> Share:
        """
        Save a share entity.
        Returns the saved share with updated version and timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, share_id: int) -> Optional[Share]:
        """
        Find a share by its ID.
        """
        pass

    @abstractmethod
    async def find_by_token(self, token: str) -> Optional[Share]:
        """
        Find a share by its access token.
        """
        pass

    @abstractmethod
    async def find_all(self, 
                      skip: int = 0, 
                      limit: int = 100,
                      owner_id: Optional[str] = None,
                      resource_type: Optional[str] = None,
                      status: Optional[ShareStatus] = None) -> List[Share]:
        """
        Find all shares with optional filtering.
        """
        pass

    @abstractmethod
    async def find_by_owner(self, owner_id: str, 
                           skip: int = 0, 
                           limit: int = 100) -> List[Share]:
        """
        Find all shares created by a specific owner.
        """
        pass

    @abstractmethod
    async def find_by_resource(self, resource_type: str, 
                             resource_id: int,
                             status: Optional[ShareStatus] = None) -> List[Share]:
        """
        Find all shares for a specific resource.
        """
        pass

    @abstractmethod
    async def update(self, share: Share) -> Share:
        """
        Update an existing share.
        """
        pass

    @abstractmethod
    async def delete(self, share_id: int) -> bool:
        """
        Delete a share by ID.
        Returns True if successful, False if share not found.
        """
        pass

    @abstractmethod
    async def exists_by_token(self, token: str) -> bool:
        """
        Check if a share exists with the given token.
        """
        pass

    @abstractmethod
    async def count(self, owner_id: Optional[str] = None) -> int:
        """
        Count shares, optionally filtering by owner.
        """
        pass