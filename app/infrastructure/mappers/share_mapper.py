"""
Share mapper for converting between domain entities and database models.
"""

import json
from typing import Optional

from app.domain.models.share import Share, ShareStatus, SharePermissions
from app.infrastructure.db.models import ShareModel


class ShareMapper:
    """Maps between Share domain entity and ShareModel database model."""
    
    def domain_to_model(self, share: Share) -> ShareModel:
        """Convert Share domain entity to ShareModel."""
        return ShareModel(
            id=share.id,
            owner_id=share.owner_id,
            resource_type=share.resource_type,
            resource_id=share.resource_id,
            share_token=share.share_token,
            status=share.status.value,
            permissions=json.dumps([p.value for p in share.permissions]),
            expires_at=share.expires_at,
            max_access_count=share.max_access_count,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at,
            shared_with_email=share.shared_with_email,
            message=share.message,
            created_at=share.created_at,
            updated_at=share.updated_at,
            version=share.version
        )
    
    def model_to_domain(self, model: ShareModel) -> Share:
        """Convert ShareModel to Share domain entity."""
        # Parse permissions JSON
        permissions = []
        if model.permissions:
            try:
                permission_values = json.loads(model.permissions)
                permissions = [SharePermissions(p) for p in permission_values]
            except (json.JSONDecodeError, TypeError):
                permissions = [SharePermissions.READ]
        
        share = Share(
            owner_id=model.owner_id,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            share_token=model.share_token,
            status=ShareStatus(model.status) if model.status else ShareStatus.ACTIVE,
            permissions=permissions,
            expires_at=model.expires_at,
            max_access_count=model.max_access_count,
            access_count=model.access_count or 0,
            last_accessed_at=model.last_accessed_at,
            shared_with_email=model.shared_with_email,
            message=model.message
        )
        
        # Set entity metadata
        share.id = model.id
        share.created_at = model.created_at
        share.updated_at = model.updated_at
        share.version = model.version or 1
        
        return share