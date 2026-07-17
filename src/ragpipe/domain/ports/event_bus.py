"""Event bus port interface for the RAG Data Ingestion Platform.

This module defines the abstract ``EventBus`` contract and the
``EventHandler`` type alias for subscribing to domain events.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from ragpipe.domain.events.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]
"""Type alias for async event handler functions.

An ``EventHandler`` receives a ``DomainEvent`` and returns an awaitable
(coroutine) that resolves to ``None``.
"""


class EventBus(ABC):
    """Abstract interface for publishing and subscribing to domain events.

    Implementations may be in-memory, backed by a message broker (e.g.
    RabbitMQ, Kafka), or use any other pub-sub mechanism.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all registered handlers.

        Args:
            event: The domain event to publish.
        """

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type string to subscribe to (matches
                ``DomainEvent.event_type``).
            handler: The async callable to invoke when a matching event
                is published.
        """

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler.

        Args:
            event_type: The event type string.
            handler: The handler to remove.

        Raises:
            ValueError: If the handler is not registered for the event type.
        """
