"""
User repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.domain.models.user import User
from app.domain.repositories.user_repository import UserRepositoryInterface
from app.domain.models.base import EntityNotFoundError, DuplicateEntityError
from app.infrastructure.db.models import UserProfileModel
from app.infrastructure.mappers.user_mapper import UserMapper


class SQLAlchemyUserRepository(UserRepositoryInterface):
    """SQLAlchemy implementation of user repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = UserMapper()
    
    def save(self, user: User) -> User:
        """Save a user entity."""
        if user.is_new:
            # Check for duplicate email
            existing = self.session.query(UserProfileModel).filter_by(
                email=str(user.email)
            ).first()
            if existing:
                raise DuplicateEntityError("User", "email", str(user.email))
            
            # Create new user
            model = self.mapper.domain_to_model(user)
            self.session.add(model)
        else:
            # Update existing user
            model = self.session.query(UserProfileModel).filter_by(
                id=user.id
            ).first()
            if not model:
                raise EntityNotFoundError("User", user.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(user)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated user with ID
        if user.is_new:
            user.id = model.id
        return user
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        model = self.session.query(UserProfileModel).filter_by(
            id=user_id
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        model = self.session.query(UserProfileModel).filter_by(
            email=email
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get all users with optional pagination."""
        query = self.session.query(UserProfileModel)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, user_id: str) -> bool:
        """Delete user by ID."""
        model = self.session.query(UserProfileModel).filter_by(
            id=user_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count(self) -> int:
        """Get total user count."""
        return self.session.query(func.count(UserProfileModel.id)).scalar()
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        return self.session.query(
            self.session.query(UserProfileModel).filter_by(
                email=email
            ).exists()
        ).scalar()
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[User]:
        """Get users by status."""
        query = self.session.query(UserProfileModel).filter_by(status=status)
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_role(self, role: str, limit: Optional[int] = None) -> List[User]:
        """Get users by role."""
        query = self.session.query(UserProfileModel).filter_by(role=role)
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]