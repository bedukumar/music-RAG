"""
Media Registrar Service.

Handles ingestion and updates of media items.
"""

from dataclasses import replace
from typing import Any

from ragpipe.domain.events.events import (
    AudioUploaded,
    MediaCreated,
    MetadataUpdated,
    TranscriptUploaded,
)
from ragpipe.domain.models.media import MediaItem
from ragpipe.domain.models.modality import Modality, ModalityStatus
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.exceptions import MediaNotFoundError


class MediaRegistrar:
    """Service for registering and updating media items."""

    def __init__(
        self,
        media_repository: MediaRepository,
        state_store: StateStore,
        event_bus: EventBus,
        metrics: MetricsCollector,
    ) -> None:
        self.media_repo = media_repository
        self.state_store = state_store
        self.event_bus = event_bus
        self.metrics = metrics

    async def register_media(self, media: MediaItem) -> MediaItem:
        """Register a new media item and set up modality statuses.

        Args:
            media: The new media item.

        Returns:
            The saved media item.
        """
        # Save media
        await self.media_repo.save(media)
        self.metrics.increment("media_registered_total", tags={"type": media.media_type.value})

        # Set up modalities based on provided data
        has_audio = bool(media.audio_path)
        
        has_transcript = False
        if hasattr(media, "transcript_text") and media.transcript_text:
            has_transcript = True
        elif hasattr(media, "lyrics") and media.lyrics:
            has_transcript = True
            
        has_metadata = bool(media.metadata_fields)

        statuses = [
            ModalityStatus(media.id, Modality.AUDIO, has_audio, "pending" if has_audio else "skipped", None, None, None),
            ModalityStatus(media.id, Modality.TRANSCRIPT, has_transcript, "pending" if has_transcript else "skipped", None, None, None),
            ModalityStatus(media.id, Modality.METADATA, has_metadata, "pending" if has_metadata else "skipped", None, None, None),
        ]

        for status in statuses:
            await self.media_repo.save_modality_status(status)

        # Publish event
        await self.event_bus.publish(MediaCreated(
            media_id=media.id,
            media_type=media.media_type.value,
        ))

        return media

    async def register_batch(self, media_items: list[MediaItem]) -> tuple[list[str], dict[str, str]]:
        """Register multiple media items in batch."""
        successful = []
        failed = {}
        try:
            await self.media_repo.save_batch(media_items)
            statuses = []
            for media in media_items:
                has_audio = bool(media.audio_path)
                has_transcript = False
                if hasattr(media, "transcript_text") and media.transcript_text:
                    has_transcript = True
                elif hasattr(media, "lyrics") and media.lyrics:
                    has_transcript = True
                has_metadata = bool(media.metadata_fields)
                statuses.extend([
                    ModalityStatus(media.id, Modality.AUDIO, has_audio, "pending" if has_audio else "skipped", None, None, None),
                    ModalityStatus(media.id, Modality.TRANSCRIPT, has_transcript, "pending" if has_transcript else "skipped", None, None, None),
                    ModalityStatus(media.id, Modality.METADATA, has_metadata, "pending" if has_metadata else "skipped", None, None, None),
                ])
                successful.append(media.id)
                self.metrics.increment("media_registered_total", tags={"type": media.media_type.value})
            for status in statuses:
                await self.media_repo.save_modality_status(status)
            for media in media_items:
                await self.event_bus.publish(MediaCreated(media_id=media.id, media_type=media.media_type.value))
        except Exception as e:
            for media in media_items:
                failed[media.id] = str(e)
            successful = []
        return successful, failed

    async def update_audio(self, media_id: str, audio_path: str, duration: float | None = None) -> None:
        """Update the audio path for a media item.

        Args:
            media_id: The media ID.
            audio_path: New audio path.
            duration: Optional duration in seconds.
        """
        media = await self.media_repo.get(media_id)
        if not media:
            raise MediaNotFoundError(media_id)

        updated_media = replace(media, audio_path=audio_path)
        if duration is not None:
            updated_media = replace(updated_media, duration=duration)

        await self.media_repo.update(updated_media)

        status = await self.media_repo.get_modality_status(media_id, Modality.AUDIO)
        if status:
            updated_status = replace(status, data_available=True, embedding_status="pending")
            await self.media_repo.save_modality_status(updated_status)

        await self.event_bus.publish(AudioUploaded(
            media_id=media_id,
            audio_path=audio_path,
            duration=duration or 0.0,
        ))

    async def update_transcript(self, media_id: str, transcript: str) -> None:
        """Update the transcript for a media item.

        Args:
            media_id: The media ID.
            transcript: New transcript text.
        """
        media = await self.media_repo.get(media_id)
        if not media:
            raise MediaNotFoundError(media_id)

        if hasattr(media, "lyrics"):
            updated_media = replace(media, transcript_text=transcript, lyrics=transcript)
        else:
            updated_media = replace(media, transcript_text=transcript)

        await self.media_repo.update(updated_media)

        status = await self.media_repo.get_modality_status(media_id, Modality.TRANSCRIPT)
        if status:
            updated_status = replace(status, data_available=True, embedding_status="pending")
            await self.media_repo.save_modality_status(updated_status)

        await self.event_bus.publish(TranscriptUploaded(
            media_id=media_id,
            transcript_length=len(transcript),
        ))

    async def update_metadata(self, media_id: str, metadata: dict[str, Any]) -> None:
        """Merge new metadata into existing metadata fields.

        Args:
            media_id: The media ID.
            metadata: New metadata dict.
        """
        media = await self.media_repo.get(media_id)
        if not media:
            raise MediaNotFoundError(media_id)

        new_metadata = dict(media.metadata_fields)
        new_metadata.update(metadata)
        updated_media = replace(media, metadata_fields=new_metadata)
        
        await self.media_repo.update(updated_media)

        status = await self.media_repo.get_modality_status(media_id, Modality.METADATA)
        if status:
            updated_status = replace(status, data_available=True, embedding_status="pending")
            await self.media_repo.save_modality_status(updated_status)

        await self.event_bus.publish(MetadataUpdated(
            media_id=media_id,
            changed_fields=list(metadata.keys()),
        ))

    async def delete_batch(self, media_ids: list[str]) -> tuple[list[str], dict[str, str]]:
        """Delete multiple media items."""
        successful = []
        failed = {}
        try:
            deleted_count = await self.media_repo.delete_batch(media_ids)
            successful = media_ids
            self.metrics.increment("media_deleted_total", deleted_count)
        except Exception as e:
            for m_id in media_ids:
                failed[m_id] = str(e)
        return successful, failed

    async def delete_media(self, media_id: str) -> None:
        """Delete a media item completely.

        Args:
            media_id: The media ID.
        """
        if not await self.media_repo.exists(media_id):
            raise MediaNotFoundError(media_id)

        # Deleting from repo should cascade or be handled by event listeners
        # For simplicity, we assume cascading deletes in the repository for modality statuses
        await self.media_repo.delete(media_id)
        self.metrics.increment("media_deleted_total")
        
        # Note: In a real system, you'd want to also publish a VectorDeleted event 
        # so the vector DB can be cleaned up
