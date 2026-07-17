"""Media repository port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for persisting and querying
``MediaItem`` entities and their associated ``ModalityStatus`` records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ragpipe.domain.models.media import MediaItem, MediaType
from ragpipe.domain.models.modality import Modality, ModalityStatus


class MediaRepository(ABC):
    """Abstract interface for media item persistence.

    Implementations may use any storage backend (PostgreSQL, SQLite, etc.).
    """

    # ------------------------------------------------------------------
    # Media CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    def save(self, media: MediaItem) -> None:
        """Persist a new media item.

        Args:
            media: The media item to save.

        Raises:
            DuplicateMediaError: If a media item with the same id exists.
        """

    @abstractmethod
    def get(self, media_id: str) -> Optional[MediaItem]:
        """Retrieve a media item by its identifier.

        Args:
            media_id: The unique media item identifier.

        Returns:
            The ``MediaItem`` if found, otherwise ``None``.
        """

    @abstractmethod
    def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        media_type: Optional[MediaType] = None,
        filters: Optional[dict[str, object]] = None,
    ) -> tuple[list[MediaItem], int]:
        """List media items with pagination and optional filtering.

        Args:
            offset: Number of items to skip (0-indexed).
            limit: Maximum number of items to return.
            media_type: Optional filter by media type.
            filters: Optional additional filters (implementation-defined).

        Returns:
            A tuple of ``(items, total_count)`` where ``total_count`` is
            the total number of matching items (before pagination).
        """

    @abstractmethod
    def update(self, media: MediaItem) -> None:
        """Update an existing media item.

        Args:
            media: The updated media item.  The ``id`` field must match
                an existing record.

        Raises:
            MediaNotFoundError: If the media item does not exist.
        """

    @abstractmethod
    def delete(self, media_id: str) -> None:
        """Delete a media item by its identifier.

        Args:
            media_id: The unique media item identifier.

        Raises:
            MediaNotFoundError: If the media item does not exist.
        """

    @abstractmethod
    def exists(self, media_id: str) -> bool:
        """Check whether a media item exists.

        Args:
            media_id: The unique media item identifier.

        Returns:
            ``True`` if the item exists.
        """

    # ------------------------------------------------------------------
    # Modality status
    # ------------------------------------------------------------------

    @abstractmethod
    def get_modality_status(
        self,
        media_id: str,
        modality: Modality,
    ) -> Optional[ModalityStatus]:
        """Retrieve the modality status for a media item.

        Args:
            media_id: The media item identifier.
            modality: The modality to query.

        Returns:
            The ``ModalityStatus`` if found, otherwise ``None``.
        """

    @abstractmethod
    def save_modality_status(self, status: ModalityStatus) -> None:
        """Persist or update a modality status record.

        Args:
            status: The modality status to save.
        """

    @abstractmethod
    def list_modality_statuses(
        self, media_id: str
    ) -> list[ModalityStatus]:
        """List all modality statuses for a media item.

        Args:
            media_id: The media item identifier.

        Returns:
            List of ``ModalityStatus`` records for the item.
        """

    @abstractmethod
    def get_items_needing_processing(
        self,
        modality: Modality,
        limit: int = 100,
    ) -> list[str]:
        """Find media item IDs that need processing for a given modality.

        Returns items where data is available but embeddings are not yet
        completed.

        Args:
            modality: The modality to check.
            limit: Maximum number of IDs to return.

        Returns:
            List of media item identifiers.
        """
