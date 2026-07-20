"""
Dependency Injection Container.

Wires up all the domain, infrastructure, and application components.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ragpipe.application.pipelines.audio_pipeline import AudioPipeline
from ragpipe.application.pipelines.base_pipeline import BasePipeline
from ragpipe.application.pipelines.metadata_pipeline import MetadataPipeline
from ragpipe.application.pipelines.transcript_pipeline import TranscriptPipeline
from ragpipe.application.services.embedding_manager import EmbeddingManager
from ragpipe.application.services.job_manager import JobManager
from ragpipe.application.services.chunk_manager import ChunkManager
from ragpipe.application.services.worker_manager import WorkerManager
from ragpipe.application.services.search_service import SearchService
from ragpipe.application.services.enrichment_service import EnrichmentService
from ragpipe.application.services.duplicate_detector import DuplicateDetector
from ragpipe.application.services.system_manager import SystemManager
from ragpipe.application.services.media_registrar import MediaRegistrar
from ragpipe.application.services.metadata_synchronizer import MetadataSynchronizer
from ragpipe.application.services.recovery_manager import RecoveryManager
from ragpipe.application.services.migration_manager import MigrationManager
from ragpipe.application.services.pipeline_orchestrator import PipelineOrchestrator
from ragpipe.application.services.status_service import StatusService
from ragpipe.domain.models.chunk import ChunkingConfig
from ragpipe.domain.models.embedding import EmbeddingVersion
from ragpipe.domain.models.modality import Modality
from ragpipe.infrastructure.chunkers.audio.fixed_duration import FixedDurationChunker
from ragpipe.infrastructure.chunkers.metadata.field_concatenator import FieldConcatenator
from ragpipe.infrastructure.chunkers.text.sentence_chunker import SentenceChunker
from ragpipe.infrastructure.database.models import Base
from ragpipe.infrastructure.database.media_repository import SQLAlchemyMediaRepository
from ragpipe.infrastructure.database.state_store import SQLAlchemyStateStore
from ragpipe.infrastructure.embedders.clap_embedder import CLAPEmbedder
from ragpipe.infrastructure.embedders.mock_embedder import MockAudioEmbedder, MockTextEmbedder
from ragpipe.infrastructure.embedders.sentence_transformer import SentenceTransformerEmbedder
from ragpipe.infrastructure.events.async_event_bus import AsyncEventBus
from ragpipe.infrastructure.locking.db_lock_manager import DatabaseLockManager
from ragpipe.infrastructure.metrics.prometheus_metrics import PrometheusMetricsCollector
from ragpipe.infrastructure.storage.local_file_storage import LocalFileStorage
from ragpipe.infrastructure.vector.qdrant_repository import QdrantVectorRepository

logger = logging.getLogger(__name__)


class Container:
    """Simple DI Container."""

    def __init__(self, db_url: str, storage_path: str, qdrant_url: str):
        self.db_url = db_url
        self.storage_path = storage_path
        self.qdrant_url = qdrant_url
        
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        
        # Ports
        self.event_bus = AsyncEventBus()
        self.metrics = PrometheusMetricsCollector()
        self.file_storage = LocalFileStorage(storage_path)
        self.vector_repository = QdrantVectorRepository(url=qdrant_url)
        
        # Repositories (will be initialized with session on request or handled via middleware in a real app, 
        # but for simplicity we'll create a single session for the container or factory)
        self.media_repository: Optional[SQLAlchemyMediaRepository] = None
        self.state_store: Optional[SQLAlchemyStateStore] = None
        self.lock_manager: Optional[DatabaseLockManager] = None
        
        # Services
        self.media_registrar: Optional[MediaRegistrar] = None
        self.pipeline_orchestrator: Optional[PipelineOrchestrator] = None
        self.embedding_manager: Optional[EmbeddingManager] = None
        self.migration_manager: Optional[MigrationManager] = None
        self.metadata_synchronizer: Optional[MetadataSynchronizer] = None
        self.status_service: Optional[StatusService] = None
        self.job_manager: Optional[JobManager] = None
        self.chunk_manager: Optional[ChunkManager] = None
        self.worker_manager: Optional[WorkerManager] = None
        self.search_service: Optional[SearchService] = None
        self.enrichment_service: Optional[EnrichmentService] = None
        self.duplicate_detector: Optional[DuplicateDetector] = None
        self.system_manager: Optional[SystemManager] = None
        self.recovery_manager: Optional[RecoveryManager] = None
        
        # Embedders (Lazy init or mock for now)
        self.audio_embedder = MockAudioEmbedder()
        self.text_embedder = MockTextEmbedder(modality=Modality.TRANSCRIPT)
        
        # Chunkers
        self.audio_chunker = FixedDurationChunker()
        self.text_chunker = SentenceChunker()
        self.metadata_chunker = FieldConcatenator()

    async def init_resources(self):
        """Initialize async resources like DB engine."""
        self.engine = create_async_engine(self.db_url, echo=False)
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Use async_scoped_session so that each background task / API request
        # gets its own independent AsyncSession to prevent InvalidRequestError.
        from asyncio import current_task
        from sqlalchemy.ext.asyncio import async_scoped_session
        
        self._shared_session = async_scoped_session(
            self.session_factory, 
            scopefunc=current_task
        )
        
        self.media_repository = SQLAlchemyMediaRepository(self._shared_session)
        self.state_store = SQLAlchemyStateStore(self._shared_session)
        self.lock_manager = DatabaseLockManager(self._shared_session)
        
        # Initialize Mock Qdrant collections so ingestion pipelines don't fail
        import uuid
        for mod in Modality:
            dummy_id = str(uuid.uuid5(uuid.NAMESPACE_OID, mod.value))
            coll_name = f"{mod.value}_{dummy_id}"
            dim = 512 if mod == Modality.AUDIO else 384
            try:
                await self.vector_repository.create_collection(coll_name, dim)
            except Exception as e:
                import logging
                logging.warning(f"Failed to create collection {coll_name}: {e}")
        # Initialize Services
        self.media_registrar = MediaRegistrar(
            self.media_repository, self.state_store, self.event_bus, self.metrics
        )
        
        self.embedding_manager = EmbeddingManager(
            self.state_store, self.event_bus
        )
        
        self.pipeline_orchestrator = PipelineOrchestrator(
            self.media_repository, self.state_store, self.event_bus, self.metrics, self.lock_manager, self._pipeline_factory
        )
        
        self.migration_manager = MigrationManager(
            self.state_store, self.media_repository, self.vector_repository, self.event_bus, self.metrics, self._pipeline_factory
        )
        
        self.metadata_synchronizer = MetadataSynchronizer(
            self.media_repository, self.vector_repository, self.state_store, self.event_bus, self.metrics
        )
        await self.metadata_synchronizer.subscribe_to_events()
        
        self.status_service = StatusService(
            self.state_store, self.media_repository, self.metrics
        )
        
        self.job_manager = JobManager(
            self.state_store, self.event_bus, self.metrics
        )
        
        self.chunk_manager = ChunkManager(
            self.state_store, self.media_repository, self._pipeline_factory
        )
        self.worker_manager = WorkerManager()
        self.search_service = SearchService(
            self.vector_repository, self.media_repository
        )
        self.enrichment_service = EnrichmentService(self.media_repository)
        self.duplicate_detector = DuplicateDetector(self.media_repository, self.vector_repository)
        self.system_manager = SystemManager(self.metrics, self.event_bus)
        
        self.recovery_manager = RecoveryManager(
            self.vector_repository, self.media_repository, self.event_bus
        )
        
        # Hook up the broadcast callback if using AsyncEventBus
        if hasattr(self.event_bus, 'set_broadcast_callback'):
            original_cb = self.event_bus._broadcast_callback if hasattr(self.event_bus, '_broadcast_callback') else None
            def combined_cb(event):
                self.system_manager.log_event(event)
                if original_cb:
                    original_cb(event)
            self.event_bus.set_broadcast_callback(combined_cb)

    def _pipeline_factory(self, modality: Modality) -> BasePipeline:
        """Factory to create the right pipeline based on modality."""
        # Simplified: We should ideally fetch the active EmbeddingVersion from EmbeddingManager here
        # For synchronous factory, we'll just mock a version if not available, or assume it's fetched asynchronously prior.
        # Let's create a dummy version for the factory; in reality, the orchestrator should pass it.
        import uuid
        from datetime import datetime, timezone
        
        dummy_version = EmbeddingVersion(
            id=str(uuid.uuid5(uuid.NAMESPACE_OID, modality.value)), modality=modality, model_name="mock", model_version="1",
            dimension=512 if modality == Modality.AUDIO else 384, chunking_strategy="mock", chunking_version="1", pipeline_version="1",
            is_active=True, created_at=datetime.now(timezone.utc)
        )
        
        if modality == Modality.AUDIO:
            return AudioPipeline(
                self.media_repository, self.state_store, self.vector_repository, self.event_bus,
                self.metrics, self.lock_manager, dummy_version, self.audio_embedder, self.audio_chunker,
                ChunkingConfig("fixed", "1", 30.0, 0.0, {}), self.file_storage
            )
        elif modality == Modality.TRANSCRIPT:
            return TranscriptPipeline(
                self.media_repository, self.state_store, self.vector_repository, self.event_bus,
                self.metrics, self.lock_manager, dummy_version, self.text_embedder, self.text_chunker,
                ChunkingConfig("sentence", "1", 5, 1, {})
            )
        elif modality == Modality.METADATA:
            return MetadataPipeline(
                self.media_repository, self.state_store, self.vector_repository, self.event_bus,
                self.metrics, self.lock_manager, dummy_version, self.text_embedder, self.metadata_chunker,
                ChunkingConfig("field_concat", "1", 1, 0, {"fields": ["title", "artist", "tags"]})
            )
        else:
            raise ValueError(f"Unknown modality: {modality}")

    async def close_resources(self):
        """Cleanup resources."""
        if hasattr(self, '_shared_session'):
            await self._shared_session.close()
        if self.engine:
            await self.engine.dispose()
