"""
Async Event Bus.

In-process asynchronous event bus for domain events.
"""

import asyncio
import logging
from typing import Callable, Optional

from ragpipe.domain.events.events import DomainEvent
from ragpipe.domain.ports.event_bus import EventBus, EventHandler

logger = logging.getLogger(__name__)


class AsyncEventBus(EventBus):
    """In-process async event bus."""

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[str, list[EventHandler]] = {}
        self._broadcast_callback: Optional[Callable[[DomainEvent], None]] = None
        self._lock = asyncio.Lock()

    def set_broadcast_callback(self, callback: Callable[[DomainEvent], None]) -> None:
        """Set a callback to be invoked for all events (e.g., for WebSockets)."""
        self._broadcast_callback = callback

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The domain event to publish.
        """
        event_type = event.event_type
        logger.debug("Publishing event %s", event_type)

        # Notify global broadcast callback if set
        if self._broadcast_callback:
            try:
                self._broadcast_callback(event)
            except Exception as e:
                logger.error("Error in event broadcast callback: %s", e)

        async with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        if not handlers:
            return

        # Execute handlers concurrently
        tasks = []
        for handler in handlers:
            tasks.append(self._execute_handler(handler, event))
            
        await asyncio.gather(*tasks)

    async def _execute_handler(self, handler: EventHandler, event: DomainEvent) -> None:
        """Execute a single handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error("Error executing handler for event %s: %s", event.event_type, e, exc_info=True)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The string event type to subscribe to.
            handler: The async callback function.
        """
        async with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
        logger.debug("Subscribed to event %s", event_type)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: The string event type.
            handler: The async callback function to remove.
        """
        async with self._lock:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
        logger.debug("Unsubscribed from event %s", event_type)
