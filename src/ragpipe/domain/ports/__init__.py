"""Port interfaces (ABCs) for the RAG Data Ingestion Platform.

Re-exports all port abstract base classes and type aliases for convenient access.
"""

from ragpipe.domain.ports.bulk_upload_repository import BulkUploadRepository
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
from ragpipe.domain.ports.message_queue import (
    BatchSendEntry,
    BatchSendResult,
    Message,
    MessageQueue,
    MessageQueueError,
)
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.object_storage import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
)
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
    "BulkUploadRepository",
    # state
    "StateStore",
    # event bus
    "EventBus",
    "EventHandler",
    # infrastructure
    "LockManager",
    "FileStorage",
    "MetricsCollector",
    # object storage
    "ObjectStorage",
    "ObjectStorageError",
    "ObjectNotFoundError",
    # message queue
    "MessageQueue",
    "MessageQueueError",
    "Message",
    "BatchSendEntry",
    "BatchSendResult",
]
