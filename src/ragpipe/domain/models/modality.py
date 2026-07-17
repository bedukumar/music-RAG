"""Modality domain models for the RAG Data Ingestion Platform.

This module defines the supported content modalities and the status tracking
structures that record whether each modality's data is available, its
embedding state, and any processing errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Modality(Enum):
    """Content modality types supported by the platform.

    Each media item can produce data across one or more modalities. Embeddings
    and processing pipelines are modality-specific.
    """

    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    METADATA = "metadata"


class ProcessingStatus(Enum):
    """Status of a processing operation.

    Used across pipeline stages, embedding generation, and migration
    operations to indicate progress.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ModalityStatus:
    """Tracks the processing state of a single modality for a media item.

    Immutable value object — create a new instance via ``dataclasses.replace``
    to reflect state changes.

    Attributes:
        media_id: The parent media item identifier.
        modality: Which modality this status applies to.
        data_available: Whether raw data for this modality has been uploaded.
        embedding_status: Current embedding state string.
        embedding_version_id: Active embedding version identifier.
        last_processed: When this modality was last processed.
        error_message: Most recent error, if any.
    """

    media_id: str
    modality: Modality
    data_available: bool = False
    embedding_status: str = "pending"
    embedding_version_id: Optional[str] = None
    last_processed: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        valid_statuses = {"pending", "processing", "completed", "failed", "skipped"}
        if self.embedding_status not in valid_statuses:
            from ragpipe.domain.exceptions import ValidationError

            raise ValidationError(
                "embedding_status",
                f"Must be one of {valid_statuses}, got '{self.embedding_status}'",
            )
