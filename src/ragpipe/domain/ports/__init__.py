"""Port interfaces (ABCs) for the RAG Data Ingestion Platform.

Re-exports all port abstract base classes and type aliases for convenient access.
"""

from ragpipe.domain.ports.chunker import AudioChunker, MetadataChunker, TextChunker
from ragpipe.domain.ports.embedding_provider import (
    AudioEmbeddingProvider,
    EmbeddingProvider,
    TextEmbeddingProvider,
)
from ragpipe.domain.ports.event_bus import EventBus, EventHandler
from ragpipe.domain.ports.file_storage import FileStorage
from ragpipe.domain.ports.lock_manager import LockManager
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.vector_repository import VectorRepository

__all__ = [
    # embedding providers
    "EmbeddingProvider",
    "AudioEmbeddingProvider",
    "TextEmbeddingProvider",
    # chunkers
    "AudioChunker",
    "TextChunker",
    "MetadataChunker",
    # repositories
    "VectorRepository",
    "MediaRepository",
    # state
    "StateStore",
    # event bus
    "EventBus",
    "EventHandler",
    # infrastructure
    "LockManager",
    "FileStorage",
    "MetricsCollector",
]
