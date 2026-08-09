"""Bulk upload repository port interface for the RAG Data Ingestion Platform.

Defines the persistence contract for ``BulkUpload`` and ``BulkUploadRow``
aggregates.  Implementations use SQLAlchemy/SQLite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadRow


class BulkUploadRepository(ABC):
    """Abstract interface for persisting bulk upload records."""

    # ------------------------------------------------------------------
    # BulkUpload CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    async def save(self, bulk_upload: BulkUpload) -> BulkUpload:
        """Persist a new bulk upload record.

        Args:
            bulk_upload: The ``BulkUpload`` aggregate to save.

        Returns:
            The saved ``BulkUpload``.
        """

    @abstractmethod
    async def get(self, bulk_upload_id: str) -> Optional[BulkUpload]:
        """Retrieve a bulk upload by its ID.

        Args:
            bulk_upload_id: The unique bulk upload identifier.

        Returns:
            The ``BulkUpload`` if found, otherwise ``None``.
        """

    @abstractmethod
    async def update(self, bulk_upload: BulkUpload) -> BulkUpload:
        """Persist updates to an existing bulk upload.

        Args:
            bulk_upload: The updated ``BulkUpload`` aggregate.

        Returns:
            The updated ``BulkUpload``.
        """

    @abstractmethod
    async def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BulkUpload], int]:
        """List bulk uploads, optionally filtered by status.

        Args:
            status: Optional status string filter (e.g. ``"PENDING"``).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """

    # ------------------------------------------------------------------
    # BulkUploadRow CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    async def save_row(self, row: BulkUploadRow) -> BulkUploadRow:
        """Persist a bulk upload row record.

        Args:
            row: The ``BulkUploadRow`` to save.

        Returns:
            The saved ``BulkUploadRow``.
        """

    @abstractmethod
    async def get_row(
        self,
        bulk_upload_id: str,
        row_number: int,
    ) -> Optional[BulkUploadRow]:
        """Retrieve a specific row record by its idempotency key.

        The combination of ``(bulk_upload_id, row_number)`` is unique and
        is the canonical idempotency key for bulk upload processing.

        Args:
            bulk_upload_id: Parent bulk upload identifier.
            row_number: 1-indexed row position within the file.

        Returns:
            The ``BulkUploadRow`` if found, otherwise ``None``.
        """

    @abstractmethod
    async def update_row(self, row: BulkUploadRow) -> BulkUploadRow:
        """Persist updates to an existing row record.

        Args:
            row: The updated ``BulkUploadRow``.

        Returns:
            The updated ``BulkUploadRow``.
        """

    @abstractmethod
    async def list_rows(
        self,
        bulk_upload_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[BulkUploadRow], int]:
        """List rows for a bulk upload.

        Args:
            bulk_upload_id: Parent bulk upload identifier.
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (rows, total_count).
        """

    @abstractmethod
    async def count_rows_by_status(
        self,
        bulk_upload_id: str,
    ) -> dict[str, int]:
        """Count rows grouped by status for a given bulk upload.

        Args:
            bulk_upload_id: Parent bulk upload identifier.

        Returns:
            Mapping of status string → count.
        """
