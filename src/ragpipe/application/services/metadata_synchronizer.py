"""
Metadata Synchronizer Service.

Synchronizes metadata changes to the vector database payloads.
"""

import logging
from typing import Any

from ragpipe.domain.events.events import MetadataSynced, MetadataUpdated
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.vector_repository import VectorRepository

logger = logging.getLogger(__name__)


class MetadataSynchronizer:
    """Synchronizes media metadata with vector database payloads."""

    def __init__(
        self,
        media_repository: MediaRepository,
        vector_repository: VectorRepository,
        state_store: StateStore,
        event_bus: EventBus,
        metrics: MetricsCollector,
    ) -> None:
        self.media_repo = media_repository
        self.vector_repo = vector_repository
        self.state_store = state_store
        self.event_bus = event_bus
        self.metrics = metrics

    async def subscribe_to_events(self) -> None:
        """Subscribe to metadata update events."""
        await self.event_bus.subscribe(MetadataUpdated.EVENT_TYPE, self._on_metadata_updated)

    async def _on_metadata_updated(self, event: MetadataUpdated) -> None:
        """Handle metadata update event."""
        media_id = event.media_id
        try:
            await self.sync_metadata(media_id)
        except Exception as e:
            logger.error("Failed to sync metadata for media %s: %s", media_id, e)

    async def sync_metadata(self, media_id: str) -> None:
        """Synchronize metadata for a single media item.

        Args:
            media_id: The media ID.
        """
        media = await self.media_repo.get(media_id)
        if not media:
            return
            
        # Base payload to apply to all vectors for this media
        payload_base: dict[str, Any] = {
            "media_id": media.id,
            "media_type": media.media_type.value,
        }
        payload_base.update(media.metadata_fields)
        
        # Iterate through all modalities and update vectors
        for modality in Modality:
            records = await self.state_store.get_embedding_records(media_id, modality)
            if not records:
                continue
                
            # Group records by collection (version)
            # In a simplified system we only update the active collection
            active_version = await self.state_store.get_active_embedding_version(modality)
            if not active_version:
                continue
                
            collection_name = f"{modality.value}_{active_version.id}"
            
            updates = []
            for record in records:
                if record.version_id == active_version.id:
                    # Construct specific payload
                    payload = payload_base.copy()
                    payload["chunk_index"] = record.chunk_index
                    # Add chunk-specific metadata back if necessary, we assume it's in vector already
                    # or we can reconstruct from record.chunk_metadata
                    payload.update(record.chunk_metadata)
                    
                    updates.append((record.vector_id, payload))
                    
            if updates:
                await self.vector_repo.batch_update_payload(collection_name, updates)
                self.metrics.increment("metadata_syncs_total", len(updates), tags={"modality": modality.value})
                
        await self.event_bus.publish(MetadataSynced(
            media_id=media_id,
            synced_fields=list(media.metadata_fields.keys()),
        ))

    async def batch_sync(self, media_ids: list[str]) -> dict[str, bool]:
        """Synchronize metadata for multiple media items.

        Args:
            media_ids: List of media IDs.

        Returns:
            Dictionary mapping media_id to success boolean.
        """
        results = {}
        for mid in media_ids:
            try:
                await self.sync_metadata(mid)
                results[mid] = True
            except Exception as e:
                logger.error("Failed batch sync for %s: %s", mid, e)
                results[mid] = False
        return results
