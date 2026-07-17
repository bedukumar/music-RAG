"""Domain models for the RAG Data Ingestion Platform.

Re-exports all model classes, enums, and value objects for convenient access.
"""

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.embedding import EmbeddingRecord, EmbeddingVersion
from ragpipe.domain.models.media import MediaItem, MediaType, Podcast, Song, Video
from ragpipe.domain.models.migration import Migration, MigrationStatus
from ragpipe.domain.models.modality import Modality, ModalityStatus, ProcessingStatus
from ragpipe.domain.models.pipeline import (
    Job,
    PipelineStage,
    PipelineState,
    StageResult,
    StageStatus,
)

__all__ = [
    # media
    "MediaType",
    "MediaItem",
    "Song",
    "Podcast",
    "Video",
    # modality
    "Modality",
    "ModalityStatus",
    "ProcessingStatus",
    # embedding
    "EmbeddingVersion",
    "EmbeddingRecord",
    # chunk
    "ChunkType",
    "Chunk",
    "ChunkingConfig",
    # pipeline
    "PipelineStage",
    "StageStatus",
    "StageResult",
    "PipelineState",
    "Job",
    # migration
    "MigrationStatus",
    "Migration",
]
