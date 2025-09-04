"""Sharing service for generating and managing public sharing links.
Handles link generation, access control, and sharing analytics.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import secrets
import string
import hashlib

from app.domain.models.base import ValidationError, BusinessRuleViolation
from app.domain.models.share import (
    Share, ShareableType, ShareType, ShareStatus, SharePermissions
)


class SharingService:
    """
    Domain service for managing public sharing functionality.
    Handles share creation, access control, and analytics.
    """

    def __init__(self):
        self.default_token_length = 32
        self.default_expiry_days = 30
        self.max_expiry_days = 365
        self.min_password_length = 6
        self.max_views_limit = 10000

    def create_share(
        self,
        shareable_type: ShareableType,
        entity_id: int,
        created_by: str,
        share_type: ShareType = ShareType.PUBLIC,
        title: Optional[str] = None,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        password: Optional[str] = None,
        custom_permissions: Optional[SharePermissions] = None,
        custom_slug: Optional[str] = None
    ) -> Share:
        """
        Create a new share link for an entity.
        """
        # Validate inputs
        self._validate_share_creation_inputs(
            shareable_type=shareable_type,
            entity_id=entity_id,
            created_by=created_by,
            expires_in_days=expires_in_days,
            password=password,
            custom_slug=custom_slug
        )
        
        # Set expiration if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create permissions based on shareable type
        permissions = custom_permissions or self._get_default_permissions(shareable_type)
        
        # Create the share
        share = Share(
            created_by=created_by,
            shareable_type=shareable_type,
            entity_id=entity_id,
            share_type=share_type,
            title=title,
            description=description,
            expires_at=expires_at,
            password=password,
            permissions=permissions,
            custom_slug=custom_slug
        )
        
        return share

    def create_project_share(
        self,
        project_id: int,
        created_by: str,
        title: Optional[str] = None,
        password: Optional[str] = None,
        expires_in_days: int = 30,
        allow_download: bool = True
    ) -> Share:
        """
        Create a share specifically for a project.
        """
        permissions = SharePermissions(
            can_view=True,
            can_download=allow_download,
            can_print=False,
            can_export=allow_download,
            show_watermark=True,
            hide_sensitive_data=True  # Hide sensitive project data
        )
        
        return self.create_share(
            shareable_type=ShareableType.PROJECT,
            entity_id=project_id,
            created_by=created_by,
            share_type=ShareType.PASSWORD_PROTECTED if password else ShareType.PUBLIC,
            title=title or f"Project #{project_id}",
            expires_in_days=expires_in_days,
            password=password,
            custom_permissions=permissions
        )

    def create_invoice_share(
        self,
        invoice_id: int,
        created_by: str,
        title: Optional[str] = None,
        expires_in_days: int = 60,  # Longer expiry for invoices
        hide_amounts: bool = False
    ) -> Share:
        """
        Create a share specifically for an invoice.
        """
        permissions = SharePermissions(
            can_view=True,
            can_download=True,
            can_print=True,
            can_export=True,
            show_watermark=False,  # No watermark on invoices
            hide_sensitive_data=hide_amounts
        )
        
        return self.create_share(
            shareable_type=ShareableType.INVOICE,
            entity_id=invoice_id,
            created_by=created_by,
            share_type=ShareType.PUBLIC,
            title=title or f"Invoice #{invoice_id}",
            expires_in_days=expires_in_days,
            custom_permissions=permissions
        )

    def create_timesheet_share(
        self,
        project_id: int,
        created_by: str,
        start_date: datetime,
        end_date: datetime,
        title: Optional[str] = None,
        password: Optional[str] = None,
        expires_in_days: int = 14  # Shorter expiry for timesheets
    ) -> Share:
        """
        Create a share for a timesheet report.
        """
        permissions = SharePermissions(
            can_view=True,
            can_download=True,
            can_print=True,
            can_export=False,  # Prevent export of raw time data
            show_watermark=True,
            hide_sensitive_data=False
        )
        
        period = f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d/%Y')}"
        
        return self.create_share(
            shareable_type=ShareableType.TIMESHEET,
            entity_id=project_id,
            created_by=created_by,
            share_type=ShareType.PASSWORD_PROTECTED if password else ShareType.PUBLIC,
            title=title or f"Timesheet {period}",
            expires_in_days=expires_in_days,
            password=password,
            custom_permissions=permissions
        )

    def update_share_permissions(
        self,
        share: Share,
        permissions: SharePermissions,
        updated_by: str
    ) -> Share:
        """
        Update permissions for an existing share.
        """
        if share.created_by != updated_by:
            raise BusinessRuleViolation("Only the share creator can update permissions")
        
        if share.status == ShareStatus.REVOKED:
            raise BusinessRuleViolation("Cannot update permissions on revoked share")
        
        permissions.validate()
        share.update_permissions(permissions)
        
        return share

    def set_share_expiry(
        self,
        share: Share,
        expires_at: Optional[datetime],
        updated_by: str
    ) -> Share:
        """
        Set or update share expiry time.
        """
        if share.created_by != updated_by:
            raise BusinessRuleViolation("Only the share creator can update expiry")
        
        if expires_at and expires_at <= datetime.utcnow():
            raise ValidationError("Expiry time must be in the future", "expires_at")
        
        if expires_at and expires_at > datetime.utcnow() + timedelta(days=self.max_expiry_days):
            raise ValidationError(
                f"Expiry cannot be more than {self.max_expiry_days} days in the future",
                "expires_at"
            )
        
        share.set_expiry(expires_at)
        return share

    def set_share_password(
        self,
        share: Share,
        password: Optional[str],
        updated_by: str
    ) -> Share:
        """
        Set or update share password.
        """
        if share.created_by != updated_by:
            raise BusinessRuleViolation("Only the share creator can update password")
        
        if password and len(password) < self.min_password_length:
            raise ValidationError(
                f"Password must be at least {self.min_password_length} characters",
                "password"
            )
        
        share.set_password(password)
        return share

    def validate_share_access(
        self,
        share: Share,
        password: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate if a share can be accessed with given parameters.
        """
        result = {
            "can_access": False,
            "reason": None,
            "requires_password": False,
            "remaining_views": None,
            "expires_at": None
        }
        
        # Check basic accessibility
        can_access, reason = share.can_be_accessed(ip_address, referer)
        
        if not can_access:
            result["reason"] = reason
            return result
        
        # Check password if required
        if share.is_password_protected:
            result["requires_password"] = True
            
            if not password:
                result["reason"] = "Password required"
                return result
            
            if not share.verify_password(password):
                result["reason"] = "Invalid password"
                return result
        
        # All checks passed
        result["can_access"] = True
        result["remaining_views"] = share.remaining_views
        result["expires_at"] = share.expires_at.isoformat() if share.expires_at else None
        
        return result

    def record_share_access(
        self,
        share: Share,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record an access to a share and return access info.
        """
        # Record the access
        share.record_access(ip_address, user_agent, referer)
        
        return {
            "view_count": share.view_count,
            "remaining_views": share.remaining_views,
            "is_expired": share.is_expired,
            "last_accessed_at": share.last_accessed_at.isoformat() if share.last_accessed_at else None
        }

    def generate_share_url(
        self,
        share: Share,
        base_url: str
    ) -> str:
        """
        Generate the complete URL for accessing a share.
        """
        return share.get_public_url(base_url)

    def create_qr_code_data(
        self,
        share: Share,
        base_url: str
    ) -> Dict[str, Any]:
        """
        Create QR code data for a share.
        """
        url = self.generate_share_url(share, base_url)
        
        return {
            "url": url,
            "title": share.title or f"{share.shareable_type.value.title()} Share",
            "description": share.description,
            "qr_data": url,  # The actual data to encode in QR
            "expires_at": share.expires_at.isoformat() if share.expires_at else None
        }

    def get_share_analytics(
        self,
        share: Share,
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        Get analytics data for a share.
        """
        analytics = share.get_analytics()
        
        if detailed:
            # Add more detailed analytics
            analytics.update({
                "share_info": {
                    "created_at": share.created_at.isoformat(),
                    "status": share.status.value,
                    "share_type": share.share_type.value,
                    "is_password_protected": share.is_password_protected,
                    "has_expiry": share.expires_at is not None
                },
                "access_patterns": self._analyze_access_patterns(share.access_log),
                "geographic_distribution": self._analyze_geographic_distribution(share.access_log)
            })
        
        return analytics

    def bulk_expire_shares(
        self,
        shares: List[Share],
        reason: str = "Bulk expiration"
    ) -> int:
        """
        Bulk expire multiple shares.
        """
        expired_count = 0
        
        for share in shares:
            if share.is_active:
                share.status = ShareStatus.EXPIRED
                share.mark_as_updated()
                expired_count += 1
        
        return expired_count

    def cleanup_expired_shares(
        self,
        shares: List[Share],
        grace_period_days: int = 7
    ) -> int:
        """
        Clean up shares that have been expired for a while.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=grace_period_days)
        cleaned_count = 0
        
        for share in shares:
            if (share.status == ShareStatus.EXPIRED and 
                share.expires_at and 
                share.expires_at < cutoff_date):
                # Mark for cleanup (actual deletion would be handled by infrastructure layer)
                share.status = ShareStatus.REVOKED
                share.mark_as_updated()
                cleaned_count += 1
        
        return cleaned_count

    def suggest_share_settings(
        self,
        shareable_type: ShareableType,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Suggest optimal share settings based on type and context.
        """
        context = context or {}
        
        suggestions = {
            "share_type": ShareType.PUBLIC,
            "expires_in_days": self.default_expiry_days,
            "permissions": self._get_default_permissions(shareable_type),
            "requires_password": False,
            "max_views": None
        }
        
        # Adjust based on shareable type
        if shareable_type == ShareableType.INVOICE:
            suggestions.update({
                "expires_in_days": 60,  # Longer for invoices
                "requires_password": False,  # Usually public for clients
            })
        elif shareable_type == ShareableType.PROJECT:
            suggestions.update({
                "expires_in_days": 30,
                "requires_password": True,  # More sensitive data
                "share_type": ShareType.PASSWORD_PROTECTED
            })
        elif shareable_type == ShareableType.TIMESHEET:
            suggestions.update({
                "expires_in_days": 14,  # Shorter for time data
                "requires_password": True,
                "max_views": 50  # Limit views for timesheets
            })
        
        # Adjust based on context
        if context.get("is_sensitive", False):
            suggestions.update({
                "requires_password": True,
                "share_type": ShareType.PASSWORD_PROTECTED,
                "expires_in_days": min(suggestions["expires_in_days"], 7),
                "max_views": 10
            })
        
        if context.get("client_share", False):
            suggestions.update({
                "requires_password": False,  # Easier for clients
                "expires_in_days": 90  # Longer for client access
            })
        
        return suggestions

    def _validate_share_creation_inputs(
        self,
        shareable_type: ShareableType,
        entity_id: int,
        created_by: str,
        expires_in_days: Optional[int],
        password: Optional[str],
        custom_slug: Optional[str]
    ) -> None:
        """
        Validate inputs for share creation.
        """
        if not created_by:
            raise ValidationError("Created by is required", "created_by")
        
        if entity_id <= 0:
            raise ValidationError("Entity ID must be positive", "entity_id")
        
        if expires_in_days is not None:
            if expires_in_days <= 0:
                raise ValidationError("Expires in days must be positive", "expires_in_days")
            
            if expires_in_days > self.max_expiry_days:
                raise ValidationError(
                    f"Expires in days cannot exceed {self.max_expiry_days}",
                    "expires_in_days"
                )
        
        if password and len(password) < self.min_password_length:
            raise ValidationError(
                f"Password must be at least {self.min_password_length} characters",
                "password"
            )
        
        if custom_slug:
            if len(custom_slug) < 3:
                raise ValidationError("Custom slug must be at least 3 characters", "custom_slug")
            
            if not custom_slug.replace('-', '').replace('_', '').isalnum():
                raise ValidationError(
                    "Custom slug can only contain letters, numbers, hyphens, and underscores",
                    "custom_slug"
                )

    def _get_default_permissions(self, shareable_type: ShareableType) -> SharePermissions:
        """
        Get default permissions based on shareable type.
        """
        permissions_map = {
            ShareableType.PROJECT: SharePermissions(
                can_view=True,
                can_download=True,
                can_print=False,
                can_export=False,
                show_watermark=True,
                hide_sensitive_data=True
            ),
            ShareableType.INVOICE: SharePermissions(
                can_view=True,
                can_download=True,
                can_print=True,
                can_export=True,
                show_watermark=False,
                hide_sensitive_data=False
            ),
            ShareableType.TIMESHEET: SharePermissions(
                can_view=True,
                can_download=True,
                can_print=True,
                can_export=False,
                show_watermark=True,
                hide_sensitive_data=False
            ),
            ShareableType.REPORT: SharePermissions(
                can_view=True,
                can_download=True,
                can_print=True,
                can_export=True,
                show_watermark=True,
                hide_sensitive_data=False
            ),
            ShareableType.TASK_BOARD: SharePermissions(
                can_view=True,
                can_download=False,
                can_print=False,
                can_export=False,
                show_watermark=True,
                hide_sensitive_data=True
            )
        }
        
        return permissions_map.get(shareable_type, SharePermissions())

    def _analyze_access_patterns(self, access_log: List) -> Dict[str, Any]:
        """
        Analyze access patterns from access log.
        """
        if not access_log:
            return {"peak_hours": [], "peak_days": [], "access_frequency": 0}
        
        # Extract hours and days from access log
        hours = []
        days = []
        
        for access in access_log:
            if hasattr(access, 'accessed_at'):
                hour = access.accessed_at.hour
                day = access.accessed_at.strftime('%A')
                hours.append(hour)
                days.append(day)
        
        # Find peak hours and days
        hour_counts = {}
        day_counts = {}
        
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        for day in days:
            day_counts[day] = day_counts.get(day, 0) + 1
        
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "peak_hours": [f"{hour}:00" for hour, _ in peak_hours],
            "peak_days": [day for day, _ in peak_days],
            "access_frequency": len(access_log),
            "unique_hours": len(hour_counts),
            "unique_days": len(day_counts)
        }

    def _analyze_geographic_distribution(self, access_log: List) -> Dict[str, Any]:
        """
        Analyze geographic distribution from access log.
        """
        if not access_log:
            return {"unique_ips": 0, "ip_distribution": {}}
        
        ip_counts = {}
        for access in access_log:
            if hasattr(access, 'ip_address') and access.ip_address:
                ip_counts[access.ip_address] = ip_counts.get(access.ip_address, 0) + 1
        
        return {
            "unique_ips": len(ip_counts),
            "ip_distribution": dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "total_accesses": sum(ip_counts.values())
        }