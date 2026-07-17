"""Domain events for the RAG Data Ingestion Platform.

Re-exports all event classes for convenient access.
"""

from ragpipe.domain.events.events import (
    AudioUploaded,
    ChunkingCompleted,
    DomainEvent,
    EmbeddingCompleted,
    EmbeddingRequested,
    IndexMigrationFinished,
    IndexMigrationStarted,
    JobCreated,
    JobRetried,
    MediaCreated,
    MetadataSynced,
    MetadataUpdated,
    PipelineFailed,
    PipelineStageCompleted,
    TranscriptUploaded,
    VectorDeleted,
)

__all__ = [
    "DomainEvent",
    "MediaCreated",
    "AudioUploaded",
    "TranscriptUploaded",
    "MetadataUpdated",
    "EmbeddingRequested",
    "EmbeddingCompleted",
    "ChunkingCompleted",
    "IndexMigrationStarted",
    "IndexMigrationFinished",
    "VectorDeleted",
    "MetadataSynced",
    "PipelineStageCompleted",
    "PipelineFailed",
    "JobCreated",
    "JobRetried",
]
