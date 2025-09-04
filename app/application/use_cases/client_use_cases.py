"""
Client use cases for the application layer.
Implements business logic for client operations.
"""

from typing import List, Optional
from datetime import datetime
from app.application.use_cases.base_use_case import (
    CreateUseCase, UpdateUseCase, DeleteUseCase, GetByIdUseCase, 
    ListUseCase, SearchUseCase, AuthorizedUseCase, BulkUseCase,
    UseCaseResult
)
from app.application.dto.client_dto import (
    CreateClientRequestDTO, UpdateClientRequestDTO, UpdateClientBillingRequestDTO,
    ListClientsRequestDTO, SearchClientsRequestDTO, ClientResponseDTO,
    ClientSummaryResponseDTO, ClientStatsResponseDTO, ClientActivityResponseDTO,
    BulkUpdateClientsRequestDTO, ArchiveClientRequestDTO, ClientAnalyticsResponseDTO,
    ClientHealthScoreResponseDTO, ContactInfoResponseDTO
)
from app.domain.models.client import Client, ContactInfo
from app.domain.repositories.client_repository import ClientRepository
from app.domain.services.billing_service import BillingService


class CreateClientUseCase(AuthorizedUseCase, CreateUseCase[CreateClientRequestDTO, ClientResponseDTO]):
    """Use case for creating a new client."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_command_logic(self, request: CreateClientRequestDTO) -> ClientResponseDTO:
        # Check for duplicate client name for this user
        existing_client = await self.client_repository.find_by_name_and_owner(
            request.name, self.current_user_id
        )
        if existing_client:
            raise ValueError("Client with this name already exists")
        
        # Create contact info if provided
        contact = None
        if request.contact:
            contact = ContactInfo(
                contact_name=request.contact.contact_name,
                email=request.contact.email,
                phone=request.contact.phone,
                mobile=request.contact.mobile,
                address=request.contact.address,
                city=request.contact.city,
                state=request.contact.state,
                country=request.contact.country,
                postal_code=request.contact.postal_code,
                website=request.contact.website
            )
        
        # Create client
        client = Client.create(
            owner_id=self.current_user_id,
            name=request.name,
            contact=contact,
            tax_id=request.tax_id,
            company_type=request.company_type,
            industry=request.industry,
            default_currency=request.default_currency,
            default_hourly_rate=request.default_hourly_rate,
            payment_terms=request.payment_terms,
            custom_payment_terms=request.custom_payment_terms,
            tags=request.tags,
            notes=request.notes
        )
        
        # Save client
        saved_client = await self.client_repository.save(client)
        
        return self._client_to_response_dto(saved_client)


class UpdateClientUseCase(AuthorizedUseCase, UpdateUseCase[UpdateClientRequestDTO, ClientResponseDTO]):
    """Use case for updating client information."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _check_authorization(self, request: UpdateClientRequestDTO) -> None:
        if hasattr(request, 'id'):
            client = await self.client_repository.find_by_id(request.id)
            if client:
                self._require_owner_or_role(client.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateClientRequestDTO) -> ClientResponseDTO:
        # Get client
        client = await self.client_repository.find_by_id(request.id)
        if not client:
            raise ValueError("Client not found")
        
        # Update fields
        if request.name is not None:
            # Check for duplicate name
            existing = await self.client_repository.find_by_name_and_owner(
                request.name, client.owner_id
            )
            if existing and existing.id != client.id:
                raise ValueError("Client with this name already exists")
            client.name = request.name
        
        if request.contact is not None:
            client.contact = ContactInfo(
                contact_name=request.contact.contact_name,
                email=request.contact.email,
                phone=request.contact.phone,
                mobile=request.contact.mobile,
                address=request.contact.address,
                city=request.contact.city,
                state=request.contact.state,
                country=request.contact.country,
                postal_code=request.contact.postal_code,
                website=request.contact.website
            )
        
        if request.tax_id is not None:
            client.tax_id = request.tax_id
        if request.company_type is not None:
            client.company_type = request.company_type
        if request.industry is not None:
            client.industry = request.industry
        if request.default_currency is not None:
            client.default_currency = request.default_currency
        if request.default_hourly_rate is not None:
            client.default_hourly_rate = request.default_hourly_rate
        if request.payment_terms is not None:
            client.payment_terms = request.payment_terms
        if request.custom_payment_terms is not None:
            client.custom_payment_terms = request.custom_payment_terms
        if request.tags is not None:
            client.tags = request.tags
        if request.notes is not None:
            client.notes = request.notes
        
        # Save client
        saved_client = await self.client_repository.save(client)
        
        return self._client_to_response_dto(saved_client)


