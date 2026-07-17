"""Domain events for the RAG Data Ingestion Platform.

This module defines all domain events emitted by the platform. Events follow
an immutable, self-describing pattern: each event class carries a class-level
``EVENT_TYPE`` constant and auto-populates ``event_type`` in ``__post_init__``.

All events inherit from ``DomainEvent`` and can be published via the
``EventBus`` port.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Attributes:
        event_id: Unique event identifier (UUID-4 string).
        event_type: Machine-readable event type string.
        timestamp: When the event occurred (UTC).
        payload: Arbitrary additional data.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Media events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MediaCreated(DomainEvent):
    """Emitted when a new media item is created in the system.

    Attributes:
        media_id: The identifier of the newly created media item.
        media_type: The type of media (song, podcast, video).
    """

    EVENT_TYPE: str = field(default="media.created", init=False, repr=False)

    media_id: str = ""
    media_type: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class AudioUploaded(DomainEvent):
    """Emitted when an audio file is uploaded for a media item.

    Attributes:
        media_id: The associated media item.
        audio_path: Storage path of the uploaded audio file.
        duration: Duration of the audio in seconds.
    """

    EVENT_TYPE: str = field(default="media.audio_uploaded", init=False, repr=False)

    media_id: str = ""
    audio_path: str = ""
    duration: Optional[float] = None

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class TranscriptUploaded(DomainEvent):
    """Emitted when a transcript is uploaded for a media item.

    Attributes:
        media_id: The associated media item.
        transcript_length: Character length of the transcript.
    """

    EVENT_TYPE: str = field(default="media.transcript_uploaded", init=False, repr=False)

    media_id: str = ""
    transcript_length: int = 0

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class MetadataUpdated(DomainEvent):
    """Emitted when metadata fields are updated on a media item.

    Attributes:
        media_id: The associated media item.
        changed_fields: Names of the fields that changed.
    """

    EVENT_TYPE: str = field(default="media.metadata_updated", init=False, repr=False)

    media_id: str = ""
    changed_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Embedding events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingRequested(DomainEvent):
    """Emitted when embedding generation is requested for a media item.

    Attributes:
        media_id: The media item to embed.
        modality: The modality to embed.
        version_id: The embedding version to use.
    """

    EVENT_TYPE: str = field(default="embedding.requested", init=False, repr=False)

    media_id: str = ""
    modality: str = ""
    version_id: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class EmbeddingCompleted(DomainEvent):
    """Emitted when embedding generation completes for a media item.

    Attributes:
        media_id: The media item that was embedded.
        modality: The modality that was embedded.
        version_id: The embedding version used.
        vector_count: Number of vectors produced.
        duration_ms: Time taken in milliseconds.
    """

    EVENT_TYPE: str = field(default="embedding.completed", init=False, repr=False)

    media_id: str = ""
    modality: str = ""
    version_id: str = ""
    vector_count: int = 0
    duration_ms: int = 0

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Chunking events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChunkingCompleted(DomainEvent):
    """Emitted when chunking completes for a media item and modality.

    Attributes:
        media_id: The media item that was chunked.
        modality: The modality that was chunked.
        chunk_count: Number of chunks produced.
        strategy: The chunking strategy used.
    """

    EVENT_TYPE: str = field(default="chunking.completed", init=False, repr=False)

    media_id: str = ""
    modality: str = ""
    chunk_count: int = 0
    strategy: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Migration events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexMigrationStarted(DomainEvent):
    """Emitted when an index migration begins.

    Attributes:
        migration_id: The migration identifier.
        modality: The modality being migrated.
        from_version: Source embedding version.
        to_version: Target embedding version.
    """

    EVENT_TYPE: str = field(
        default="migration.started", init=False, repr=False
    )

    migration_id: str = ""
    modality: str = ""
    from_version: Optional[str] = None
    to_version: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class IndexMigrationFinished(DomainEvent):
    """Emitted when an index migration finishes (success or failure).

    Attributes:
        migration_id: The migration identifier.
        modality: The modality that was migrated.
        status: Terminal status of the migration.
    """

    EVENT_TYPE: str = field(
        default="migration.finished", init=False, repr=False
    )

    migration_id: str = ""
    modality: str = ""
    status: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Vector events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VectorDeleted(DomainEvent):
    """Emitted when vectors are deleted from the vector store.

    Attributes:
        media_id: The media item whose vectors were deleted.
        modality: The modality of the deleted vectors.
        vector_ids: List of deleted vector identifiers.
    """

    EVENT_TYPE: str = field(default="vector.deleted", init=False, repr=False)

    media_id: str = ""
    modality: str = ""
    vector_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class MetadataSynced(DomainEvent):
    """Emitted when metadata is synced to vector payloads.

    Attributes:
        media_id: The media item whose metadata was synced.
        synced_fields: Names of the fields that were synced.
    """

    EVENT_TYPE: str = field(default="metadata.synced", init=False, repr=False)

    media_id: str = ""
    synced_fields: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Pipeline events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PipelineStageCompleted(DomainEvent):
    """Emitted when a pipeline stage completes successfully.

    Attributes:
        media_id: The media item being processed.
        modality: The modality being processed.
        stage: The pipeline stage that completed.
        duration_ms: Time taken in milliseconds.
    """

    EVENT_TYPE: str = field(
        default="pipeline.stage_completed", init=False, repr=False
    )

    media_id: str = ""
    modality: str = ""
    stage: str = ""
    duration_ms: int = 0

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class PipelineFailed(DomainEvent):
    """Emitted when a pipeline fails at a specific stage.

    Attributes:
        media_id: The media item being processed.
        modality: The modality being processed.
        stage: The pipeline stage where failure occurred.
        error: Error description.
    """

    EVENT_TYPE: str = field(default="pipeline.failed", init=False, repr=False)

    media_id: str = ""
    modality: str = ""
    stage: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


# ---------------------------------------------------------------------------
# Job events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JobCreated(DomainEvent):
    """Emitted when a new processing job is created.

    Attributes:
        job_id: The job identifier.
        media_id: The media item to process.
        modality: The target modality.
    """

    EVENT_TYPE: str = field(default="job.created", init=False, repr=False)

    job_id: str = ""
    media_id: str = ""
    modality: str = ""

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class JobRetried(DomainEvent):
    """Emitted when a failed job is retried.

    Attributes:
        job_id: The job identifier.
        retry_count: The new retry count after this retry.
    """

    EVENT_TYPE: str = field(default="job.retried", init=False, repr=False)

    job_id: str = ""
    retry_count: int = 0

    def __post_init__(self) -> None:
        """Auto-populate ``event_type`` from class constant."""
        object.__setattr__(self, "event_type", self.EVENT_TYPE)
