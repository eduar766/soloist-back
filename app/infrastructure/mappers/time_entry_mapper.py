"""
Time entry mapper for converting between domain entities and database models.
"""

import json
from typing import Optional

from app.domain.models.time_entry import TimeEntry, TimeEntryStatus
from app.infrastructure.db.models import TimeEntryModel


class TimeEntryMapper:
    """Maps between TimeEntry domain entity and TimeEntryModel database model."""
    
    def domain_to_model(self, time_entry: TimeEntry) -> TimeEntryModel:
        """Convert TimeEntry domain entity to TimeEntryModel."""
        return TimeEntryModel(
            id=time_entry.id,
            user_id=time_entry.user_id,
            project_id=time_entry.project_id,
            task_id=time_entry.task_id,
            description=time_entry.description,
            started_at=time_entry.started_at,
            ended_at=time_entry.ended_at,
            duration_minutes=time_entry.duration_minutes,
            billable=time_entry.billable,
            hourly_rate=time_entry.hourly_rate,
            status=time_entry.status.value,
            tags=json.dumps(time_entry.tags) if time_entry.tags else "[]",
            invoice_id=time_entry.invoice_id,
            created_at=time_entry.created_at,
            updated_at=time_entry.updated_at,
            version=time_entry.version
        )
    
    def model_to_domain(self, model: TimeEntryModel) -> TimeEntry:
        """Convert TimeEntryModel to TimeEntry domain entity."""
        # Parse tags JSON
        tags = []
        if model.tags:
            try:
                tags = json.loads(model.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        
        time_entry = TimeEntry(
            user_id=model.user_id,
            project_id=model.project_id,
            task_id=model.task_id,
            description=model.description,
            started_at=model.started_at,
            ended_at=model.ended_at,
            duration_minutes=model.duration_minutes,
            billable=model.billable if model.billable is not None else True,
            hourly_rate=model.hourly_rate,
            status=TimeEntryStatus(model.status) if model.status else TimeEntryStatus.DRAFT,
            tags=tags,
            invoice_id=model.invoice_id
        )
        
        # Set entity metadata
        time_entry.id = model.id
        time_entry.created_at = model.created_at
        time_entry.updated_at = model.updated_at
        time_entry.version = model.version or 1
        
        return time_entry