class UpdateClientBillingUseCase(AuthorizedUseCase, UpdateUseCase[UpdateClientBillingRequestDTO, ClientResponseDTO]):
    """Use case for updating client billing configuration."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _check_authorization(self, request: UpdateClientBillingRequestDTO) -> None:
        if hasattr(request, 'id'):
            client = await self.client_repository.find_by_id(request.id)
            if client:
                self._require_owner_or_role(client.owner_id, "admin")
    
    async def _execute_command_logic(self, request: UpdateClientBillingRequestDTO) -> ClientResponseDTO:
        # Get client
        client = await self.client_repository.find_by_id(request.id)
        if not client:
            raise ValueError("Client not found")
        
        # Update billing fields
        if request.default_currency is not None:
            client.default_currency = request.default_currency
        if request.default_hourly_rate is not None:
            client.default_hourly_rate = request.default_hourly_rate
        if request.payment_terms is not None:
            client.payment_terms = request.payment_terms
        if request.custom_payment_terms is not None:
            client.custom_payment_terms = request.custom_payment_terms
        
        # Save client
        saved_client = await self.client_repository.save(client)
        
        return self._client_to_response_dto(saved_client)


class GetClientByIdUseCase(AuthorizedUseCase, GetByIdUseCase[int, ClientResponseDTO]):
    """Use case for getting client by ID."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_business_logic(self, client_id: int) -> ClientResponseDTO:
        client = await self.client_repository.find_by_id(client_id)
        if not client:
            raise ValueError("Client not found")
        
        # Check authorization
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Get client stats
        stats = await self.client_repository.get_client_stats(client_id)
        
        response = self._client_to_response_dto(client)
        if stats:
            response.stats = ClientStatsResponseDTO(
                total_projects=stats.total_projects,
                active_projects=stats.active_projects,
                total_invoiced=stats.total_invoiced,
                total_paid=stats.total_paid,
                outstanding_balance=stats.outstanding_balance,
                avg_payment_time_days=stats.avg_payment_time_days,
                last_project_date=stats.last_project_date,
                last_payment_date=stats.last_payment_date
            )
        
        return response


class ListClientsUseCase(AuthorizedUseCase, ListUseCase[ListClientsRequestDTO, ClientSummaryResponseDTO]):
    """Use case for listing clients with filters."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_business_logic(self, request: ListClientsRequestDTO) -> List[ClientSummaryResponseDTO]:
        clients = await self.client_repository.find_with_filters(
            owner_id=self.current_user_id,
            status=request.status,
            payment_terms=request.payment_terms,
            industry=request.industry,
            has_outstanding_balance=request.has_outstanding_balance,
            has_active_projects=request.has_active_projects,
            tags=request.tags,
            search=request.search,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        return [self._client_to_summary_dto(client) for client in clients]


class SearchClientsUseCase(AuthorizedUseCase, SearchUseCase[SearchClientsRequestDTO, ClientSummaryResponseDTO]):
    """Use case for searching clients."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_business_logic(self, request: SearchClientsRequestDTO) -> List[ClientSummaryResponseDTO]:
        clients = await self.client_repository.search_clients(
            owner_id=self.current_user_id,
            query=request.query,
            status=request.status,
            payment_terms=request.payment_terms,
            industry=request.industry,
            page=request.page,
            page_size=request.page_size
        )
        
        return [self._client_to_summary_dto(client) for client in clients]


class DeleteClientUseCase(AuthorizedUseCase, DeleteUseCase[int, bool]):
    """Use case for deleting a client."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_command_logic(self, client_id: int) -> bool:
        # Get client
        client = await self.client_repository.find_by_id(client_id)
        if not client:
            raise ValueError("Client not found")
        
        # Check authorization
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Check if client has active projects
        stats = await self.client_repository.get_client_stats(client_id)
        if stats and stats.active_projects > 0:
            raise ValueError("Cannot delete client with active projects")
        
        # Delete client
        await self.client_repository.delete(client_id)
        
        return True


class ArchiveClientUseCase(AuthorizedUseCase, UpdateUseCase[ArchiveClientRequestDTO, bool]):
    """Use case for archiving a client."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_command_logic(self, request: ArchiveClientRequestDTO) -> bool:
        # Get client
        client = await self.client_repository.find_by_id(request.id)
        if not client:
            raise ValueError("Client not found")
        
        # Check authorization
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Archive client
        client.archive(reason=request.reason)
        
        # Save client
        await self.client_repository.save(client)
        
        return True


