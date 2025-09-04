"""
Share use cases for the application layer.
Implements business logic for resource sharing operations.
"""

from typing import List, Optional
from datetime import datetime, date
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.share_dto import (
    CreateShareRequestDTO, UpdateShareRequestDTO, AccessSharedResourceRequestDTO,
    RevokeShareRequestDTO, ListSharesRequestDTO, ShareAnalyticsRequestDTO,
    ShareResponseDTO, ShareSummaryResponseDTO, SharedResourceResponseDTO,
    ShareAccessLogResponseDTO, ShareStatsResponseDTO, ShareAnalyticsResponseDTO,
    BulkUpdateSharesRequestDTO, BulkRevokeSharesRequestDTO, ExportShareAnalyticsRequestDTO,
    ShareTemplateRequestDTO, ShareTemplateResponseDTO
)
from app.domain.models.share import (
    Share, ShareableType, ShareType, ShareStatus, ShareAccess, SharePermissions
)
from app.domain.repositories.share_repository import ShareRepository
from app.domain.repositories.project_repository import ProjectRepository
from app.domain.repositories.invoice_repository import InvoiceRepository
from app.domain.repositories.user_repository import UserRepositoryInterface as UserRepository
from app.domain.services.sharing_service import SharingService


class CreateShareUseCase(AuthorizedUseCase, CreateUseCase[CreateShareRequestDTO, ShareResponseDTO]):
    """Use case for creating a new share."""
    
    def __init__(
        self, 
        share_repository: ShareRepository,
        project_repository: ProjectRepository,
        invoice_repository: InvoiceRepository,
        sharing_service: SharingService
    ):
        super().__init__()
        self.share_repository = share_repository
        self.project_repository = project_repository
        self.invoice_repository = invoice_repository
        self.sharing_service = sharing_service
    
    async def _execute_command_logic(self, request: CreateShareRequestDTO) -> ShareResponseDTO:
        # Verify resource exists and user has access
        resource = await self._get_and_verify_resource(request.resource_type, request.resource_id)
        
        # Create permissions
        permissions = SharePermissions(
            can_view=request.permissions.can_view,
            can_download=request.permissions.can_download,
            can_comment=request.permissions.can_comment,
            can_edit=request.permissions.can_edit if request.permissions.can_edit is not None else False
        )
        
        # Create share
        share = Share.create(
            owner_id=self.current_user_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            share_type=request.share_type,
            permissions=permissions,
            expires_at=request.expires_at,
            max_access_count=request.max_access_count,
            password=request.password,
            require_email=request.require_email,
            allow_anonymous=request.allow_anonymous,
            title=request.title,
            description=request.description,
            custom_message=request.custom_message
        )
        
        # Generate share token and URL
        await self.sharing_service.generate_share_token(share)
        
        # Save share
        saved_share = await self.share_repository.save(share)
        
        return await self._share_to_response_dto(saved_share)
    
    async def _get_and_verify_resource(self, resource_type: ShareableType, resource_id: int):
        """Verify that the resource exists and user has permission to share it."""
        if resource_type == ShareableType.PROJECT:
            project = await self.project_repository.find_by_id(resource_id)
            if not project:
                raise ValueError("Project not found")
            
            # Check if user has access to project
            member = project.get_member(self.current_user_id)
            if not member and project.owner_id != self.current_user_id:
                self._require_role("admin")
            
            return project
            
        elif resource_type == ShareableType.INVOICE:
            invoice = await self.invoice_repository.find_by_id(resource_id)
            if not invoice:
                raise ValueError("Invoice not found")
            
            # Check if user owns the invoice
            self._require_owner_or_role(invoice.owner_id, "admin")
            return invoice
            
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")


