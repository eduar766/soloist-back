"""
Domain events related to clients.
Events for client management and updates.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .base import DomainEvent



class ClientRegistered(DomainEvent):
    """Event fired when a new client is registered."""
    
    client_id: int
    user_id: str
    client_name: str
    client_email: Optional[str] = None
    client_type: Optional[str] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "client_name": self.client_name,
            "client_email": self.client_email,
            "client_type": self.client_type
        }



class ClientUpdated(DomainEvent):
    """Event fired when client information is updated."""
    
    client_id: int
    user_id: str
    client_name: str
    updated_fields: Dict[str, Any]
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "client_name": self.client_name,
            "updated_fields": self.updated_fields
        }



class ClientDeactivated(DomainEvent):
    """Event fired when a client is deactivated."""
    
    client_id: int
    user_id: str
    client_name: str
    deactivation_reason: Optional[str] = None
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "client_name": self.client_name,
            "deactivation_reason": self.deactivation_reason
        }