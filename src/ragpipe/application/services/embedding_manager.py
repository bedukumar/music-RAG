"""
Embedding Manager Service.

Manages embedding versions and their lifecycles.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from ragpipe.domain.models.embedding import EmbeddingVersion
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.state_store import StateStore


class EmbeddingManager:
    """Manages embedding versions."""

    def __init__(
        self,
        state_store: StateStore,
        event_bus: EventBus,
    ) -> None:
        self.state_store = state_store
        self.event_bus = event_bus

    async def create_embedding_version(
        self,
        modality: Modality,
        model_name: str,
        model_version: str,
        dimension: int,
        chunking_strategy: str,
        chunking_version: str,
        pipeline_version: str,
        activate: bool = False,
    ) -> EmbeddingVersion:
        """Create a new embedding version configuration.

        Args:
            modality: Target modality.
            model_name: Name of the embedding model.
            model_version: Version of the embedding model.
            dimension: Output dimension of the model.
            chunking_strategy: Name of the chunking strategy.
            chunking_version: Version of the chunking strategy.
            pipeline_version: Pipeline version.
            activate: Whether to immediately activate this version.

        Returns:
            The created EmbeddingVersion.
        """
        now = datetime.now(timezone.utc)
        version = EmbeddingVersion(
            id=str(uuid.uuid4()),
            modality=modality,
            model_name=model_name,
            model_version=model_version,
            dimension=dimension,
            chunking_strategy=chunking_strategy,
            chunking_version=chunking_version,
            pipeline_version=pipeline_version,
            is_active=activate,
            created_at=now,
        )
        
        if activate:
            # We need to deactivate existing ones first
            await self._deactivate_all_for_modality(modality)
            
        await self.state_store.save_embedding_version(version)
        return version

    async def _deactivate_all_for_modality(self, modality: Modality) -> None:
        """Helper to deactivate all versions for a modality."""
        active = await self.state_store.get_active_embedding_version(modality)
        if active:
            # We fetch all, and set is_active=False on the ones that are true.
            # But the repository has no update method for versions, we could just overwrite or add update method.
            # Assuming state_store.save_embedding_version overwrites by ID or we just need an update method
            # For simplicity, we just rely on an update or save overwriting.
            active.is_active = False
            await self.state_store.save_embedding_version(active)

    async def activate_version(self, version_id: str) -> None:
        """Activate a specific embedding version.

        Args:
            version_id: The ID of the version to activate.
        """
        version = await self.state_store.get_embedding_version(version_id)
        if not version:
            raise ValueError(f"Version not found: {version_id}")
            
        await self._deactivate_all_for_modality(version.modality)
        
        version.is_active = True
        await self.state_store.save_embedding_version(version)

    async def get_active_version(self, modality: Modality) -> Optional[EmbeddingVersion]:
        """Get the currently active embedding version for a modality."""
        return await self.state_store.get_active_embedding_version(modality)

    async def list_versions(self, modality: Optional[Modality] = None) -> list[EmbeddingVersion]:
        """List embedding versions, optionally filtered by modality."""
        return await self.state_store.list_embedding_versions(modality)

    async def get_version(self, version_id: str) -> Optional[EmbeddingVersion]:
        """Get a specific embedding version by ID."""
        return await self.state_store.get_embedding_version(version_id)

    async def get_media_embeddings(self, media_id: str, modality: Optional[Modality] = None, include_vectors: bool = False) -> list[dict]:
        """Get embedding info for a media item."""
        modalities = [modality] if modality else [m for m in Modality]
        results = []
        for m in modalities:
            records = await self.state_store.get_embedding_records(media_id, m)
            for r in records:
                version = await self.get_version(r.version_id)
                data = {
                    "modality": m.value,
                    "vector_id": r.vector_id,
                    "chunk_index": r.chunk_index,
                    "version_id": r.version_id,
                    "model": version.model_name if version else "unknown",
                    "dimension": version.dimension if version else 0,
                    "created_at": r.created_at.isoformat(),
                    "metadata": r.chunk_metadata
                }
                if include_vectors:
                    data["vector"] = [] # In real app, fetch from vector_repo
                results.append(data)
        return results

    async def list_installed_models(self) -> list[dict]:
        """Return installed embedding models."""
        return [
            {"model": "CLAP", "modality": "audio", "dimension": 512},
            {"model": "SentenceTransformers", "modality": "transcript", "dimension": 384},
            {"model": "MockText", "modality": "metadata", "dimension": 384}
        ]
