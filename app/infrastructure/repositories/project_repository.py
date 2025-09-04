"""
Project repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.domain.models.project import Project
from app.domain.repositories.project_repository import ProjectRepository as ProjectRepositoryInterface
from app.domain.models.base import EntityNotFoundError, DuplicateEntityError
from app.infrastructure.db.models import ProjectModel
from app.infrastructure.mappers.project_mapper import ProjectMapper


class SQLAlchemyProjectRepository(ProjectRepositoryInterface):
    """SQLAlchemy implementation of project repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = ProjectMapper()
    
    def save(self, project: Project) -> Project:
        """Save a project entity."""
        if project.is_new:
            # Check for duplicate name within owner
            existing = self.session.query(ProjectModel).filter_by(
                owner_id=project.owner_id,
                name=project.name
            ).first()
            if existing:
                raise DuplicateEntityError("Project", "name", project.name)
            
            # Create new project
            model = self.mapper.domain_to_model(project)
            self.session.add(model)
        else:
            # Update existing project
            model = self.session.query(ProjectModel).filter_by(
                id=project.id
            ).first()
            if not model:
                raise EntityNotFoundError("Project", project.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(project)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated project with ID
        if project.is_new:
            project.id = model.id
        return project
    
    def get_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        model = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter_by(id=project_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_owner(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Project]:
        """Get projects by owner with optional pagination."""
        query = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter_by(owner_id=owner_id)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_client(self, client_id: int, limit: Optional[int] = None) -> List[Project]:
        """Get projects by client."""
        query = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter_by(client_id=client_id)
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_active_by_owner(self, owner_id: str) -> List[Project]:
        """Get active projects by owner."""
        models = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter_by(
            owner_id=owner_id,
            status='active'
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, project_id: int) -> bool:
        """Delete project by ID."""
        model = self.session.query(ProjectModel).filter_by(
            id=project_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count_by_owner(self, owner_id: str) -> int:
        """Get project count for owner."""
        return self.session.query(func.count(ProjectModel.id)).filter_by(
            owner_id=owner_id
        ).scalar()
    
    def search_by_name(self, owner_id: str, name_query: str, limit: Optional[int] = None) -> List[Project]:
        """Search projects by name."""
        query = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter(
            ProjectModel.owner_id == owner_id,
            ProjectModel.name.ilike(f'%{name_query}%')
        )
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_status(self, owner_id: str, status: str) -> List[Project]:
        """Get projects by status."""
        models = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter_by(
            owner_id=owner_id,
            status=status
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_date_range(self, owner_id: str, start_date, end_date) -> List[Project]:
        """Get projects within date range."""
        models = self.session.query(ProjectModel).options(
            joinedload(ProjectModel.client)
        ).filter(
            ProjectModel.owner_id == owner_id,
            ProjectModel.start_date >= start_date,
            ProjectModel.end_date <= end_date
        ).all()
        
        return [self.mapper.model_to_domain(model) for model in models]