"""
Share repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.domain.models.share import Share
from app.domain.repositories.share_repository import ShareRepositoryInterface
from app.domain.models.base import EntityNotFoundError, DuplicateEntityError
from app.infrastructure.db.models import ShareModel
from app.infrastructure.mappers.share_mapper import ShareMapper


class SQLAlchemyShareRepository(ShareRepositoryInterface):
    """SQLAlchemy implementation of share repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = ShareMapper()
    
    def save(self, share: Share) -> Share:
        """Save a share entity."""
        if share.is_new:
            # Check for duplicate share token
            existing = self.session.query(ShareModel).filter_by(
                share_token=share.share_token
            ).first()
            if existing:
                raise DuplicateEntityError("Share", "share_token", share.share_token)
            
            # Create new share
            model = self.mapper.domain_to_model(share)
            self.session.add(model)
        else:
            # Update existing share
            model = self.session.query(ShareModel).filter_by(
                id=share.id
            ).first()
            if not model:
                raise EntityNotFoundError("Share", share.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(share)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated share with ID
        if share.is_new:
            share.id = model.id
        return share
    
    def get_by_id(self, share_id: int) -> Optional[Share]:
        """Get share by ID."""
        model = self.session.query(ShareModel).filter_by(
            id=share_id
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_token(self, share_token: str) -> Optional[Share]:
        """Get share by token."""
        model = self.session.query(ShareModel).filter_by(
            share_token=share_token
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_owner(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Share]:
        """Get shares by owner with optional pagination."""
        query = self.session.query(ShareModel).filter_by(
            owner_id=owner_id
        ).order_by(ShareModel.created_at.desc())
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_resource(self, resource_type: str, resource_id: int) -> List[Share]:
        """Get shares by resource."""
        models = self.session.query(ShareModel).filter_by(
            resource_type=resource_type,
            resource_id=resource_id
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, share_id: int) -> bool:
        """Delete share by ID."""
        model = self.session.query(ShareModel).filter_by(
            id=share_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count_by_owner(self, owner_id: str) -> int:
        """Get share count for owner."""
        return self.session.query(func.count(ShareModel.id)).filter_by(
            owner_id=owner_id
        ).scalar()
    
    def get_active_shares(self, owner_id: str) -> List[Share]:
        """Get active (non-expired) shares by owner."""
        now = datetime.utcnow()
        models = self.session.query(ShareModel).filter(
            and_(
                ShareModel.owner_id == owner_id,
                ShareModel.status == 'active',
                or_(
                    ShareModel.expires_at.is_(None),
                    ShareModel.expires_at > now
                )
            )
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_expired_shares(self) -> List[Share]:
        """Get expired shares."""
        now = datetime.utcnow()
        models = self.session.query(ShareModel).filter(
            and_(
                ShareModel.expires_at < now,
                ShareModel.status == 'active'
            )
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_status(self, owner_id: str, status: str) -> List[Share]:
        """Get shares by status."""
        models = self.session.query(ShareModel).filter_by(
            owner_id=owner_id,
            status=status
        ).order_by(ShareModel.created_at.desc()).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def increment_access_count(self, share_id: int) -> None:
        """Increment access count for share."""
        self.session.query(ShareModel).filter_by(
            id=share_id
        ).update({
            "access_count": ShareModel.access_count + 1,
            "last_accessed_at": datetime.utcnow()
        })
    
    def cleanup_expired_shares(self) -> int:
        """Delete expired shares and return count."""
        now = datetime.utcnow()
        count = self.session.query(ShareModel).filter(
            and_(
                ShareModel.expires_at < now,
                ShareModel.status == 'active'
            )
        ).count()
        
        self.session.query(ShareModel).filter(
            and_(
                ShareModel.expires_at < now,
                ShareModel.status == 'active'
            )
        ).update({"status": "expired"})
        
        return count