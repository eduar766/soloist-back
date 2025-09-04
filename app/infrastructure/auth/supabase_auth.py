"""
Supabase authentication service.
Handles user authentication operations with Supabase.
"""

from typing import Optional, Dict, Any
from supabase import create_client, Client
import requests

from app.config import get_settings
from app.domain.models.base import ValidationError, BusinessRuleViolation


class SupabaseAuthService:
    """Service for Supabase authentication operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase: Client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_anon_key
        )
    
    def sign_up(self, email: str, password: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Sign up a new user.
        
        Args:
            email: User email
            password: User password
            metadata: Optional user metadata
            
        Returns:
            Dict containing user data and session
            
        Raises:
            ValidationError: If sign up fails
        """
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": metadata or {}
                }
            })
            
            if response.user is None:
                raise ValidationError("Failed to create user account")
            
            return {
                "user": response.user.model_dump(),
                "session": response.session.model_dump() if response.session else None
            }
            
        except Exception as e:
            raise ValidationError(f"Sign up failed: {str(e)}")
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in a user.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict containing user data and session
            
        Raises:
            ValidationError: If sign in fails
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user is None or response.session is None:
                raise ValidationError("Invalid email or password")
            
            return {
                "user": response.user.model_dump(),
                "session": response.session.model_dump(),
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
            
        except Exception as e:
            raise ValidationError(f"Sign in failed: {str(e)}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Dict containing new session data
            
        Raises:
            ValidationError: If refresh fails
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if response.session is None:
                raise ValidationError("Invalid refresh token")
            
            return {
                "session": response.session.model_dump(),
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
            
        except Exception as e:
            raise ValidationError(f"Token refresh failed: {str(e)}")
    
    def sign_out(self, access_token: str) -> bool:
        """
        Sign out a user.
        
        Args:
            access_token: Access token to invalidate
            
        Returns:
            True if successful
        """
        try:
            # Set the session for the current client
            self.supabase.auth.set_session(access_token, "")
            self.supabase.auth.sign_out()
            return True
        except Exception:
            # Even if sign out fails, we consider it successful
            # as the token will expire anyway
            return True
    
    def get_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from access token.
        
        Args:
            access_token: Access token
            
        Returns:
            User data dict or None if invalid
        """
        try:
            # Set the session and get user
            self.supabase.auth.set_session(access_token, "")
            user = self.supabase.auth.get_user()
            
            if user.user:
                return user.user.model_dump()
            
            return None
            
        except Exception:
            return None
    
    def reset_password(self, email: str) -> bool:
        """
        Send password reset email.
        
        Args:
            email: User email
            
        Returns:
            True if email sent successfully
        """
        try:
            response = self.supabase.auth.reset_password_email(email)
            return True
        except Exception:
            # Don't reveal if email exists or not
            return True
    
    def update_password(self, access_token: str, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            access_token: Valid access token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            ValidationError: If update fails
        """
        try:
            self.supabase.auth.set_session(access_token, "")
            response = self.supabase.auth.update_user({
                "password": new_password
            })
            
            return response.user is not None
            
        except Exception as e:
            raise ValidationError(f"Password update failed: {str(e)}")
    
    def update_user_metadata(self, access_token: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user metadata.
        
        Args:
            access_token: Valid access token
            metadata: Metadata to update
            
        Returns:
            Updated user data
            
        Raises:
            ValidationError: If update fails
        """
        try:
            self.supabase.auth.set_session(access_token, "")
            response = self.supabase.auth.update_user({
                "data": metadata
            })
            
            if response.user is None:
                raise ValidationError("Failed to update user metadata")
            
            return response.user.model_dump()
            
        except Exception as e:
            raise ValidationError(f"Metadata update failed: {str(e)}")
    
    def verify_otp(self, email: str, token: str, type: str = "signup") -> Dict[str, Any]:
        """
        Verify OTP token.
        
        Args:
            email: User email
            token: OTP token
            type: Token type (signup, recovery, etc.)
            
        Returns:
            Session data
            
        Raises:
            ValidationError: If verification fails
        """
        try:
            response = self.supabase.auth.verify_otp({
                "email": email,
                "token": token,
                "type": type
            })
            
            if response.session is None:
                raise ValidationError("Invalid or expired OTP token")
            
            return {
                "user": response.user.model_dump() if response.user else None,
                "session": response.session.model_dump(),
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
            
        except Exception as e:
            raise ValidationError(f"OTP verification failed: {str(e)}")