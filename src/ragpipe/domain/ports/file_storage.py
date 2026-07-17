"""File storage port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for binary file storage
(audio files, transcripts, etc.).  Implementations may use local disk,
S3, GCS, or any other object store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class FileStorage(ABC):
    """Abstract interface for binary file storage operations."""

    @abstractmethod
    def save(self, path: str, data: bytes) -> str:
        """Save binary data to the given path.

        Args:
            path: Storage path (relative or absolute depending on
                implementation).
            data: Raw bytes to persist.

        Returns:
            The canonical path at which the data was stored.
        """

    @abstractmethod
    def load(self, path: str) -> bytes:
        """Load binary data from the given path.

        Args:
            path: Storage path.

        Returns:
            Raw bytes of the stored file.

        Raises:
            FileNotFoundError: If the path does not exist.
        """

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file at the given path.

        Args:
            path: Storage path.

        Returns:
            ``True`` if the file was deleted, ``False`` if it did not exist.
        """

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether a file exists at the given path.

        Args:
            path: Storage path.

        Returns:
            ``True`` if the file exists.
        """

    @abstractmethod
    def get_url(self, path: str) -> str:
        """Generate an access URL for a stored file.

        For local storage this may be a ``file://`` URI; for cloud storage
        it may be a pre-signed URL.

        Args:
            path: Storage path.

        Returns:
            Accessible URL string.
        """

    @abstractmethod
    def list_files(self, prefix: str) -> list[str]:
        """List files matching a path prefix.

        Args:
            prefix: Path prefix to match.

        Returns:
            List of matching file paths.
        """
