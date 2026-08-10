"""Bulk Upload Application Service.

Orchestrates the HTTP-facing bulk upload workflow:

1. Validate the uploaded file type.
2. Save the raw file bytes locally via the ``FileStorage`` port.
3. Create a ``BulkUpload`` database record with status ``PENDING``.
4. Dispatch background processing using ``BulkUploadProcessor``.
5. Return the ``BulkUpload`` to the caller (the HTTP layer returns 202 Accepted).

Allowed file types: ``text/csv``, ``application/vnd.ms-excel``,
``application/vnd.openxmlformats-officedocument.spreadsheetml.sheet``,
``application/csv``, ``text/plain`` (commonly sent for .csv files).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import structlog

from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadStatus
from ragpipe.domain.ports.bulk_upload_repository import BulkUploadRepository
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.file_storage import FileStorage
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.application.services.bulk_upload_processor import BulkUploadProcessor

logger = structlog.get_logger(__name__)

ALLOWED_CONTENT_TYPES = frozenset(
    [
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Some clients send text/plain for .csv files
        "text/plain",
    ]
)

ALLOWED_EXTENSIONS = frozenset([".csv", ".xlsx", ".xls"])


class BulkUploadService:
    """Application service for bulk upload orchestration.

    Dependencies are injected via the ``Container`` — no concrete infrastructure
    classes are referenced here.
    """

    def __init__(
        self,
        file_storage: FileStorage,
        bulk_upload_repository: BulkUploadRepository,
        bulk_upload_processor: BulkUploadProcessor,
        event_bus: EventBus,
        metrics: MetricsCollector,
    ) -> None:
        self._file_storage = file_storage
        self._repo = bulk_upload_repository
        self._processor = bulk_upload_processor
        self._event_bus = event_bus
        self._metrics = metrics

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def create_bulk_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> BulkUpload:
        """Accept a raw file and enqueue it for background processing.

        Args:
            file_bytes: Raw file content (not parsed here).
            original_filename: Original filename from the upload.
            content_type: MIME type declared by the client.

        Returns:
            A ``BulkUpload`` aggregate in ``PENDING`` status.

        Raises:
            ValueError: If the file type is not supported.
        """
        self._validate_file_type(original_filename, content_type)

        log = logger.bind(original_filename=original_filename)

        # 1. Build local path
        import uuid as _uuid
        import os
        batch_id = str(_uuid.uuid4())
        ext = os.path.splitext(original_filename)[1].lower() or ".csv"
        # store locally using FileStorage
        file_path = f"bulk-uploads/{batch_id}/{original_filename}"

        # 2. Save locally
        log.info("bulk_upload_saving", file_path=file_path)
        self._file_storage.save(file_path, file_bytes)
        log.info("bulk_upload_saved", file_path=file_path, bytes=len(file_bytes))

        # 3. Create BulkUpload domain object
        bulk_upload = BulkUpload.create(
            object_key=file_path,
            bucket="local",
            original_filename=original_filename,
        )
        # Override the auto-generated id to match the prefix so they're traceable
        bulk_upload.id = batch_id

        await self._repo.save(bulk_upload)
        log.info("bulk_upload_db_created", bulk_upload_id=bulk_upload.id)

        # 4. Trigger local background processing instead of SQS
        asyncio.create_task(
            self._processor.process_bulk_upload(bulk_upload.id, file_bytes)
        )
        log.info("bulk_upload_task_dispatched", bulk_upload_id=bulk_upload.id)

        self._metrics.increment(
            "bulk_uploads_submitted_total",
            tags={"ext": ext},
        )
        return bulk_upload

    async def get_bulk_upload(self, bulk_upload_id: str) -> Optional[BulkUpload]:
        """Retrieve a bulk upload by its ID.

        Args:
            bulk_upload_id: The bulk upload identifier.

        Returns:
            The ``BulkUpload`` if found, otherwise ``None``.
        """
        return await self._repo.get(bulk_upload_id)

    async def list_bulk_uploads(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BulkUpload], int]:
        """List bulk uploads with optional status filter.

        Args:
            status: Optional status string (e.g. ``"PENDING"``).
            limit: Page size.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        return await self._repo.list(status=status, limit=limit, offset=offset)

    async def cancel_bulk_upload(self, bulk_upload_id: str) -> BulkUpload:
        """Cancel a pending or processing bulk upload.

        Args:
            bulk_upload_id: The bulk upload identifier.

        Returns:
            The updated ``BulkUpload`` in ``CANCELLED`` status.

        Raises:
            ValueError: If not found or already in a terminal state.
        """
        bulk_upload = await self._repo.get(bulk_upload_id)
        if not bulk_upload:
            raise ValueError(f"Bulk upload not found: {bulk_upload_id}")

        terminal = {
            BulkUploadStatus.COMPLETED,
            BulkUploadStatus.COMPLETED_WITH_ERRORS,
            BulkUploadStatus.FAILED,
            BulkUploadStatus.CANCELLED,
        }
        if bulk_upload.status in terminal:
            raise ValueError(
                f"Cannot cancel bulk upload in terminal state: {bulk_upload.status.value}"
            )

        bulk_upload.mark_cancelled()
        await self._repo.update(bulk_upload)
        logger.info("bulk_upload_cancelled", bulk_upload_id=bulk_upload_id)
        return bulk_upload

    async def list_bulk_upload_rows(
        self,
        bulk_upload_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list, int]:
        """List the row-level results for a bulk upload.

        Args:
            bulk_upload_id: Parent bulk upload identifier.
            status: Optional row status filter.
            limit: Page size.
            offset: Pagination offset.

        Returns:
            Tuple of (rows, total_count).
        """
        return await self._repo.list_rows(
            bulk_upload_id=bulk_upload_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_file_type(filename: str, content_type: str) -> None:
        """Raise ValueError if the file type is not supported."""
        import os

        ext = os.path.splitext(filename)[1].lower()
        normalised_ct = content_type.split(";")[0].strip().lower()

        if ext not in ALLOWED_EXTENSIONS and normalised_ct not in ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported file type: extension='{ext}', content_type='{content_type}'. "
                f"Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
            )
