"""
Client management router.
Handles CRUD operations for client resources.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.infrastructure.auth import get_current_user_id
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
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)]
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
    user_id: Annotated[str, Depends(get_current_user_id)],
    repository: Annotated[SQLAlchemyClientRepository, Depends(get_client_repository)],
    limit: int = Query(50, ge=1, le=100, description="Number of clients to return"),
    offset: int = Query(0, ge=0, description="Number of clients to skip"),
    status: Optional[str] = Query(None, description="Filter by client status"),
    search: Optional[str] = Query(None, description="Search clients by name")
):
    """
    List clients for the authenticated user.
    
    - **limit**: Maximum number of clients to return (1-100, default 50)
    - **offset**: Number of clients to skip for pagination
    - **status**: Filter by client status (active, inactive, archived)
    - **search**: Search clients by name
    """
    try:
        use_case = ListClientsUseCase(repository)
        
        if search:
            clients = await use_case.search_by_name(user_id, search, limit)
            total = len(clients)  # Simplified - in production you'd get actual count
        elif status:
            clients = await use_case.list_by_status(user_id, status)
            total = len(clients)
        else:
            clients = await use_case.execute(user_id, limit, offset)
            total = await use_case.get_total_count(user_id)
        
        return dict(
            clients=[ClientResponseDTO.from_domain(client) for client in clients],
            total=total,
            limit=limit,
            offset=offset
        )
        
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