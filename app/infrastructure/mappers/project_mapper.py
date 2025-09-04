"""
Project mapper for converting between domain entities and database models.
"""

import json
from typing import Optional

from app.domain.models.project import Project, ProjectStatus, BillingType
from app.infrastructure.db.models import ProjectModel


class ProjectMapper:
    """Maps between Project domain entity and ProjectModel database model."""
    
    def domain_to_model(self, project: Project) -> ProjectModel:
        """Convert Project domain entity to ProjectModel."""
        return ProjectModel(
            id=project.id,
            owner_id=project.owner_id,
            client_id=project.client_id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            billing_type=project.billing_type.value,
            hourly_rate=project.hourly_rate,
            fixed_budget=project.fixed_budget,
            currency=project.currency,
            start_date=project.start_date,
            end_date=project.end_date,
            estimated_hours=project.estimated_hours,
            notes=project.notes,
            tags=json.dumps(project.tags) if project.tags else "[]",
            is_billable=project.is_billable,
            total_hours=project.total_hours,
            billable_hours=project.billable_hours,
            total_billed=project.total_billed,
            completion_percentage=project.completion_percentage,
            created_at=project.created_at,
            updated_at=project.updated_at,
            version=project.version
        )
    
    def model_to_domain(self, model: ProjectModel) -> Project:
        """Convert ProjectModel to Project domain entity."""
        # Parse tags JSON
        tags = []
        if model.tags:
            try:
                tags = json.loads(model.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        
        project = Project(
            owner_id=model.owner_id,
            client_id=model.client_id,
            name=model.name,
            description=model.description,
            status=ProjectStatus(model.status) if model.status else ProjectStatus.ACTIVE,
            billing_type=BillingType(model.billing_type) if model.billing_type else BillingType.HOURLY,
            hourly_rate=model.hourly_rate,
            fixed_budget=model.fixed_budget,
            currency=model.currency or "USD",
            start_date=model.start_date,
            end_date=model.end_date,
            estimated_hours=model.estimated_hours,
            notes=model.notes,
            tags=tags,
            is_billable=model.is_billable if model.is_billable is not None else True,
            total_hours=model.total_hours or 0.0,
            billable_hours=model.billable_hours or 0.0,
            total_billed=model.total_billed or 0.0,
            completion_percentage=model.completion_percentage or 0.0
        )
        
        # Set entity metadata
        project.id = model.id
        project.created_at = model.created_at
        project.updated_at = model.updated_at
        project.version = model.version or 1
        
        return project