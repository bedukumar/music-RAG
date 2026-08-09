"""Object storage port interface for the RAG Data Ingestion Platform.

This module defines the abstract ``ObjectStorage`` contract for durable
binary object storage.  Implementations may target local disk (for tests),
AWS S3, or LocalStack.

The dependency direction is:
    Application → ObjectStorage (port)
    Infrastructure → ObjectStorage implementation
    Container → wiring

boto3 is intentionally absent from this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ObjectStorage(ABC):
    """Abstract interface for cloud-style object storage.

    Callers work only with *keys* (path-like strings within a bucket).
    The implementation is responsible for bucket resolution and credentials.
    """

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload binary data under the given key.

        Args:
            key: Object key (path within the bucket).
            data: Raw bytes to store.
            content_type: MIME type hint for the stored object.

        Returns:
            The canonical object key at which data was stored.

        Raises:
            ObjectStorageError: On upload failure.
        """

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download and return the raw bytes of an object.

        Args:
            key: Object key.

        Returns:
            Raw bytes.

        Raises:
            ObjectNotFoundError: If the key does not exist.
            ObjectStorageError: On download failure.
        """

    @abstractmethod
    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Return metadata (head) for an object without downloading it.

        Args:
            key: Object key.

        Returns:
            Dictionary of metadata (e.g. ``content_type``, ``content_length``,
            ``last_modified``).

        Raises:
            ObjectNotFoundError: If the key does not exist.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an object.

        Args:
            key: Object key.

        Returns:
            ``True`` if the object was deleted, ``False`` if it did not exist.
        """

    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiry_seconds: int = 3600,
    ) -> str:
        """Generate a time-limited pre-signed URL for direct client access.

        Args:
            key: Object key.
            expiry_seconds: URL validity in seconds (default 1 hour).

        Returns:
            Pre-signed URL string.
        """


class ObjectStorageError(Exception):
    """Raised when an object storage operation fails at the infrastructure level."""


class ObjectNotFoundError(ObjectStorageError):
    """Raised when a requested object key does not exist."""
