"""
User mapper for converting between domain entities and database models.
"""

import json
from typing import Optional
from datetime import datetime

from app.domain.models.user import User, UserPreferences, UserRole, UserStatus
from app.domain.models.base import Email
from app.infrastructure.db.models import UserProfileModel


class UserMapper:
    """Maps between User domain entity and UserProfileModel database model."""
    
    def domain_to_model(self, user: User) -> UserProfileModel:
        """Convert User domain entity to UserProfileModel."""
        return UserProfileModel(
            id=user.user_id,
            email=str(user.email) if user.email else None,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            company=user.company,
            position=user.position,
            bio=user.bio,
            role=user.role.value,
            status=user.status.value,
            preferences=json.dumps(user.preferences.to_dict()),
            email_verified=user.email_verified,
            email_verified_at=user.email_verified_at,
            last_sign_in_at=user.last_sign_in_at,
            default_hourly_rate=user.default_hourly_rate,
            default_currency=user.default_currency,
            tax_id=user.tax_id,
            billing_address=user.billing_address,
            total_projects=user.total_projects,
            total_clients=user.total_clients,
            total_hours_tracked=user.total_hours_tracked,
            total_revenue=user.total_revenue,
            created_at=user.created_at,
            updated_at=user.updated_at,
            version=user.version
        )
    
    def model_to_domain(self, model: UserProfileModel) -> User:
        """Convert UserProfileModel to User domain entity."""
        # Parse preferences JSON
        preferences_data = {}
        if model.preferences:
            try:
                preferences_data = json.loads(model.preferences)
            except (json.JSONDecodeError, TypeError):
                preferences_data = {}
        
        preferences = UserPreferences(**preferences_data)
        
        # Create Email value object
        email = Email(model.email) if model.email else None
        
        user = User(
            user_id=model.id,
            email=email,
            full_name=model.full_name,
            avatar_url=model.avatar_url,
            phone=model.phone,
            company=model.company,
            position=model.position,
            bio=model.bio,
            role=UserRole(model.role) if model.role else UserRole.FREELANCER,
            status=UserStatus(model.status) if model.status else UserStatus.ACTIVE,
            preferences=preferences,
            email_verified=model.email_verified or False,
            email_verified_at=model.email_verified_at,
            last_sign_in_at=model.last_sign_in_at,
            default_hourly_rate=model.default_hourly_rate,
            default_currency=model.default_currency or "USD",
            tax_id=model.tax_id,
            billing_address=model.billing_address,
            total_projects=model.total_projects or 0,
            total_clients=model.total_clients or 0,
            total_hours_tracked=model.total_hours_tracked or 0.0,
            total_revenue=model.total_revenue or 0.0
        )
        
        # Set entity metadata
        user.id = model.id
        user.created_at = model.created_at
        user.updated_at = model.updated_at
        user.version = model.version or 1
        
        return user