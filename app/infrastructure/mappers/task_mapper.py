"""
Task mapper for converting between domain entities and database models.
"""

import json
from typing import Optional

from app.domain.models.task import Task, TaskStatus, TaskPriority
from app.infrastructure.db.models import TaskModel


class TaskMapper:
    """Maps between Task domain entity and TaskModel database model."""
    
    def domain_to_model(self, task: Task) -> TaskModel:
        """Convert Task domain entity to TaskModel."""
        return TaskModel(
            id=task.id,
            project_id=task.project_id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            priority=task.priority.value,
            assignee_id=task.assignee_id,
            due_date=task.due_date,
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours,
            position=task.position,
            tags=json.dumps(task.tags) if task.tags else "[]",
            is_billable=task.is_billable,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            version=task.version
        )
    
    def model_to_domain(self, model: TaskModel) -> Task:
        """Convert TaskModel to Task domain entity."""
        # Parse tags JSON
        tags = []
        if model.tags:
            try:
                tags = json.loads(model.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        
        task = Task(
            project_id=model.project_id,
            title=model.title,
            description=model.description,
            status=TaskStatus(model.status) if model.status else TaskStatus.TODO,
            priority=TaskPriority(model.priority) if model.priority else TaskPriority.MEDIUM,
            assignee_id=model.assignee_id,
            due_date=model.due_date,
            estimated_hours=model.estimated_hours,
            actual_hours=model.actual_hours or 0.0,
            position=model.position or 0,
            tags=tags,
            is_billable=model.is_billable if model.is_billable is not None else True,
            completed_at=model.completed_at
        )
        
        # Set entity metadata
        task.id = model.id
        task.created_at = model.created_at
        task.updated_at = model.updated_at
        task.version = model.version or 1
        
        return task