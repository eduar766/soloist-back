"""
Client repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy import func

from app.domain.models.client import Client
from app.domain.repositories.client_repository import ClientRepository as ClientRepositoryInterface
from app.domain.models.base import EntityNotFoundError, DuplicateEntityError
from app.infrastructure.db.models import ClientModel
from app.infrastructure.mappers.client_mapper import ClientMapper


class SQLAlchemyClientRepository(ClientRepositoryInterface):
    """SQLAlchemy implementation of client repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = ClientMapper()
        self.model = ClientModel
    
    def save(self, client: Client) -> Client:
        """Save a client entity."""
        if client.is_new:
            # Check for duplicate name within owner
            existing = self.session.query(ClientModel).filter_by(
                owner_id=client.owner_id,
                name=client.name
            ).first()
            if existing:
                raise DuplicateEntityError("Client", "name", client.name)
            
            # Create new client
            model = self.mapper.domain_to_model(client)
            self.session.add(model)
        else:
            # Update existing client
            model = self.session.query(ClientModel).filter_by(
                id=client.id
            ).first()
            if not model:
                raise EntityNotFoundError("Client", client.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(client)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated client with ID
        if client.is_new:
            client.id = model.id
        return client
    
    def get_by_id(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        model = self.session.query(ClientModel).filter_by(
            id=client_id
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_owner_and_name(self, owner_id: str, name: str) -> Optional[Client]:
        """Get client by owner and name."""
        model = self.session.query(ClientModel).filter_by(
            owner_id=owner_id,
            name=name
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_owner(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Client]:
        """Get clients by owner with optional pagination."""
        query = self.session.query(ClientModel).filter_by(owner_id=owner_id)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_active_by_owner(self, owner_id: str) -> List[Client]:
        """Get active clients by owner."""
        models = self.session.query(ClientModel).filter_by(
            owner_id=owner_id,
            status='active'
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, client_id: int) -> bool:
        """Delete client by ID."""
        model = self.session.query(ClientModel).filter_by(
            id=client_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count_by_owner(self, owner_id: str) -> int:
        """Get client count for owner."""
        return self.session.query(func.count(ClientModel.id)).filter_by(
            owner_id=owner_id
        ).scalar()
    
    def search_by_name(self, owner_id: str, name_query: str, limit: Optional[int] = None) -> List[Client]:
        """Search clients by name."""
        query = self.session.query(ClientModel).filter(
            ClientModel.owner_id == owner_id,
            ClientModel.name.ilike(f'%{name_query}%')
        )
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_status(self, owner_id: str, status: str) -> List[Client]:
        """Get clients by status."""
        models = self.session.query(ClientModel).filter_by(
            owner_id=owner_id,
            status=status
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_base_query(self) -> Query:
        """Get base query for client model."""
        return self.session.query(ClientModel)
    
    def get_with_projects(self, client_id: int) -> Optional[Client]:
        """Get client with eager-loaded projects to prevent N+1 queries."""
        model = self.session.query(ClientModel).options(
            joinedload(ClientModel.projects)
        ).filter_by(id=client_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_with_invoices(self, client_id: int) -> Optional[Client]:
        """Get client with eager-loaded invoices to prevent N+1 queries."""
        model = self.session.query(ClientModel).options(
            joinedload(ClientModel.invoices)
        ).filter_by(id=client_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_clients_with_relationships(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Client]:
        """Get clients with all relationships eager-loaded to prevent N+1 queries."""
        query = self.session.query(ClientModel).options(
            joinedload(ClientModel.projects),
            joinedload(ClientModel.invoices)
        ).filter_by(owner_id=owner_id)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]