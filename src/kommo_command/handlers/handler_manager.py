"""Handler manager for coordinating Firebase event processing."""

from __future__ import annotations

import logging
from typing import Any, List

from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class HandlerManager:
    """Manager class for coordinating Firebase event handlers."""

    def __init__(self) -> None:
        """Initialize the handler manager."""
        self.handlers: List[BaseHandler] = []
        self.default_handler: BaseHandler | None = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_handler(self, handler: BaseHandler, *, default: bool = False) -> None:
        """
        Register a new handler.

        Args:
            handler: Handler instance to register
            default: Whether this handler should be used as the fallback option
        """
        self.handlers.append(handler)

        if default:
            self.default_handler = handler
            self.logger.info(
                "Registered default handler",
                extra={"handler": handler.__class__.__name__},
            )
        else:
            self.logger.info(
                "Registered handler",
                extra={"handler": handler.__class__.__name__},
            )
    
    def unregister_handler(self, handler: BaseHandler) -> None:
        """
        Unregister a handler.
        
        Args:
            handler: Handler instance to unregister
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
            if self.default_handler is handler:
                self.default_handler = None
            self.logger.info(
                "Unregistered handler",
                extra={"handler": handler.__class__.__name__},
            )
    
    def process_event(self, event_path: str, event_data: Any) -> None:
        """
        Process a Firebase event through registered handlers.
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
        """
        self.logger.debug(f"Processing event at path: {event_path}")
        
        default_handler = self.default_handler
        capable_handlers: List[BaseHandler] = []
        non_default_handlers: List[BaseHandler] = []

        for handler in self.handlers:
            if handler is default_handler:
                continue

            try:
                if handler.can_handle(event_path, event_data):
                    non_default_handlers.append(handler)
            except Exception as e:
                self.logger.error(
                    f"Error checking if {handler.__class__.__name__} can handle event: {e}",
                    exc_info=True
                )

        if default_handler is not None:
            capable_handlers.append(default_handler)

            if not non_default_handlers:
                self.logger.info(
                    "Default handler processing event (no specific handlers matched)",
                    extra={
                        "event_path": event_path,
                        "default_handler": default_handler.__class__.__name__,
                    },
                )

        capable_handlers.extend(non_default_handlers)

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
                'type': str(type(handler)),
                'is_default': handler is self.default_handler,
            }
            for handler in self.handlers
        ]
    
    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        handler_count = len(self.handlers)
        self.handlers.clear()
        self.default_handler = None
        self.logger.info(f"Cleared {handler_count} handler(s)")