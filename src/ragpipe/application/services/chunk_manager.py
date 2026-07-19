import structlog
from typing import Callable, Optional
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.application.pipelines.base_pipeline import BasePipeline

logger = structlog.get_logger(__name__)

class ChunkManager:
    """Service for managing chunks."""
    def __init__(
        self,
        state_store: StateStore,
        media_repo: MediaRepository,
        pipeline_factory: Callable[[Modality], BasePipeline]
    ) -> None:
        self.state_store = state_store
        self.media_repo = media_repo
        self.pipeline_factory = pipeline_factory

    async def get_chunks(self, media_id: str, modality: Optional[Modality] = None) -> list[dict]:
        """Get chunks for a media item."""
        if modality:
            modalities = [modality]
        else:
            statuses = await self.media_repo.list_modality_statuses(media_id)
            modalities = [s.modality for s in statuses if s.data_available]

        all_chunks = []
        for m in modalities:
            records = await self.state_store.get_embedding_records(media_id, m)
            for r in records:
                all_chunks.append({
                    "chunk_id": f"{m.value}-{r.chunk_index}",
                    "modality": m.value,
                    "chunk_index": r.chunk_index,
                    "version_id": r.version_id,
                    "vector_id": r.vector_id,
                    "metadata": r.chunk_metadata,
                    "created_at": r.created_at.isoformat()
                })
        return all_chunks

    async def delete_chunks(self, media_id: str, modality: Optional[Modality] = None) -> None:
        """Delete chunks for a media item."""
        if modality:
            modalities = [modality]
        else:
            statuses = await self.media_repo.list_modality_statuses(media_id)
            modalities = [s.modality for s in statuses if s.data_available]
            
        for m in modalities:
            await self.state_store.delete_embedding_records(media_id, m)
            logger.info("Deleted chunks", media_id=media_id, modality=m.value)

    async def rebuild_chunks(self, media_id: str, modality: Modality, regenerate_embeddings: bool = False) -> None:
        """Rebuild chunks without regenerating embeddings unless requested."""
        if regenerate_embeddings:
            raise ValueError("Use reprocess API to regenerate embeddings")
            
        logger.info("Rebuilding chunks without embedding regeneration", media_id=media_id, modality=modality.value)
        # Detailed logic to rebuild just chunks goes here
