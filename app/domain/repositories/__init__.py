"""
Repository interfaces for the domain layer.
This module exports all repository interfaces (ports) for dependency injection.
"""

from .client_repository import ClientRepository
from .project_repository import ProjectRepository
from .task_repository import TaskRepository
from .time_entry_repository import TimeEntryRepository
from .invoice_repository import InvoiceRepository

__all__ = [
    "ClientRepository",
    "ProjectRepository", 
    "TaskRepository",
    "TimeEntryRepository",
    "InvoiceRepository",
]