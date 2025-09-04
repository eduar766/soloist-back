"""
Base classes for domain events and event handling.
Provides the foundation for event-driven architecture.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid


logger = logging.getLogger(__name__)


@dataclass
class DomainEvent(ABC):
    """Base class for all domain events."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)
    event_type: str = field(init=False)
    version: int = field(default=1)
    
    def __post_init__(self):
        """Set event type based on class name."""
        if not hasattr(self, 'event_type') or not self.event_type:
            self.event_type = self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self._get_event_data()
        }
    
    @abstractmethod
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data for serialization."""
        pass


class EventHandler(ABC):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        pass
    
    @abstractmethod
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process the given event."""
        pass


class EventDispatcher:
    """Dispatches domain events to registered handlers."""
    
    def __init__(self):
        """Initialize event dispatcher."""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_log: List[Dict[str, Any]] = []
        
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an event handler for specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler {handler.__class__.__name__} for {event_type}")
    
    def register_global_handler(self, handler: EventHandler) -> None:
        """Register a handler that receives all events."""
        self._global_handlers.append(handler)
        logger.info(f"Registered global handler {handler.__class__.__name__}")
    
    async def dispatch(self, event: DomainEvent) -> None:
        """Dispatch event to all registered handlers."""
        try:
            # Log the event
            event_data = event.to_dict()
            self._event_log.append(event_data)
            
            logger.info(f"Dispatching event: {event.event_type} (ID: {event.event_id})")
            
            # Get specific handlers for this event type
            specific_handlers = self._handlers.get(event.event_type, [])
            
            # Combine with global handlers
            all_handlers = specific_handlers + [
                h for h in self._global_handlers 
                if h.can_handle(event)
            ]
            
            if not all_handlers:
                logger.warning(f"No handlers registered for event: {event.event_type}")
                return
            
            # Execute all handlers concurrently
            tasks = []
            for handler in all_handlers:
                tasks.append(self._safe_handle(handler, event))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Successfully dispatched {event.event_type} to {len(all_handlers)} handler(s)")
            
        except Exception as e:
            logger.error(f"Error dispatching event {event.event_type}: {str(e)}")
            raise
    
    async def _safe_handle(self, handler: EventHandler, event: DomainEvent) -> None:
        """Safely execute event handler with error handling."""
        try:
            await handler.handle(event)
            logger.debug(f"Handler {handler.__class__.__name__} processed {event.event_type}")
        except Exception as e:
            logger.error(
                f"Handler {handler.__class__.__name__} failed to process "
                f"{event.event_type}: {str(e)}"
            )
            # Don't re-raise to prevent one handler from affecting others
    
    def get_event_log(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent events from the log."""
        events = sorted(self._event_log, key=lambda x: x['occurred_at'], reverse=True)
        return events[:limit] if limit else events
    
    def clear_event_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()
    
    def get_registered_handlers(self) -> Dict[str, List[str]]:
        """Get information about registered handlers."""
        result = {}
        
        for event_type, handlers in self._handlers.items():
            result[event_type] = [h.__class__.__name__ for h in handlers]
        
        if self._global_handlers:
            result["global"] = [h.__class__.__name__ for h in self._global_handlers]
        
        return result


# Singleton instance
_event_dispatcher = None

def get_event_dispatcher() -> EventDispatcher:
    """Get singleton event dispatcher instance."""
    global _event_dispatcher
    if _event_dispatcher is None:
        _event_dispatcher = EventDispatcher()
    return _event_dispatcher


# Convenience function for dispatching events
async def publish_event(event: DomainEvent) -> None:
    """Publish a domain event."""
    dispatcher = get_event_dispatcher()
    await dispatcher.dispatch(event)