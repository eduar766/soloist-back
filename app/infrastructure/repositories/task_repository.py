"""
Task repository implementation using SQLAlchemy.
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.domain.models.task import Task
from app.domain.repositories.task_repository import TaskRepositoryInterface
from app.domain.models.base import EntityNotFoundError
from app.infrastructure.db.models import TaskModel
from app.infrastructure.mappers.task_mapper import TaskMapper


class SQLAlchemyTaskRepository(TaskRepositoryInterface):
    """SQLAlchemy implementation of task repository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = TaskMapper()
    
    def save(self, task: Task) -> Task:
        """Save a task entity."""
        if task.is_new:
            # Create new task
            model = self.mapper.domain_to_model(task)
            self.session.add(model)
        else:
            # Update existing task
            model = self.session.query(TaskModel).filter_by(
                id=task.id
            ).first()
            if not model:
                raise EntityNotFoundError("Task", task.id)
            
            # Update model with new data
            updated_model = self.mapper.domain_to_model(task)
            for attr, value in updated_model.__dict__.items():
                if not attr.startswith('_') and attr != 'id':
                    setattr(model, attr, value)
        
        self.session.flush()
        # Return updated task with ID
        if task.is_new:
            task.id = model.id
        return task
    
    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        model = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter_by(id=task_id).first()
        
        if not model:
            return None
        
        return self.mapper.model_to_domain(model)
    
    def get_by_project(self, project_id: int, limit: Optional[int] = None, offset: int = 0) -> List[Task]:
        """Get tasks by project with optional pagination."""
        query = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter_by(project_id=project_id).order_by(TaskModel.position)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_assignee(self, assignee_id: str, limit: Optional[int] = None) -> List[Task]:
        """Get tasks assigned to user."""
        query = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter_by(assignee_id=assignee_id)
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_by_owner(self, owner_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Task]:
        """Get tasks by owner (through project)."""
        query = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).join(TaskModel.project).filter(
            TaskModel.project.has(owner_id=owner_id)
        )
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def delete(self, task_id: int) -> bool:
        """Delete task by ID."""
        model = self.session.query(TaskModel).filter_by(
            id=task_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        return True
    
    def count_by_project(self, project_id: int) -> int:
        """Get task count for project."""
        return self.session.query(func.count(TaskModel.id)).filter_by(
            project_id=project_id
        ).scalar()
    
    def get_by_status(self, project_id: int, status: str) -> List[Task]:
        """Get tasks by status."""
        models = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter_by(
            project_id=project_id,
            status=status
        ).order_by(TaskModel.position).all()
        
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_overdue_tasks(self, assignee_id: Optional[str] = None) -> List[Task]:
        """Get overdue tasks."""
        from datetime import datetime
        
        query = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter(
            and_(
                TaskModel.due_date < datetime.utcnow(),
                TaskModel.status != 'completed'
            )
        )
        
        if assignee_id:
            query = query.filter_by(assignee_id=assignee_id)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def search_by_title(self, project_id: int, title_query: str, limit: Optional[int] = None) -> List[Task]:
        """Search tasks by title."""
        query = self.session.query(TaskModel).options(
            joinedload(TaskModel.project)
        ).filter(
            TaskModel.project_id == project_id,
            TaskModel.title.ilike(f'%{title_query}%')
        )
        
        if limit:
            query = query.limit(limit)
        
        models = query.all()
        return [self.mapper.model_to_domain(model) for model in models]
    
    def get_next_position(self, project_id: int) -> int:
        """Get next position for task in project."""
        max_position = self.session.query(func.max(TaskModel.position)).filter_by(
            project_id=project_id
        ).scalar()
        
        return (max_position or 0) + 1
    
    def reorder_tasks(self, project_id: int, task_positions: List[tuple]) -> None:
        """Reorder tasks in project. task_positions is list of (task_id, new_position)."""
        for task_id, position in task_positions:
            self.session.query(TaskModel).filter_by(
                id=task_id,
                project_id=project_id
            ).update({"position": position})