"""
Time entry repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc

from app.domain.models.time_entry import TimeEntry
from app.domain.repositories.time_entry_repository import TimeEntryRepository as TimeEntryRepositoryInterface
from app.domain.models.base import EntityNotFoundError
from app.infrastructure.db.models import TimeEntryModel
from app.infrastructure.mappers.time_entry_mapper import TimeEntryMapper


class SQLAlchemyTimeEntryRepository(TimeEntryRepositoryInterface):
    """SQLAlchemy implementation of time entry repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = TimeEntryMapper()
        self.model = TimeEntryModel
    
    def save(self, time_entry: TimeEntry) -> TimeEntry:
        """Save a time entry entity."""
        if time_entry.is_new:
            # Create new time entry
            model = self.mapper.domain_to_model(time_entry)
            self.session.add(model)
        else:
            # Update existing time entry
            model = self.session.query(TimeEntryModel).filter_by(
                id=time_entry.id
            ).first()
            if not model:
                raise EntityNotFoundError("TimeEntry", time_entry.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(time_entry)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated time entry with ID
        if time_entry.is_new:
            time_entry.id = model.id
        return time_entry
    
    def get_by_id(self, entry_id: int) -> Optional[TimeEntry]:
        """Get time entry by ID."""
        model = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter_by(id=entry_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_user(self, user_id: str, limit: Optional[int] = None, offset: int = 0) -> List[TimeEntry]:
        """Get time entries by user with optional pagination."""
        query = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter_by(user_id=user_id).order_by(desc(TimeEntryModel.started_at))
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_project(self, project_id: int, limit: Optional[int] = None) -> List[TimeEntry]:
        """Get time entries by project."""
        query = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter_by(project_id=project_id).order_by(desc(TimeEntryModel.started_at))
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_task(self, task_id: int) -> List[TimeEntry]:
        """Get time entries by task."""
        models = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter_by(task_id=task_id).order_by(desc(TimeEntryModel.started_at)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_running_entry(self, user_id: str) -> Optional[TimeEntry]:
        """Get currently running time entry for user."""
        model = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter(
            and_(
                TimeEntryModel.user_id == user_id,
                TimeEntryModel.ended_at.is_(None)
            )
        ).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def delete(self, entry_id: int) -> bool:
        """Delete time entry by ID."""
        model = self.session.query(TimeEntryModel).filter_by(
            id=entry_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def get_by_date_range(
        self, 
        user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[TimeEntry]:
        """Get time entries within date range."""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        models = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter(
            and_(
                TimeEntryModel.user_id == user_id,
                TimeEntryModel.started_at >= start_datetime,
                TimeEntryModel.started_at <= end_datetime
            )
        ).order_by(desc(TimeEntryModel.started_at)).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_billable_entries(
        self, 
        project_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[TimeEntry]:
        """Get billable time entries for project."""
        query = self.session.query(TimeEntryModel).options(
            joinedload(TimeEntryModel.project),
            joinedload(TimeEntryModel.task)
        ).filter(
            and_(
                TimeEntryModel.project_id == project_id,
                TimeEntryModel.billable == True,
                TimeEntryModel.status != 'invoiced'
            )
        )
        
        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            query = query.filter(TimeEntryModel.started_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            query = query.filter(TimeEntryModel.started_at <= end_datetime)
        
        models = query.order_by(desc(TimeEntryModel.started_at)).all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_total_hours_by_project(self, project_id: int) -> float:
        """Get total hours tracked for project."""
        result = self.session.query(func.sum(TimeEntryModel.duration_minutes)).filter(
            and_(
                TimeEntryModel.project_id == project_id,
                TimeEntryModel.ended_at.is_not(None)
            )
        ).scalar()
        
        return (result or 0) / 60.0  # Convert minutes to hours
    
    def get_total_hours_by_user(self, user_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> float:
        """Get total hours tracked by user."""
        query = self.session.query(func.sum(TimeEntryModel.duration_minutes)).filter(
            and_(
                TimeEntryModel.user_id == user_id,
                TimeEntryModel.ended_at.is_not(None)
            )
        )
        
        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            query = query.filter(TimeEntryModel.started_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
            query = query.filter(TimeEntryModel.started_at <= end_datetime)
        
        result = query.scalar()
        return (result or 0) / 60.0  # Convert minutes to hours
    
    def get_base_query(self):
        """Get base query for time entry model."""
        return self.session.query(TimeEntryModel)