class BulkUpdateClientsUseCase(AuthorizedUseCase, BulkUseCase[BulkUpdateClientsRequestDTO, dict]):
    """Use case for bulk updating clients."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_business_logic(self, request: BulkUpdateClientsRequestDTO) -> dict:
        results = {"updated": 0, "errors": []}
        
        for client_id in request.client_ids:
            try:
                # Get client
                client = await self.client_repository.find_by_id(client_id)
                if not client:
                    results["errors"].append({"id": client_id, "error": "Client not found"})
                    continue
                
                # Check authorization
                if client.owner_id != self.current_user_id and "admin" not in self.current_user_roles:
                    results["errors"].append({"id": client_id, "error": "Insufficient permissions"})
                    continue
                
                # Apply updates
                if request.payment_terms is not None:
                    client.payment_terms = request.payment_terms
                if request.status is not None:
                    client.status = request.status
                if request.tags_to_add:
                    client.add_tags(request.tags_to_add)
                if request.tags_to_remove:
                    client.remove_tags(request.tags_to_remove)
                
                # Save client
                await self.client_repository.save(client)
                results["updated"] += 1
                
            except Exception as e:
                results["errors"].append({"id": client_id, "error": str(e)})
        
        return results


class GetClientActivityUseCase(AuthorizedUseCase, GetByIdUseCase[int, List[ClientActivityResponseDTO]]):
    """Use case for getting client activity history."""
    
    def __init__(self, client_repository: ClientRepository):
        super().__init__()
        self.client_repository = client_repository
    
    async def _execute_business_logic(self, client_id: int) -> List[ClientActivityResponseDTO]:
        # Get client
        client = await self.client_repository.find_by_id(client_id)
        if not client:
            raise ValueError("Client not found")
        
        # Check authorization
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Get activity
        activities = await self.client_repository.get_client_activity(client_id)
        
        return [
            ClientActivityResponseDTO(
                date=activity.date,
                activity_type=activity.activity_type,
                description=activity.description,
                project_id=activity.project_id,
                project_name=activity.project_name,
                amount=activity.amount
            )
            for activity in activities
        ]


class GetClientAnalyticsUseCase(AuthorizedUseCase, GetByIdUseCase[int, ClientAnalyticsResponseDTO]):
    """Use case for getting client analytics."""
    
    def __init__(self, client_repository: ClientRepository, billing_service: BillingService):
        super().__init__()
        self.client_repository = client_repository
        self.billing_service = billing_service
    
    async def _execute_business_logic(self, client_id: int) -> ClientAnalyticsResponseDTO:
        # Get client
        client = await self.client_repository.find_by_id(client_id)
        if not client:
            raise ValueError("Client not found")
        
        # Check authorization
        self._require_owner_or_role(client.owner_id, "admin")
        
        # Get analytics data
        analytics = await self.billing_service.get_client_analytics(client_id)
        
        return ClientAnalyticsResponseDTO(
            client_id=client.id,
            client_name=client.name,
            total_revenue=analytics.total_revenue,
            revenue_trend=analytics.revenue_trend,
            avg_project_value=analytics.avg_project_value,
            payment_behavior=analytics.payment_behavior,
            project_count=analytics.project_count,
            project_success_rate=analytics.project_success_rate,
            avg_project_duration=analytics.avg_project_duration,
            total_hours=analytics.total_hours,
            billable_hours=analytics.billable_hours,
            avg_hourly_rate=analytics.avg_hourly_rate,
            relationship_duration_days=analytics.relationship_duration_days,
            last_activity=analytics.last_activity,
            communication_frequency=analytics.communication_frequency
        )


    def _client_to_response_dto(self, client: Client) -> ClientResponseDTO:
        """Convert Client domain model to response DTO."""
        contact = None
        if client.contact:
            contact = ContactInfoResponseDTO(
                contact_name=client.contact.contact_name,
                email=client.contact.email,
                phone=client.contact.phone,
                mobile=client.contact.mobile,
                address=client.contact.address,
                city=client.contact.city,
                state=client.contact.state,
                country=client.contact.country,
                postal_code=client.contact.postal_code,
                website=client.contact.website
            )
        
        return ClientResponseDTO(
            id=client.id,
            owner_id=client.owner_id,
            name=client.name,
            contact=contact,
            tax_id=client.tax_id,
            company_type=client.company_type,
            industry=client.industry,
            default_currency=client.default_currency,
            default_hourly_rate=client.default_hourly_rate,
            payment_terms=client.payment_terms,
            payment_terms_days=client.get_payment_terms_days(),
            display_payment_terms=client.get_display_payment_terms(),
            custom_payment_terms=client.custom_payment_terms,
            status=client.status,
            tags=client.tags,
            notes=client.notes,
            is_active=client.is_active,
            is_archived=client.is_archived,
            has_outstanding_balance=client.has_outstanding_balance,
            can_create_project=client.can_create_project,
            created_at=client.created_at,
            updated_at=client.updated_at
        )
    
    def _client_to_summary_dto(self, client: Client) -> ClientSummaryResponseDTO:
        """Convert Client domain model to summary DTO."""
        return ClientSummaryResponseDTO(
            id=client.id,
            name=client.name,
            status=client.status,
            default_currency=client.default_currency,
            total_projects=0,  # Will be populated by repository query
            active_projects=0,  # Will be populated by repository query
            outstanding_balance=0.0,  # Will be populated by repository query
            last_activity=None,  # Will be populated by repository query
            contact_email=client.contact.email if client.contact else None
        )