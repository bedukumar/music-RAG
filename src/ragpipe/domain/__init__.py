"""Domain layer for the RAG Data Ingestion Platform.

This package contains all domain models, enums, events, port interfaces
(ABCs), and custom exceptions.  It has ZERO dependencies on infrastructure
or application layers — only standard library and domain-internal imports.

Key sub-packages:

- ``models`` — dataclasses and enums representing domain entities.
- ``events`` — immutable domain event classes for pub-sub communication.
- ``ports`` — abstract base classes defining infrastructure contracts.
- ``exceptions`` — structured, domain-specific exception hierarchy.
"""

from ragpipe.domain.exceptions import (
    ChunkingError,
    ConfigurationError,
    DuplicateMediaError,
    EmbeddingError,
    InvalidMediaError,
    LockError,
    MediaNotFoundError,
    MigrationError,
    PipelineError,
    RagPipeError,
    ValidationError,
    VectorStoreError,
)
from ragpipe.domain.models import (
    Chunk,
    ChunkingConfig,
    ChunkType,
    EmbeddingRecord,
    EmbeddingVersion,
    Job,
    MediaItem,
    MediaType,
    Migration,
    MigrationStatus,
    Modality,
    ModalityStatus,
    PipelineStage,
    PipelineState,
    Podcast,
    ProcessingStatus,
    Song,
    StageResult,
    StageStatus,
    Video,
)

__all__ = [
    # Models
    "MediaType",
    "MediaItem",
    "Song",
    "Podcast",
    "Video",
    "Modality",
    "ModalityStatus",
    "ProcessingStatus",
    "EmbeddingVersion",
    "EmbeddingRecord",
    "ChunkType",
    "Chunk",
    "ChunkingConfig",
    "PipelineStage",
    "StageStatus",
    "StageResult",
    "PipelineState",
    "Job",
    "MigrationStatus",
    "Migration",
    # Exceptions
    "RagPipeError",
    "MediaNotFoundError",
    "DuplicateMediaError",
    "InvalidMediaError",
    "PipelineError",
    "EmbeddingError",
    "ChunkingError",
    "VectorStoreError",
    "MigrationError",
    "LockError",
    "ConfigurationError",
    "ValidationError",
]
