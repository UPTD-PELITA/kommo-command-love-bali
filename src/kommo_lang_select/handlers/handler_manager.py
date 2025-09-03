"""Handler manager for coordinating Firebase event processing."""

from __future__ import annotations

import logging
from typing import Any, List

from .base_handler import BaseHandler
from ..services import FirebaseAdminListener

logger = logging.getLogger(__name__)


class HandlerManager:
    """Manager class for coordinating Firebase event handlers."""
    
    def __init__(self) -> None:
        """Initialize the handler manager."""
        self.handlers: List[BaseHandler] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def register_handler(self, handler: BaseHandler) -> None:
        """
        Register a new handler.
        
        Args:
            handler: Handler instance to register
        """
        self.handlers.append(handler)
        self.logger.info(f"Registered handler: {handler.__class__.__name__}")
    
    def unregister_handler(self, handler: BaseHandler) -> None:
        """
        Unregister a handler.
        
        Args:
            handler: Handler instance to unregister
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            self.logger.info(f"Unregistered handler: {handler.__class__.__name__}")
    
    def process_event(self, event_path: str, event_data: Any) -> None:
        """
        Process a Firebase event through registered handlers.
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
        """
        self.logger.debug(f"Processing event at path: {event_path}")
        
        # Find handlers that can process this event
        capable_handlers = []
        for handler in self.handlers:
            try:
                if handler.can_handle(event_path, event_data):
                    capable_handlers.append(handler)
            except Exception as e:
                self.logger.error(
                    f"Error checking if {handler.__class__.__name__} can handle event: {e}",
                    exc_info=True
                )
        
        if not capable_handlers:
            self.logger.debug(f"No handlers found for event at path: {event_path}")
            return
        
        self.logger.info(
            f"Found {len(capable_handlers)} handler(s) for event at path: {event_path}",
            extra={
                'handlers': [h.__class__.__name__ for h in capable_handlers],
                'event_path': event_path
            }
        )
        
        # Process event with each capable handler
        for handler in capable_handlers:
            try:
                self.logger.debug(f"Processing event with {handler.__class__.__name__}")
                handler.handle(event_path, event_data)
                self.logger.debug(f"Successfully processed event with {handler.__class__.__name__}")
            except Exception as e:
                self.logger.error(
                    f"Error processing event with {handler.__class__.__name__}: {e}",
                    extra={
                        'handler': handler.__class__.__name__,
                        'event_path': event_path,
                        'error': str(e)
                    },
                    exc_info=True
                )
                # Continue with other handlers even if one fails
    
    def get_handler_info(self) -> List[dict]:
        """
        Get information about registered handlers.
        
        Returns:
            List of handler information dictionaries
        """
        return [
            {
                'name': handler.__class__.__name__,
                'module': handler.__class__.__module__,
                'type': str(type(handler))
            }
            for handler in self.handlers
        ]
    
    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        handler_count = len(self.handlers)
        self.handlers.clear()
        self.logger.info(f"Cleared {handler_count} handler(s)")