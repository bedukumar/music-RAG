"""Message queue port interface for the RAG Data Ingestion Platform.

This module defines the abstract ``MessageQueue`` contract and the ``Message``
value object.  Implementations may target AWS SQS or LocalStack.

Design decisions:
- Messages carry only identifier/reference information (never large payloads).
- ``send_message_batch`` respects the AWS SQS limit of 10 per batch call.
- Receipt handles are opaque strings — callers must not interpret them.
- ``change_visibility`` is exposed so workers can extend the timeout on
  long-running operations without losing the message.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Message:
    """A single message received from the queue.

    Attributes:
        message_id: Unique message identifier assigned by the broker.
        receipt_handle: Opaque token required to delete or change visibility.
        body: Deserialized JSON payload.
        receive_count: How many times this message has been delivered.
            Values > 1 indicate a replay (e.g. after a visibility timeout).
        attributes: Additional broker-specific attributes.
    """

    message_id: str
    receipt_handle: str
    body: dict[str, Any]
    receive_count: int = 1
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchSendEntry:
    """A single entry for batch message sending.

    Attributes:
        id: Caller-assigned unique ID within the batch (alphanumeric, max 80 chars).
        body: JSON-serialisable payload dict.
        delay_seconds: Per-message delay override (0–900 seconds).
    """

    id: str
    body: dict[str, Any]
    delay_seconds: int = 0


@dataclass(frozen=True)
class BatchSendResult:
    """Result of a batch send operation.

    Attributes:
        successful: IDs of messages successfully enqueued.
        failed: Mapping of ID → error reason for messages that failed.
    """

    successful: list[str]
    failed: dict[str, str]


class MessageQueue(ABC):
    """Abstract interface for durable asynchronous message queuing."""

    @abstractmethod
    async def send_message(
        self,
        body: dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Send a single message to the queue.

        Args:
            body: JSON-serialisable payload.
            delay_seconds: Delivery delay (0–900 seconds).

        Returns:
            The broker-assigned message ID.

        Raises:
            MessageQueueError: On send failure.
        """

    @abstractmethod
    async def send_message_batch(
        self,
        entries: list[BatchSendEntry],
    ) -> BatchSendResult:
        """Send up to 10 messages in a single batch call.

        AWS SQS imposes a hard limit of 10 messages per ``SendMessageBatch``
        call.  Callers are responsible for splitting larger lists.

        Args:
            entries: List of up to 10 ``BatchSendEntry`` items.

        Returns:
            ``BatchSendResult`` listing successes and failures.

        Raises:
            ValueError: If ``entries`` contains more than 10 items.
            MessageQueueError: On infrastructure failure.
        """

    @abstractmethod
    async def receive_messages(
        self,
        max_messages: int = 1,
        wait_seconds: int = 20,
    ) -> list[Message]:
        """Receive messages from the queue (long-polling).

        Messages remain invisible to other consumers until the visibility
        timeout expires or they are deleted.  This is the standard
        at-least-once delivery guarantee.

        Args:
            max_messages: Maximum number of messages to receive (1–10).
            wait_seconds: Long-poll wait time (0–20 seconds).

        Returns:
            List of ``Message`` objects (may be empty).
        """

    @abstractmethod
    async def delete_message(self, receipt_handle: str) -> None:
        """Acknowledge and permanently remove a message from the queue.

        Call this ONLY after the corresponding work has been durably persisted.

        Args:
            receipt_handle: The receipt handle from ``Message.receipt_handle``.

        Raises:
            MessageQueueError: On deletion failure.
        """

    @abstractmethod
    async def change_visibility(
        self,
        receipt_handle: str,
        timeout_seconds: int,
    ) -> None:
        """Extend or reset the visibility timeout for an in-flight message.

        Args:
            receipt_handle: The receipt handle from ``Message.receipt_handle``.
            timeout_seconds: New visibility timeout from *now* (0–43200 seconds).
        """


class MessageQueueError(Exception):
    """Raised when a message queue operation fails at the infrastructure level."""
