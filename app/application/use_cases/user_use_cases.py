"""
User use cases for the application layer.
Implements business logic for user operations.
"""

from typing import List, Optional
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, GetByIdUseCase, ListUseCase, 
    SearchUseCase, AuthorizedUseCase, UseCaseResult
)
from app.application.dto.user_dto import (
    CreateUserRequestDTO, UpdateUserRequestDTO, UpdateUserPreferencesRequestDTO,
    UpdateBillingInfoRequestDTO, ChangePasswordRequestDTO, ListUsersRequestDTO,
    UserResponseDTO, UserPreferencesResponseDTO, UserStatsResponseDTO,
    LoginRequestDTO, RegisterRequestDTO, RefreshTokenRequestDTO,
    ForgotPasswordRequestDTO, ResetPasswordRequestDTO, VerifyEmailRequestDTO,
    AuthUserResponseDTO, UserActivityResponseDTO, UserProductivityResponseDTO,
    UserTimeTrackingStatsDTO
)
from app.domain.models.user import User
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository as UserRepository
from app.domain.services.auth_service import AuthService
from app.domain.services.email_service import EmailService


class CreateUserUseCase(CreateUseCase[CreateUserRequestDTO, UserResponseDTO]):
    """Use case for creating a new user."""
    
    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
    
    async def _execute_command_logic(self, request: CreateUserRequestDTO) -> UserResponseDTO:
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(request.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = await self.auth_service.hash_password(request.password)
        
        # Create user
        user = User.create(
            email=str(request.email),
            full_name=request.full_name,
            password_hash=hashed_password,
            phone=request.phone,
            company=request.company,
            position=request.position
        )
        
        # Save user
        saved_user = await self.user_repository.save(user)
        
        # Convert to response DTO
        return UserResponseDTO(
            user_id=saved_user.user_id,
            email=saved_user.email,
            full_name=saved_user.full_name,
            phone=saved_user.phone,
            company=saved_user.company,
            position=saved_user.position,
            role=saved_user.role,
            status=saved_user.status,
            email_verified=saved_user.email_verified,
            email_verified_at=saved_user.email_verified_at,
            last_sign_in_at=saved_user.last_sign_in_at,
            preferences=UserPreferencesResponseDTO(
                locale=saved_user.locale,
                timezone=saved_user.timezone,
                currency=saved_user.default_currency,
                date_format=saved_user.date_format,
                time_format=saved_user.time_format,
                notifications_enabled=saved_user.notifications_enabled,
                email_notifications=saved_user.email_notifications,
                weekly_summary=saved_user.weekly_summary
            ),
            default_currency=saved_user.default_currency,
            created_at=saved_user.created_at,
            updated_at=saved_user.updated_at
        )


class UpdateUserUseCase(AuthorizedUseCase, UpdateUseCase[UpdateUserRequestDTO, UserResponseDTO]):
    """Use case for updating user information."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _check_authorization(self, request: UpdateUserRequestDTO) -> None:
        # Users can only update their own profile unless they're admin
        if not self.current_user_id:
            raise ValueError("Authentication required")
    
    async def _execute_command_logic(self, request: UpdateUserRequestDTO) -> UserResponseDTO:
        # Get user
        user = await self.user_repository.find_by_id(self.current_user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update fields
        if request.full_name is not None:
            user.update_profile(full_name=request.full_name)
        if request.phone is not None:
            user.phone = request.phone
        if request.company is not None:
            user.company = request.company
        if request.position is not None:
            user.position = request.position
        if request.bio is not None:
            user.bio = request.bio
        if request.avatar_url is not None:
            user.avatar_url = request.avatar_url
        
        # Save user
        saved_user = await self.user_repository.save(user)
        
        # Return response
        return self._user_to_response_dto(saved_user)


class UpdateUserPreferencesUseCase(AuthorizedUseCase, UpdateUseCase[UpdateUserPreferencesRequestDTO, UserPreferencesResponseDTO]):
    """Use case for updating user preferences."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: UpdateUserPreferencesRequestDTO) -> UserPreferencesResponseDTO:
        # Get user
        user = await self.user_repository.find_by_id(self.current_user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update preferences
        user.update_preferences(
            locale=request.locale,
            timezone=request.timezone,
            currency=request.currency,
            date_format=request.date_format,
            time_format=request.time_format,
            notifications_enabled=request.notifications_enabled,
            email_notifications=request.email_notifications,
            weekly_summary=request.weekly_summary
        )
        
        # Save user
        saved_user = await self.user_repository.save(user)
        
        # Return preferences
        return UserPreferencesResponseDTO(
            locale=saved_user.locale,
            timezone=saved_user.timezone,
            currency=saved_user.default_currency,
            date_format=saved_user.date_format,
            time_format=saved_user.time_format,
            notifications_enabled=saved_user.notifications_enabled,
            email_notifications=saved_user.email_notifications,
            weekly_summary=saved_user.weekly_summary
        )


class UpdateBillingInfoUseCase(AuthorizedUseCase, UpdateUseCase[UpdateBillingInfoRequestDTO, UserResponseDTO]):
    """Use case for updating user billing information."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _execute_command_logic(self, request: UpdateBillingInfoRequestDTO) -> UserResponseDTO:
        # Get user
        user = await self.user_repository.find_by_id(self.current_user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update billing info
        if request.hourly_rate is not None:
            user.default_hourly_rate = request.hourly_rate
        if request.currency is not None:
            user.default_currency = request.currency
        if request.tax_id is not None:
            user.tax_id = request.tax_id
        if request.billing_address is not None:
            user.billing_address = request.billing_address
        
        # Save user
        saved_user = await self.user_repository.save(user)
        
        return self._user_to_response_dto(saved_user)


class ChangePasswordUseCase(AuthorizedUseCase, UpdateUseCase[ChangePasswordRequestDTO, bool]):
    """Use case for changing user password."""
    
    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
    
    async def _execute_command_logic(self, request: ChangePasswordRequestDTO) -> bool:
        # Get user
        user = await self.user_repository.find_by_id(self.current_user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify current password
        if not await self.auth_service.verify_password(request.current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Hash new password
        new_password_hash = await self.auth_service.hash_password(request.new_password)
        
        # Update password
        user.password_hash = new_password_hash
        
        # Save user
        await self.user_repository.save(user)
        
        return True


class GetUserByIdUseCase(AuthorizedUseCase, GetByIdUseCase[str, UserResponseDTO]):
    """Use case for getting user by ID."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _execute_business_logic(self, user_id: str) -> UserResponseDTO:
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        return self._user_to_response_dto(user)


class ListUsersUseCase(AuthorizedUseCase, ListUseCase[ListUsersRequestDTO, UserResponseDTO]):
    """Use case for listing users with filters."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _check_authorization(self, request: ListUsersRequestDTO) -> None:
        # Only admins can list users
        self._require_role("admin")
    
    async def _execute_business_logic(self, request: ListUsersRequestDTO) -> List[UserResponseDTO]:
        users = await self.user_repository.find_with_filters(
            role=request.role,
            status=request.status,
            company=request.company,
            search=request.search,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [self._user_to_response_dto(user) for user in users]


class LoginUseCase(CreateUseCase[LoginRequestDTO, AuthUserResponseDTO]):
    """Use case for user login."""
    
    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
    
    async def _execute_command_logic(self, request: LoginRequestDTO) -> AuthUserResponseDTO:
        # Find user by email
        user = await self.user_repository.find_by_email(str(request.email))
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not await self.auth_service.verify_password(request.password, user.password_hash):
            raise ValueError("Invalid email or password")
        
        # Check if user is active
        if user.status != "active":
            raise ValueError("Account is not active")
        
        # Generate tokens
        access_token, expires_at = await self.auth_service.generate_access_token(user.user_id)
        refresh_token = await self.auth_service.generate_refresh_token(user.user_id) if request.remember_me else None
        
        # Update last sign in
        user.last_sign_in_at = datetime.utcnow()
        await self.user_repository.save(user)
        
        return AuthUserResponseDTO(
            user=self._user_to_response_dto(user),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            token_type="bearer"
        )


class RegisterUseCase(CreateUseCase[RegisterRequestDTO, AuthUserResponseDTO]):
    """Use case for user registration."""
    
    def __init__(self, user_repository: UserRepository, auth_service: AuthService, email_service: EmailService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.email_service = email_service
    
    async def _execute_command_logic(self, request: RegisterRequestDTO) -> AuthUserResponseDTO:
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(str(request.email))
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = await self.auth_service.hash_password(request.password)
        
        # Create user
        user = User.create(
            email=str(request.email),
            full_name=request.full_name,
            password_hash=hashed_password,
            phone=request.phone,
            company=request.company,
            position=request.position
        )
        
        # Save user
        saved_user = await self.user_repository.save(user)
        
        # Send verification email
        verification_token = await self.auth_service.generate_verification_token(saved_user.user_id)
        await self.email_service.send_verification_email(saved_user.email, verification_token)
        
        # Generate tokens
        access_token, expires_at = await self.auth_service.generate_access_token(saved_user.user_id)
        
        return AuthUserResponseDTO(
            user=self._user_to_response_dto(saved_user),
            access_token=access_token,
            expires_at=expires_at,
            token_type="bearer"
        )


class RefreshTokenUseCase(CreateUseCase[RefreshTokenRequestDTO, AuthUserResponseDTO]):
    """Use case for refreshing access tokens."""
    
    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        super().__init__()
        self.user_repository = user_repository
        self.auth_service = auth_service
    
    async def _execute_command_logic(self, request: RefreshTokenRequestDTO) -> AuthUserResponseDTO:
        # Validate refresh token
        user_id = await self.auth_service.validate_refresh_token(request.refresh_token)
        if not user_id:
            raise ValueError("Invalid refresh token")
        
        # Get user
        user = await self.user_repository.find_by_id(user_id)
        if not user or user.status != "active":
            raise ValueError("User not found or inactive")
        
        # Generate new tokens
        access_token, expires_at = await self.auth_service.generate_access_token(user.user_id)
        new_refresh_token = await self.auth_service.generate_refresh_token(user.user_id)
        
        return AuthUserResponseDTO(
            user=self._user_to_response_dto(user),
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_at=expires_at,
            token_type="bearer"
        )


class GetUserStatsUseCase(AuthorizedUseCase, GetByIdUseCase[str, UserStatsResponseDTO]):
    """Use case for getting user statistics."""
    
    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository
    
    async def _execute_business_logic(self, user_id: str) -> UserStatsResponseDTO:
        # Users can only get their own stats unless they're admin
        if user_id != self.current_user_id and "admin" not in self.current_user_roles:
            raise ValueError("Insufficient permissions")
        
        stats = await self.user_repository.get_user_stats(user_id)
        
        return UserStatsResponseDTO(
            total_projects=stats.total_projects,
            active_projects=stats.active_projects,
            total_clients=stats.total_clients,
            total_hours_tracked=stats.total_hours_tracked,
            total_revenue=stats.total_revenue,
            hours_this_week=stats.hours_this_week,
            hours_this_month=stats.hours_this_month,
            avg_hourly_rate=stats.avg_hourly_rate
        )


    def _user_to_response_dto(self, user: User) -> UserResponseDTO:
        """Convert User domain model to response DTO."""
        return UserResponseDTO(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            company=user.company,
            position=user.position,
            bio=user.bio,
            role=user.role,
            status=user.status,
            email_verified=user.email_verified,
            email_verified_at=user.email_verified_at,
            last_sign_in_at=user.last_sign_in_at,
            preferences=UserPreferencesResponseDTO(
                locale=user.locale,
                timezone=user.timezone,
                currency=user.default_currency,
                date_format=user.date_format,
                time_format=user.time_format,
                notifications_enabled=user.notifications_enabled,
                email_notifications=user.email_notifications,
                weekly_summary=user.weekly_summary
            ),
            default_hourly_rate=user.default_hourly_rate,
            default_currency=user.default_currency,
            tax_id=user.tax_id,
            billing_address=user.billing_address,
            created_at=user.created_at,
            updated_at=user.updated_at
        )