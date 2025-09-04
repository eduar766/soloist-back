"""
JWT token handler for Supabase authentication.
Validates JWT tokens and extracts user information.
"""

import jwt
from typing import Optional, Dict, Any
from datetime import datetime
from jose import JWTError, jwt as jose_jwt

from app.config import get_settings
from app.domain.models.base import ValidationError


class JWTHandler:
    """Handles JWT token validation and user extraction."""
    
    def __init__(self):
        self.settings = get_settings()
        self.jwt_secret = self.settings.supabase_jwt_secret
        self.jwt_algorithm = "HS256"
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a Supabase JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing token payload
            
        Raises:
            ValidationError: If token is invalid or expired
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode and verify the token
            payload = jose_jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": True}
            )
            
            # Validate required claims
            if 'sub' not in payload:
                raise ValidationError("Token missing user ID (sub claim)")
            
            if 'exp' not in payload:
                raise ValidationError("Token missing expiration (exp claim)")
            
            # Check if token is expired
            exp_timestamp = payload['exp']
            if datetime.utcnow().timestamp() > exp_timestamp:
                raise ValidationError("Token has expired")
            
            return payload
            
        except JWTError as e:
            raise ValidationError(f"Invalid JWT token: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Token validation error: {str(e)}")
    
    def get_user_id(self, token: str) -> str:
        """
        Extract user ID from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID string
            
        Raises:
            ValidationError: If token is invalid
        """
        payload = self.verify_token(token)
        return payload['sub']
    
    def get_user_email(self, token: str) -> Optional[str]:
        """
        Extract user email from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User email if present in token, None otherwise
        """
        try:
            payload = self.verify_token(token)
            return payload.get('email')
        except ValidationError:
            return None
    
    def get_user_role(self, token: str) -> Optional[str]:
        """
        Extract user role from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User role if present in token, None otherwise
        """
        try:
            payload = self.verify_token(token)
            return payload.get('role')
        except ValidationError:
            return None
    
    def is_token_valid(self, token: str) -> bool:
        """
        Check if token is valid without raising exceptions.
        
        Args:
            token: JWT token string
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.verify_token(token)
            return True
        except ValidationError:
            return False
    
    def get_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get full token payload safely.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            return self.verify_token(token)
        except ValidationError:
            return None