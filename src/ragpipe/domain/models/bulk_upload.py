"""Bulk upload domain models for the RAG Data Ingestion Platform.

This module defines the aggregate root ``BulkUpload`` which represents a
single bulk ingestion operation (a CSV/XLSX upload), and the ``BulkUploadRow``
value object which tracks the outcome of each individual row within that batch.

Design principles:
- ``BulkUpload`` is kept completely separate from the per-media ``Job`` entity.
  A single BulkUpload produces many Jobs once its rows are parsed.
- Status transitions are explicit methods that validate the current state.
- Row-level failures never fail the overall batch — they produce
  ``COMPLETED_WITH_ERRORS`` instead of ``FAILED``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class BulkUploadStatus(Enum):
    """Lifecycle status of a bulk upload batch."""

    PENDING = "PENDING"
    """File has been received and SQS message published; worker not yet started."""

    PROCESSING = "PROCESSING"
    """Worker is actively parsing rows and creating media/job records."""

    COMPLETED = "COMPLETED"
    """All rows were successfully processed."""

    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    """Processing finished but one or more rows failed validation or registration."""

    FAILED = "FAILED"
    """An infrastructure-level failure prevented the batch from being processed."""

    CANCELLED = "CANCELLED"
    """Manually cancelled before or during processing."""


class BulkUploadRowStatus(Enum):
    """Status of a single row within a bulk upload."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BulkUpload:
    """Aggregate root representing a single bulk ingestion batch.

    Attributes:
        id: Unique identifier (UUID-4 string).
        object_key: S3 object key where the original file is stored.
        bucket: S3 bucket name.
        original_filename: The filename provided by the uploader.
        status: Current lifecycle status.
        total_rows: Total rows detected after parsing (0 until parse completes).
        processed_rows: Rows where processing has been attempted.
        successful_rows: Rows that produced valid media records.
        failed_rows: Rows that failed validation or registration.
        created_at: When the upload was submitted.
        started_at: When the worker began processing.
        completed_at: When processing finished (success or failure).
        error_message: Top-level error if ``FAILED`` due to infrastructure.
    """

    id: str
    object_key: str
    bucket: str
    original_filename: str
    status: BulkUploadStatus = BulkUploadStatus.PENDING
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def mark_processing(self) -> None:
        """Transition to PROCESSING status when the worker picks up the job."""
        self.status = BulkUploadStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Transition to terminal COMPLETED or COMPLETED_WITH_ERRORS.

        Picks the correct terminal status based on whether any rows failed.
        """
        if self.failed_rows > 0:
            self.status = BulkUploadStatus.COMPLETED_WITH_ERRORS
        else:
            self.status = BulkUploadStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Transition to FAILED due to an infrastructure-level error."""
        self.status = BulkUploadStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Transition to CANCELLED."""
        self.status = BulkUploadStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def increment_success(self) -> None:
        """Record a successfully processed row."""
        self.processed_rows += 1
        self.successful_rows += 1

    def increment_failure(self) -> None:
        """Record a failed row."""
        self.processed_rows += 1
        self.failed_rows += 1

    @classmethod
    def create(
        cls,
        object_key: str,
        bucket: str,
        original_filename: str,
    ) -> BulkUpload:
        """Factory method to create a new ``BulkUpload`` with a generated UUID.

        Args:
            object_key: S3 key where the file is stored.
            bucket: S3 bucket name.
            original_filename: Original filename from the uploader.

        Returns:
            A new ``BulkUpload`` in ``PENDING`` status.
        """
        return cls(
            id=str(uuid.uuid4()),
            object_key=object_key,
            bucket=bucket,
            original_filename=original_filename,
            status=BulkUploadStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )


@dataclass
class BulkUploadRow:
    """Per-row tracking record for a bulk upload batch.

    This is the idempotency anchor: the combination of ``bulk_upload_id``
    and ``row_number`` is unique and is checked before any work is done on
    a row.  If a record exists with ``status = processed`` the row is safely
    skipped on SQS replay.

    Attributes:
        id: Unique identifier (UUID-4 string).
        bulk_upload_id: Parent bulk upload identifier.
        row_number: 1-indexed row number within the file.
        status: Processing outcome.
        media_id: The media item created from this row, if successful.
        error_type: Short error category on failure (e.g. ``validation_error``).
        error_message: Human-readable error detail.
        raw_data: JSON-safe snapshot of the raw CSV/XLSX row (for diagnostics).
        created_at: When this row record was created.
    """

    id: str
    bulk_upload_id: str
    row_number: int
    status: BulkUploadRowStatus = BulkUploadRowStatus.PENDING
    media_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    raw_data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        bulk_upload_id: str,
        row_number: int,
        raw_data: dict,
    ) -> BulkUploadRow:
        """Factory method to create a new pending row record.

        Args:
            bulk_upload_id: Parent bulk upload identifier.
            row_number: 1-indexed row position.
            raw_data: Raw row data dictionary (CSV headers → values).

        Returns:
            A new ``BulkUploadRow`` in ``PENDING`` status.
        """
        return cls(
            id=str(uuid.uuid4()),
            bulk_upload_id=bulk_upload_id,
            row_number=row_number,
            raw_data=raw_data,
            status=BulkUploadRowStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
