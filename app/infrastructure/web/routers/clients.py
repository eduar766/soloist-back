"""
Client management router.
Handles CRUD operations for client resources.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

from app.infrastructure.auth import get_current_user_id
from app.infrastructure.pagination import (
    PaginationParams, SearchParams, smart_paginator, PaginationHelper
)
from app.infrastructure.rate_limiting import create_rate_limit, search_rate_limit
from app.application.use_cases.client_use_cases import (
    CreateClientUseCase,
    UpdateClientUseCase,
    GetClientByIdUseCase,
    ListClientsUseCase,
    ArchiveClientUseCase
)
from app.application.dto.client_dto import (
    CreateClientRequestDTO,
    UpdateClientRequestDTO,
    ClientResponseDTO,
    ClientSummaryResponseDTO
)
from app.infrastructure.db.database import get_db
from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
from app.domain.models.base import EntityNotFoundError, ValidationError


router = APIRouter()


def get_client_repository(session=Depends(get_db)):
    """Dependency to get client repository."""
    return SQLAlchemyClientRepository(session)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ClientResponseDTO)
async def create_client(
    request: CreateClientRequestDTO,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)],
    _: None = Depends(create_rate_limit)
):
    """
    Create a new client.
    
    - **name**: Client name (required)
    - **contact**: Contact information
    - **tax_id**: Optional tax identification number
    - **company_type**: Type of company (SA, SpA, Ltda, etc.)
    - **industry**: Client's industry
    - **notes**: Additional notes
    - **tags**: List of tags
    """
    try:
        use_case = CreateClientUseCase(repository)
        client = await use_case.execute(user_id, request)
        return ClientResponseDTO.from_domain(client)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=dict)
async def list_clients(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)],
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search clients by name"),
    status: Optional[str] = Query(None, description="Filter by client status"),
    company_type: Optional[str] = Query(None, description="Filter by company type"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    sort_by: str = Query("updated_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    List clients with efficient pagination and filtering.
    
    - **page**: Page number (1-based)
    - **page_size**: Number of clients to return (1-100, default 50)
    - **cursor**: Cursor for cursor-based pagination
    - **search**: Search clients by name
    - **status**: Filter by client status (active, inactive, archived)
    - **company_type**: Filter by company type
    - **industry**: Filter by industry
    - **sort_by**: Field to sort by
    - **sort_order**: Sort order (asc/desc)
    """
    try:
        use_case = ListClientsUseCase(repository)
        
        # Build base query
        base_query = repository.get_base_query().filter(
            repository.model.owner_id == user_id
        )
        
        # Apply filters
        filters = {}
        if status:
            filters['status'] = status
        if company_type:
            filters['company_type'] = company_type
        if industry:
            filters['industry'] = industry
        
        # Use smart pagination with search
        if search or filters:
            result = PaginationHelper.create_search_pagination(
                base_query=base_query,
                search_term=search,
                search_fields=['name', 'contact_name', 'email'] if search else None,
                filters=filters,
                page=pagination.page,
                page_size=pagination.page_size
            )
            
            clients = [ClientResponseDTO.from_domain(client) for client in result['items']]
            
            return {
                "clients": clients,
                "pagination": {
                    "page": result['metadata'].page,
                    "page_size": result['metadata'].page_size,
                    "total_items": result['metadata'].total_items,
                    "total_pages": result['metadata'].total_pages,
                    "has_next": result['metadata'].has_next,
                    "has_previous": result['metadata'].has_previous
                },
                "search": result.get('search'),
                "_links": PaginationHelper.get_pagination_links(
                    base_url=str(request.url).split('?')[0],
                    current_page=result['metadata'].page,
                    total_pages=result['metadata'].total_pages,
                    page_size=result['metadata'].page_size,
                    search=search,
                    status=status,
                    company_type=company_type,
                    industry=industry,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
            }
        else:
            # Use smart pagination for simple listing
            result = smart_paginator.paginate(
                query=base_query,
                page=pagination.page,
                page_size=pagination.page_size,
                cursor=pagination.cursor,
                direction=pagination.direction
            )
            
            clients = [ClientResponseDTO.from_domain(client) for client in result['items']]
            
            return {
                "clients": clients,
                "pagination": result['pagination']
            }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{client_id}", response_model=ClientResponseDTO)
async def get_client(
    client_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
):
    """
    Get a specific client by ID.
    
    - **client_id**: Client ID to retrieve
    """
    try:
        use_case = GetClientUseCase(repository)
        client = await use_case.execute(user_id, client_id)
        return ClientResponseDTO.from_domain(client)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )


@router.put("/{client_id}", response_model=ClientResponseDTO)
async def update_client(
    client_id: int,
    request: UpdateClientRequestDTO,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
):
    """
    Update an existing client.
    
    - **client_id**: Client ID to update
    - **name**: Updated client name
    - **contact**: Updated contact information
    - **tax_id**: Updated tax ID
    - **company_type**: Updated company type
    - **industry**: Updated industry
    - **notes**: Updated notes
    - **tags**: Updated tags list
    """
    try:
        use_case = UpdateClientUseCase(repository)
        client = await use_case.execute(user_id, client_id, request)
        return ClientResponseDTO.from_domain(client)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_client(
    client_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)],
    reason: Optional[str] = Query(None, description="Reason for archiving")
):
    """
    Archive (soft delete) a client.
    
    - **client_id**: Client ID to archive
    - **reason**: Optional reason for archiving
    """
    try:
        use_case = ArchiveClientUseCase(repository)
        await use_case.execute(user_id, client_id, reason)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{client_id}/reactivate", response_model=ClientResponseDTO)
async def reactivate_client(
    client_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
):
    """
    Reactivate an archived client.
    
    - **client_id**: Client ID to reactivate
    """
    try:
        # Get the client first
        use_case = GetClientUseCase(repository)
        client = await use_case.execute(user_id, client_id)
        
        # Reactivate it
        client.reactivate()
        
        # Save changes
        repository.save(client)
        
        return ClientResponseDTO.from_domain(client)
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{client_id}/projects")
async def get_client_projects(
    client_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
):
    """
    Get all projects for a specific client.
    
    - **client_id**: Client ID
    """
    try:
        # First verify client exists and user has access
        use_case = GetClientUseCase(repository)
        client = await use_case.execute(user_id, client_id)
        
        # TODO: Implement project retrieval
        # This would require the project repository
        return {
            "client_id": client_id,
            "projects": [],  # Placeholder
            "message": "Project listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )


@router.get("/{client_id}/invoices")
async def get_client_invoices(
    client_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
):
    """
    Get all invoices for a specific client.
    
    - **client_id**: Client ID
    """
    try:
        # First verify client exists and user has access
        use_case = GetClientUseCase(repository)
        client = await use_case.execute(user_id, client_id)
        
        # TODO: Implement invoice retrieval
        # This would require the invoice repository
        return {
            "client_id": client_id,
            "invoices": [],  # Placeholder
            "message": "Invoice listing not yet implemented"
        }
        
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )