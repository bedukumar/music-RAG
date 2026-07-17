"""Migration domain models for the RAG Data Ingestion Platform.

This module defines the ``Migration`` entity which tracks the progress of
re-indexing operations when the embedding version changes.  Migrations
re-process all items under a given modality from one embedding version to
another.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ragpipe.domain.exceptions import MigrationError, ValidationError
from ragpipe.domain.models.modality import Modality


class MigrationStatus(Enum):
    """Status of an index migration operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Tracks an index migration from one embedding version to another.

    Mutable entity — state transitions are enforced via dedicated methods.

    Attributes:
        id: Unique migration identifier (UUID-4 string).
        modality: The modality being migrated.
        from_version_id: Source embedding version (``None`` for first-time indexing).
        to_version_id: Target embedding version.
        status: Current migration status.
        total_items: Total number of items to migrate.
        processed_items: Number of items successfully processed.
        failed_items: Number of items that failed processing.
        started_at: When the migration was started.
        completed_at: When the migration finished.
        error_message: Error details on failure.
    """

    id: str
    modality: Modality
    from_version_id: Optional[str]
    to_version_id: str
    status: MigrationStatus = MigrationStatus.PENDING
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "Migration id must not be empty")
        if not self.to_version_id:
            raise ValidationError(
                "to_version_id", "to_version_id must not be empty"
            )
        if self.total_items < 0:
            raise ValidationError(
                "total_items",
                f"total_items must be non-negative, got {self.total_items}",
            )

    @property
    def progress(self) -> float:
        """Return migration progress as a float between 0.0 and 1.0.

        Returns:
            Progress ratio.  Returns 0.0 when ``total_items`` is zero.
        """
        if self.total_items <= 0:
            return 0.0
        return min(
            (self.processed_items + self.failed_items) / self.total_items, 1.0
        )

    @property
    def is_complete(self) -> bool:
        """Check whether the migration has finished (successfully or not).

        Returns:
            ``True`` if status is ``COMPLETED``, ``FAILED``, or ``ROLLED_BACK``.
        """
        return self.status in (
            MigrationStatus.COMPLETED,
            MigrationStatus.FAILED,
            MigrationStatus.ROLLED_BACK,
        )

    def start(self) -> None:
        """Transition the migration to ``RUNNING`` status.

        Raises:
            MigrationError: If the migration is not in ``PENDING`` status.
        """
        if self.status != MigrationStatus.PENDING:
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot start migration in status {self.status.value}",
            )
        self.status = MigrationStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def advance(self, count: int = 1) -> None:
        """Record successful processing of one or more items.

        Args:
            count: Number of items processed in this batch.

        Raises:
            MigrationError: If the migration is not currently running.
            ValidationError: If count is not positive.
        """
        if self.status != MigrationStatus.RUNNING:
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot advance migration in status {self.status.value}",
            )
        if count <= 0:
            raise ValidationError(
                "count", f"Advance count must be positive, got {count}"
            )
        self.processed_items += count

    def record_failure(self, count: int = 1) -> None:
        """Record failed processing of one or more items.

        Unlike ``fail()``, this does not terminate the migration.

        Args:
            count: Number of items that failed in this batch.

        Raises:
            MigrationError: If the migration is not currently running.
            ValidationError: If count is not positive.
        """
        if self.status != MigrationStatus.RUNNING:
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot record failure in status {self.status.value}",
            )
        if count <= 0:
            raise ValidationError(
                "count", f"Failure count must be positive, got {count}"
            )
        self.failed_items += count

    def fail(self, error: str) -> None:
        """Mark the entire migration as failed.

        Args:
            error: Human-readable error description.

        Raises:
            MigrationError: If the migration is not currently running.
        """
        if self.status != MigrationStatus.RUNNING:
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot fail migration in status {self.status.value}",
            )
        self.status = MigrationStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error

    def complete(self) -> None:
        """Mark the migration as successfully completed.

        Raises:
            MigrationError: If the migration is not currently running.
        """
        if self.status != MigrationStatus.RUNNING:
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot complete migration in status {self.status.value}",
            )
        self.status = MigrationStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def rollback(self) -> None:
        """Mark the migration as rolled back.

        Rollback is allowed from ``RUNNING`` or ``FAILED`` status.

        Raises:
            MigrationError: If the migration cannot be rolled back from its
                current status.
        """
        if self.status not in (MigrationStatus.RUNNING, MigrationStatus.FAILED):
            raise MigrationError(
                migration_id=self.id,
                details=f"Cannot rollback migration in status {self.status.value}",
            )
        self.status = MigrationStatus.ROLLED_BACK
        self.completed_at = datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        modality: Modality,
        to_version_id: str,
        total_items: int,
        from_version_id: Optional[str] = None,
    ) -> Migration:
        """Factory method to create a new ``Migration`` with a generated UUID.

        Args:
            modality: The modality being migrated.
            to_version_id: Target embedding version identifier.
            total_items: Total number of items to migrate.
            from_version_id: Source embedding version (``None`` for initial).

        Returns:
            A new ``Migration`` in ``PENDING`` status.
        """
        return cls(
            id=str(uuid.uuid4()),
            modality=modality,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            status=MigrationStatus.PENDING,
            total_items=total_items,
        )
