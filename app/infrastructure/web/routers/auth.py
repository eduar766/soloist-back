"""
Authentication router for user authentication endpoints.
Handles user registration, login, token refresh, and profile management.
"""

from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.infrastructure.auth import (
    SupabaseAuthService, 
    get_current_user_id,
    get_current_user_payload
)
from app.infrastructure.auth.dependencies import get_auth_service
from app.domain.models.base import ValidationError


router = APIRouter()


# Request/Response models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    company: str = Field(None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class UpdatePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=100)


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    token: str = Field(..., min_length=6, max_length=6)
    type: str = Field(default="signup")


class AuthResponse(BaseModel):
    user: Dict[str, Any]
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Password with at least 8 characters
    - **full_name**: User's full name
    - **company**: Optional company name
    """
    try:
        metadata = {
            "full_name": request.full_name,
            "company": request.company
        }
        
        result = auth_service.sign_up(
            email=request.email,
            password=request.password,
            metadata=metadata
        )
        
        return AuthResponse(
            user=result["user"],
            access_token=result.get("session", {}).get("access_token", ""),
            refresh_token=result.get("session", {}).get("refresh_token", "")
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Authenticate user and return access tokens.
    
    - **email**: User email address
    - **password**: User password
    """
    try:
        result = auth_service.sign_in(
            email=request.email,
            password=request.password
        )
        
        return AuthResponse(
            user=result["user"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"]
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=Dict[str, str])
async def refresh_token(
    request: RefreshRequest,
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    try:
        result = auth_service.refresh_token(request.refresh_token)
        
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "bearer"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/profile", response_model=Dict[str, Any])
async def get_profile(
    user_payload: Annotated[Dict[str, Any], Depends(get_current_user_payload)]
):
    """
    Get current user profile information.
    
    Requires authentication.
    """
    return {
        "user_id": user_payload.get("sub"),
        "email": user_payload.get("email"),
        "role": user_payload.get("role"),
        "user_metadata": user_payload.get("user_metadata", {}),
        "app_metadata": user_payload.get("app_metadata", {})
    }


@router.post("/logout")
async def logout(
    user_id: Annotated[str, Depends(get_current_user_id)],
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Sign out current user.
    
    Requires authentication.
    """
    # Note: In a real implementation, you might want to get the access token
    # and invalidate it properly. For now, we'll just return success.
    return {"message": "Successfully logged out"}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetRequest,
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Send password reset email.
    
    - **email**: Email address to send reset link
    """
    auth_service.reset_password(request.email)
    
    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a reset link has been sent"}


@router.post("/update-password")
async def update_password(
    request: UpdatePasswordRequest,
    user_payload: Annotated[Dict[str, Any], Depends(get_current_user_payload)],
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Update user password.
    
    Requires authentication.
    """
    try:
        # Get access token from payload (we need it for Supabase API)
        # In a real implementation, you'd extract this from the request headers
        access_token = user_payload.get("access_token", "")
        
        success = auth_service.update_password(access_token, request.new_password)
        
        if success:
            return {"message": "Password updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update password"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    request: OTPVerificationRequest,
    auth_service: Annotated[SupabaseAuthService, Depends(get_auth_service)]
):
    """
    Verify OTP token for email confirmation or password reset.
    
    - **email**: User email address
    - **token**: 6-digit OTP token
    - **type**: Token type (signup, recovery, etc.)
    """
    try:
        result = auth_service.verify_otp(
            email=request.email,
            token=request.token,
            type=request.type
        )
        
        return AuthResponse(
            user=result["user"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"]
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )