"""
Authentication service for user management.
Handles user authentication, password hashing, and token generation.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from datetime import datetime


class AuthService(ABC):
    """
    Authentication service interface.
    Defines authentication operations for users.
    """

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """
        Hash a password using secure hashing algorithm.
        """
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        """
        pass

    @abstractmethod
    def generate_access_token(self, user_id: str) -> str:
        """
        Generate an access token for the user.
        """
        pass

    @abstractmethod
    def generate_refresh_token(self, user_id: str) -> str:
        """
        Generate a refresh token for the user.
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a token and return the user ID if valid.
        """
        pass

    @abstractmethod
    def generate_password_reset_token(self, user_id: str) -> str:
        """
        Generate a password reset token.
        """
        pass

    @abstractmethod
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token and return user ID if valid.
        """
        pass