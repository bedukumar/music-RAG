"""SQS Message Queue adapter for the RAG Data Ingestion Platform.

Implements the ``MessageQueue`` port using AWS SQS (or LocalStack).  All
boto3 calls are wrapped in ``asyncio.get_event_loop().run_in_executor`` so
they do not block the async event loop.

Configuration (environment variables):

    SQS_QUEUE_URL           Full SQS queue URL (required)
    SQS_DLQ_URL             Dead-letter queue URL (optional — for inspection only)
    SQS_ENDPOINT_URL        Custom endpoint URL (LocalStack only — leave unset for AWS)
    SQS_VISIBILITY_TIMEOUT  Seconds a message stays invisible after receive (default 300)
    SQS_WAIT_TIME_SECONDS   Long-poll wait time in seconds (default 20)

Delivery semantics:
- SQS provides at-least-once delivery.  Workers must be idempotent.
- Messages are NOT deleted automatically — callers must call ``delete_message``
  after durably persisting the work.
- ``change_visibility`` is available so workers can heartbeat on long runs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Optional

import structlog

from ragpipe.domain.ports.message_queue import (
    BatchSendEntry,
    BatchSendResult,
    Message,
    MessageQueue,
    MessageQueueError,
)

logger = structlog.get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sqs-io")


class SQSMessageQueue(MessageQueue):
    """AWS SQS / LocalStack implementation of the ``MessageQueue`` port.

    Args:
        queue_url: Full SQS queue URL.
        region: AWS region.
        endpoint_url: Optional custom SQS endpoint (for LocalStack).
        aws_access_key_id: AWS access key.  ``None`` → use IAM role.
        aws_secret_access_key: AWS secret key.  ``None`` → use IAM role.
        visibility_timeout: Seconds message stays invisible after receive.
        wait_time_seconds: Long-poll wait time.
    """

    def __init__(
        self,
        queue_url: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        visibility_timeout: int = 300,
        wait_time_seconds: int = 20,
    ) -> None:
        self._queue_url = queue_url
        self._visibility_timeout = visibility_timeout
        self._wait_time_seconds = wait_time_seconds
        self._client = self._build_client(
            region, endpoint_url, aws_access_key_id, aws_secret_access_key
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def send_message(
        self,
        body: dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Publish a single JSON message to the queue."""
        log = logger.bind(queue=self._queue_url)
        try:
            resp = await self._run(
                self._client.send_message,
                QueueUrl=self._queue_url,
                MessageBody=json.dumps(body),
                DelaySeconds=delay_seconds,
            )
            message_id: str = resp["MessageId"]
            log.info("sqs_send_success", message_id=message_id)
            return message_id
        except Exception as exc:
            log.error("sqs_send_failed", error=str(exc))
            raise MessageQueueError(f"SQS send_message failed: {exc}") from exc

    async def send_message_batch(
        self,
        entries: list[BatchSendEntry],
    ) -> BatchSendResult:
        """Send up to 10 messages in one SQS batch call."""
        if len(entries) > 10:
            raise ValueError(
                f"SQS SendMessageBatch allows max 10 entries; got {len(entries)}"
            )

        sqs_entries = [
            {
                "Id": e.id,
                "MessageBody": json.dumps(e.body),
                "DelaySeconds": e.delay_seconds,
            }
            for e in entries
        ]

        try:
            resp = await self._run(
                self._client.send_message_batch,
                QueueUrl=self._queue_url,
                Entries=sqs_entries,
            )
        except Exception as exc:
            raise MessageQueueError(f"SQS send_message_batch failed: {exc}") from exc

        successful = [r["Id"] for r in resp.get("Successful", [])]
        failed = {
            r["Id"]: r.get("Message", "Unknown error")
            for r in resp.get("Failed", [])
        }
        logger.info(
            "sqs_batch_send",
            successful=len(successful),
            failed=len(failed),
        )
        return BatchSendResult(successful=successful, failed=failed)

    async def receive_messages(
        self,
        max_messages: int = 1,
        wait_seconds: int = 20,
    ) -> list[Message]:
        """Receive messages via long-polling."""
        if max_messages < 1 or max_messages > 10:
            raise ValueError("max_messages must be between 1 and 10")

        try:
            resp = await self._run(
                self._client.receive_message,
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds,
                VisibilityTimeout=self._visibility_timeout,
                AttributeNames=["ApproximateReceiveCount"],
            )
        except Exception as exc:
            raise MessageQueueError(f"SQS receive_message failed: {exc}") from exc

        messages = []
        for raw in resp.get("Messages", []):
            try:
                body = json.loads(raw["Body"])
            except (json.JSONDecodeError, KeyError):
                body = {"raw": raw.get("Body", "")}

            attrs = raw.get("Attributes", {})
            receive_count = int(attrs.get("ApproximateReceiveCount", 1))
            messages.append(
                Message(
                    message_id=raw["MessageId"],
                    receipt_handle=raw["ReceiptHandle"],
                    body=body,
                    receive_count=receive_count,
                    attributes=attrs,
                )
            )

        logger.debug("sqs_received", count=len(messages))
        return messages

    async def delete_message(self, receipt_handle: str) -> None:
        """Permanently remove a message from the queue."""
        try:
            await self._run(
                self._client.delete_message,
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.debug("sqs_deleted", receipt_handle=receipt_handle[:20] + "…")
        except Exception as exc:
            raise MessageQueueError(f"SQS delete_message failed: {exc}") from exc

    async def change_visibility(
        self,
        receipt_handle: str,
        timeout_seconds: int,
    ) -> None:
        """Extend the visibility timeout for an in-flight message."""
        try:
            await self._run(
                self._client.change_message_visibility,
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=timeout_seconds,
            )
        except Exception as exc:
            logger.warning("sqs_visibility_change_failed", error=str(exc))
            # Non-fatal: the message will eventually become visible again

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_client(
        self,
        region: str,
        endpoint_url: Optional[str],
        access_key: Optional[str],
        secret_key: Optional[str],
    ):  # type: ignore[return]
        """Build a boto3 SQS client with optional LocalStack overrides."""
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for SQS support. "
                "Install it with: pip install 'ragpipe[bulk]'"
            ) from exc

        kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key

        return boto3.client("sqs", **kwargs)

    async def _run(self, fn, *args, **kwargs) -> Any:
        """Run a synchronous boto3 call in the dedicated thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, partial(fn, *args, **kwargs))