class UpdateShareUseCase(AuthorizedUseCase, UpdateUseCase[UpdateShareRequestDTO, ShareResponseDTO]):
    """Use case for updating a share."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _check_authorization(self, request: UpdateShareRequestDTO) -> None:
        if hasattr(request, 'id'):
            share = await self.share_repository.find_by_id(request.id)
            if share:
                self._require_owner_or_role(share.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateShareRequestDTO) -> ShareResponseDTO:
        # Get share
        share = await self.share_repository.find_by_id(request.id)
        if not share:
            raise ValueError("Share not found")
        
        # Check if share can be updated
        if share.status == ShareStatus.REVOKED:
            raise ValueError("Cannot update revoked shares")
        
        # Update basic fields
        if request.title is not None:
            share.title = request.title
        if request.description is not None:
            share.description = request.description
        if request.custom_message is not None:
            share.custom_message = request.custom_message
        if request.expires_at is not None:
            share.expires_at = request.expires_at
        if request.max_access_count is not None:
            share.max_access_count = request.max_access_count
        if request.password is not None:
            share.set_password(request.password)
        if request.require_email is not None:
            share.require_email = request.require_email
        if request.allow_anonymous is not None:
            share.allow_anonymous = request.allow_anonymous
        
        # Update permissions
        if request.permissions is not None:
            share.permissions = SharePermissions(
                can_view=request.permissions.can_view,
                can_download=request.permissions.can_download,
                can_comment=request.permissions.can_comment,
                can_edit=request.permissions.can_edit if request.permissions.can_edit is not None else False
            )
        
        # Save share
        saved_share = await self.share_repository.save(share)
        
        return await self._share_to_response_dto(saved_share)


class AccessSharedResourceUseCase(CreateUseCase[AccessSharedResourceRequestDTO, SharedResourceResponseDTO]):
    """Use case for accessing a shared resource."""
    
    def __init__(
        self, 
        share_repository: ShareRepository,
        sharing_service: SharingService
    ):
        super().__init__()
        self.share_repository = share_repository
        self.sharing_service = sharing_service
    
    async def _execute_command_logic(self, request: AccessSharedResourceRequestDTO) -> SharedResourceResponseDTO:
        # Get share by token
        share = await self.share_repository.find_by_token(request.share_token)
        if not share:
            raise ValueError("Invalid share token")
        
        # Check if share is accessible
        if share.status != ShareStatus.ACTIVE:
            raise ValueError("Share is not active")
        
        if share.is_expired:
            raise ValueError("Share has expired")
        
        if share.is_access_limit_reached:
            raise ValueError("Share access limit reached")
        
        # Verify password if required
        if share.password and not share.verify_password(request.password):
            raise ValueError("Invalid password")
        
        # Verify email if required
        if share.require_email and not request.accessor_email:
            raise ValueError("Email is required to access this share")
        
        # Record access
        access_log = share.record_access(
            accessor_email=request.accessor_email,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        # Save share with new access log
        await self.share_repository.save(share)
        
        # Get shared resource data
        resource_data = await self.sharing_service.get_shared_resource_data(share)
        
        return SharedResourceResponseDTO(
            share_id=share.id,
            resource_type=share.resource_type,
            resource_id=share.resource_id,
            title=share.title or "Shared Resource",
            description=share.description,
            custom_message=share.custom_message,
            permissions=share.permissions,
            resource_data=resource_data,
            access_count=share.access_count,
            expires_at=share.expires_at,
            owner_name=resource_data.get("owner_name", "Unknown"),
            accessed_at=access_log.accessed_at
        )


class RevokeShareUseCase(AuthorizedUseCase, UpdateUseCase[RevokeShareRequestDTO, bool]):
    """Use case for revoking a share."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_command_logic(self, request: RevokeShareRequestDTO) -> bool:
        # Get share
        share = await self.share_repository.find_by_id(request.id)
        if not share:
            raise ValueError("Share not found")
        
        # Check authorization
        self._require_owner_or_role(share.owner_id, "admin")
        
        # Revoke share
        share.revoke(reason=request.reason)
        
        # Save share
        await self.share_repository.save(share)
        
        return True


class GetShareByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, ShareResponseDTO]):
    """Use case for getting share by ID."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, share_id: int) -> ShareResponseDTO:
        share = await self.share_repository.find_by_id(share_id)
        if not share:
            raise ValueError("Share not found")
        
        # Check authorization
        self._require_owner_or_role(share.owner_id, "admin")
        
        return await self._share_to_response_dto(share)


class ListSharesUseCase(AuthorizedUseCase, ListUseCase[ListSharesRequestDTO, ShareSummaryResponseDTO]):
    """Use case for listing shares with filters."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, request: ListSharesRequestDTO) -> List[ShareSummaryResponseDTO]:
        shares = await self.share_repository.find_with_filters(
            owner_id=self.current_user_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            share_type=request.share_type,
            status=request.status,
            is_expired=request.is_expired,
            has_password=request.has_password,
            search=request.search,
            created_from=request.created_from,
            created_to=request.created_to,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [await self._share_to_summary_dto(share) for share in shares]


class DeleteShareUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting a share."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_command_logic(self, share_id: int) -> bool:
        # Get share
        share = await self.share_repository.find_by_id(share_id)
        if not share:
            raise ValueError("Share not found")
        
        # Check authorization
        self._require_owner_or_role(share.owner_id, "admin")
        
        # Delete share
        await self.share_repository.delete(share_id)
        
        return True


class BulkUpdateSharesUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateSharesRequestDTO, dict]):
    """Use case for bulk updating shares."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, request: BulkUpdateSharesRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for share_id in request.share_ids:
            try:
                # Get share
                share = await self.share_repository.find_by_id(share_id)
                if not share:
                    results["errors"].append({"id": share_id, "error": "Share not found"})
                    continue
                
                # Check authorization
                if share.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": share_id, "error": "Insufficient permissions"})
                    continue
                
                # Check if share can be updated
                if share.status == ShareStatus.REVOKED and request.status != ShareStatus.ACTIVE:
                    results["errors"].append({"id": share_id, "error": "Cannot update revoked shares"})
                    continue
                
                # Apply updates
                if request.status is not None:
                    if request.status == ShareStatus.REVOKED:
                        share.revoke(reason="Bulk revocation")
                    else:
                        share.status = request.status
                
                if request.expires_at is not None:
                    share.expires_at = request.expires_at
                
                if request.max_access_count is not None:
                    share.max_access_count = request.max_access_count
                
                # Save share
                await self.share_repository.save(share)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": share_id, "error": str(e)})
        
        return results


class BulkRevokeSharesUseCase(AuthorizedUseCase, BulkUseCase[BulkRevokeSharesRequestDTO, dict]):
    """Use case for bulk revoking shares."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, request: BulkRevokeSharesRequestDTO) -> dict:
        results = {"revoked": 0, "errors": []}
        
        for share_id in request.share_ids:
            try:
                # Get share
                share = await self.share_repository.find_by_id(share_id)
                if not share:
                    results["errors"].append({"id": share_id, "error": "Share not found"})
                    continue
                
                # Check authorization
                if share.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": share_id, "error": "Insufficient permissions"})
                    continue
                
                # Revoke share
                share.revoke(reason=request.reason or "Bulk revocation")
                
                # Save share
                await self.share_repository.save(share)
                results["revoked"] += 1
                
            except Exception as e:
                results["errors"].append({"id": share_id, "error": str(e)})
        
        return results


class GetShareStatsUseCase(AuthorizedUseCase, GetByIdUseCase[int, ShareStatsResponseDTO]):
    """Use case for getting share statistics."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, user_id: int) -> ShareStatsResponseDTO:
        # Check authorization
        if user_id != self.current_user_id:
            self._require_role("admin")
        
        # Get stats
        stats = await self.share_repository.get_share_stats(user_id)
        
        return ShareStatsResponseDTO(
            total_shares=stats.total_shares,
            active_shares=stats.active_shares,
            expired_shares=stats.expired_shares,
            revoked_shares=stats.revoked_shares,
            public_shares=stats.public_shares,
            private_shares=stats.private_shares,
            password_protected_shares=stats.password_protected_shares,
            total_access_count=stats.total_access_count,
            unique_accessors=stats.unique_accessors,
            most_accessed_share_id=stats.most_accessed_share_id,
            avg_access_per_share=stats.avg_access_per_share,
            shares_created_this_month=stats.shares_created_this_month,
            shares_created_last_month=stats.shares_created_last_month
        )


class GetShareAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[ShareAnalyticsRequestDTO, ShareAnalyticsResponseDTO]):
    """Use case for getting share analytics."""
    
    def __init__(
        self, 
        share_repository: ShareRepository,
        sharing_service: SharingService
    ):
        super().__init__()
        self.share_repository = share_repository
        self.sharing_service = sharing_service
    
    async def _execute_business_logic(self, request: ShareAnalyticsRequestDTO) -> ShareAnalyticsResponseDTO:
        # Check authorization
        if request.user_id != self.current_user_id:
            self._require_role("admin")
        
        # Get analytics
        analytics = await self.sharing_service.get_share_analytics(
            user_id=request.user_id,
            date_from=request.date_from,
            date_to=request.date_to,
            resource_type=request.resource_type
        )
        
        return ShareAnalyticsResponseDTO(
            user_id=request.user_id,
            date_from=request.date_from,
            date_to=request.date_to,
            access_trends=analytics.access_trends,
            popular_resources=analytics.popular_resources,
            geographic_distribution=analytics.geographic_distribution,
            device_breakdown=analytics.device_breakdown,
            time_patterns=analytics.time_patterns,
            conversion_metrics=analytics.conversion_metrics,
            security_events=analytics.security_events
        )


class GetShareAccessLogUseCase(AuthorizedUseCase, GetByIdUseCase[int, List[ShareAccessLogResponseDTO]]):
    """Use case for getting share access logs."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_business_logic(self, share_id: int) -> List[ShareAccessLogResponseDTO]:
        # Get share
        share = await self.share_repository.find_by_id(share_id)
        if not share:
            raise ValueError("Share not found")
        
        # Check authorization
        self._require_owner_or_role(share.owner_id, "admin")
        
        # Get access logs
        access_logs = await self.share_repository.get_share_access_logs(share_id)
        
        return [
            ShareAccessLogResponseDTO(
                id=log.id,
                share_id=log.share_id,
                accessor_email=log.accessor_email,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                accessed_at=log.accessed_at,
                location=log.location,
                device_info=log.device_info
            )
            for log in access_logs
        ]


