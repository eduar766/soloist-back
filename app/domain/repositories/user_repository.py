"""
User repository interface.
Defines the contract for user data persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.models.user import User, UserRole, UserStatus


class UserRepositoryInterface(ABC):
    """
    Repository interface for User aggregate.
    Defines all operations needed for user data persistence.
    """

    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Save a user entity.
        Returns the saved user with updated version and timestamps.
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find a user by their ID.
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by their email address.
        """
        pass

    @abstractmethod
    async def find_all(self, 
                      skip: int = 0, 
                      limit: int = 100,
                      status: Optional[UserStatus] = None,
                      role: Optional[UserRole] = None) -> List[User]:
        """
        Find all users with optional filtering.
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Update an existing user.
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user by ID.
        Returns True if successful, False if user not found.
        """
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if a user exists with the given email.
        """
        pass

    @abstractmethod
    async def count(self, status: Optional[UserStatus] = None) -> int:
        """
        Count users, optionally filtering by status.
        """
        pass

    @abstractmethod
    async def search(self,
                    query: str,
                    skip: int = 0,
                    limit: int = 100) -> List[User]:
        """
        Search users by name, email, or company.
        """
        pass