class CreateShareTemplateUseCase(AuthorizedUseCase, CreateUseCase[ShareTemplateRequestDTO, ShareTemplateResponseDTO]):
    """Use case for creating a share template."""
    
    def __init__(self, share_repository: ShareRepository):
        super().__init__()
        self.share_repository = share_repository
    
    async def _execute_command_logic(self, request: ShareTemplateRequestDTO) -> ShareTemplateResponseDTO:
        # Create share template
        template = await self.share_repository.create_share_template(
            owner_id=self.current_user_id,
            name=request.name,
            description=request.description,
            share_type=request.share_type,
            permissions=request.permissions,
            expires_in_days=request.expires_in_days,
            max_access_count=request.max_access_count,
            require_password=request.require_password,
            require_email=request.require_email,
            allow_anonymous=request.allow_anonymous,
            custom_message_template=request.custom_message_template
        )
        
        return ShareTemplateResponseDTO(
            id=template.id,
            owner_id=template.owner_id,
            name=template.name,
            description=template.description,
            share_type=template.share_type,
            permissions=template.permissions,
            expires_in_days=template.expires_in_days,
            max_access_count=template.max_access_count,
            require_password=template.require_password,
            require_email=template.require_email,
            allow_anonymous=template.allow_anonymous,
            custom_message_template=template.custom_message_template,
            usage_count=template.usage_count,
            created_at=template.created_at,
            updated_at=template.updated_at
        )


    async def _share_to_response_dto(self, share: Share) -> ShareResponseDTO:
        """Convert Share domain model to response DTO."""
        # Get resource info
        resource_name = ""
        if share.resource_type == ShareableType.PROJECT and hasattr(self, 'project_repository'):
            project = await self.project_repository.find_by_id(share.resource_id)
            resource_name = project.name if project else f"Project #{share.resource_id}"
        elif share.resource_type == ShareableType.INVOICE and hasattr(self, 'invoice_repository'):
            invoice = await self.invoice_repository.find_by_id(share.resource_id)
            resource_name = invoice.invoice_number if invoice else f"Invoice #{share.resource_id}"
        
        # Get access logs
        recent_accesses = []
        for access in share.access_logs[-5:]:  # Get last 5 accesses
            recent_accesses.append(ShareAccessLogResponseDTO(
                id=access.id,
                share_id=share.id,
                accessor_email=access.accessor_email,
                ip_address=access.ip_address,
                user_agent=access.user_agent,
                accessed_at=access.accessed_at,
                location=access.location,
                device_info=access.device_info
            ))
        
        return ShareResponseDTO(
            id=share.id,
            owner_id=share.owner_id,
            resource_type=share.resource_type,
            resource_id=share.resource_id,
            resource_name=resource_name,
            share_type=share.share_type,
            status=share.status,
            share_token=share.share_token,
            share_url=share.share_url,
            permissions=share.permissions,
            title=share.title,
            description=share.description,
            custom_message=share.custom_message,
            expires_at=share.expires_at,
            max_access_count=share.max_access_count,
            access_count=share.access_count,
            has_password=share.has_password,
            require_email=share.require_email,
            allow_anonymous=share.allow_anonymous,
            recent_accesses=recent_accesses,
            is_expired=share.is_expired,
            is_access_limit_reached=share.is_access_limit_reached,
            days_until_expiry=share.days_until_expiry,
            revoked_at=share.revoked_at,
            revoke_reason=share.revoke_reason,
            created_at=share.created_at,
            updated_at=share.updated_at
        )
    
    async def _share_to_summary_dto(self, share: Share) -> ShareSummaryResponseDTO:
        """Convert Share domain model to summary DTO."""
        # Get resource info
        resource_name = ""
        if share.resource_type == ShareableType.PROJECT and hasattr(self, 'project_repository'):
            project = await self.project_repository.find_by_id(share.resource_id)
            resource_name = project.name if project else f"Project #{share.resource_id}"
        elif share.resource_type == ShareableType.INVOICE and hasattr(self, 'invoice_repository'):
            invoice = await self.invoice_repository.find_by_id(share.resource_id)
            resource_name = invoice.invoice_number if invoice else f"Invoice #{share.resource_id}"
        
        return ShareSummaryResponseDTO(
            id=share.id,
            resource_type=share.resource_type,
            resource_name=resource_name,
            share_type=share.share_type,
            status=share.status,
            title=share.title or resource_name,
            access_count=share.access_count,
            max_access_count=share.max_access_count,
            expires_at=share.expires_at,
            is_expired=share.is_expired,
            has_password=share.has_password,
            last_accessed=share.last_accessed,
            created_at=share.created_at
        )