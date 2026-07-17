"""
SQLAlchemy Media Repository.

Implements the MediaRepository port using SQLAlchemy async sessions.
Handles CRUD operations for media items and modality statuses.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ragpipe.domain.models.media import MediaItem, MediaType, Podcast, Song, Video
from ragpipe.domain.models.modality import Modality, ModalityStatus
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.infrastructure.database.models import MediaItemORM, ModalityStatusORM

logger = logging.getLogger(__name__)


class SQLAlchemyMediaRepository(MediaRepository):
    """SQLAlchemy implementation of the MediaRepository port.

    Provides persistent storage for media items and their modality
    statuses using a relational database via SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    def _domain_to_orm(self, media: MediaItem) -> MediaItemORM:
        """Convert a domain MediaItem to an ORM model.

        Args:
            media: Domain media item.

        Returns:
            ORM media item model.
        """
        orm = MediaItemORM(
            id=media.id,
            media_type=media.media_type.value,
            title=media.title,
            artist=media.artist,
            album=media.album,
            genre=media.genre,
            tags=media.tags,
            duration=media.duration,
            language=media.language,
            source_url=media.source_url,
            audio_path=media.audio_path,
            transcript_text=media.transcript_text,
            metadata_fields=media.metadata_fields,
            created_at=media.created_at,
            updated_at=media.updated_at,
        )

        if isinstance(media, Song):
            orm.lyrics = media.lyrics
            orm.bpm = media.bpm
            orm.musical_key = media.key
        elif isinstance(media, Podcast):
            orm.show_name = media.show_name
            orm.episode_number = media.episode_number
            orm.host = media.host
            orm.guests = media.guests
            orm.description = media.description
        elif isinstance(media, Video):
            orm.resolution = media.resolution
            orm.fps = media.fps
            orm.video_path = media.video_path

        return orm

    def _orm_to_domain(self, orm: MediaItemORM) -> MediaItem:
        """Convert an ORM model to a domain MediaItem.

        Args:
            orm: ORM media item model.

        Returns:
            Domain media item.
        """
        media_type = MediaType(orm.media_type)
        base_kwargs = {
            "id": orm.id,
            "media_type": media_type,
            "title": orm.title,
            "artist": orm.artist,
            "album": orm.album,
            "genre": orm.genre,
            "tags": orm.tags or [],
            "duration": orm.duration,
            "language": orm.language,
            "source_url": orm.source_url,
            "audio_path": orm.audio_path,
            "transcript_text": orm.transcript_text,
            "metadata_fields": orm.metadata_fields or {},
            "created_at": orm.created_at,
            "updated_at": orm.updated_at,
        }

        if media_type == MediaType.SONG:
            return Song(
                **base_kwargs,
                lyrics=orm.lyrics,
                bpm=orm.bpm,
                key=orm.musical_key,
            )
        elif media_type == MediaType.PODCAST:
            return Podcast(
                **base_kwargs,
                show_name=orm.show_name,
                episode_number=orm.episode_number,
                host=orm.host,
                guests=orm.guests or [],
                description=orm.description,
            )
        elif media_type == MediaType.VIDEO:
            return Video(
                **base_kwargs,
                resolution=orm.resolution,
                fps=orm.fps,
                video_path=orm.video_path,
            )
        else:
            return MediaItem(**base_kwargs)

    def _modality_status_to_domain(self, orm: ModalityStatusORM) -> ModalityStatus:
        """Convert ORM modality status to domain model.

        Args:
            orm: ORM modality status model.

        Returns:
            Domain modality status.
        """
        return ModalityStatus(
            media_id=orm.media_id,
            modality=Modality(orm.modality),
            data_available=orm.data_available,
            embedding_status=orm.embedding_status,
            embedding_version_id=orm.embedding_version_id,
            last_processed=orm.last_processed,
            error_message=orm.error_message,
        )

    async def save(self, media: MediaItem) -> None:
        """Save a new media item to the database.

        Args:
            media: The media item to save.
        """
        orm = self._domain_to_orm(media)
        self._session.add(orm)
        await self._session.commit()
        logger.info("Saved media item", extra={"media_id": media.id, "type": media.media_type.value})

    async def get(self, media_id: str) -> Optional[MediaItem]:
        """Get a media item by ID.

        Args:
            media_id: The unique identifier of the media item.

        Returns:
            The media item if found, None otherwise.
        """
        stmt = select(MediaItemORM).where(MediaItemORM.id == media_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._orm_to_domain(orm)

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        media_type: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> tuple[list[MediaItem], int]:
        """List media items with pagination and optional filtering.

        Args:
            offset: Number of items to skip.
            limit: Maximum number of items to return.
            media_type: Optional filter by media type.
            filters: Optional additional filters (key-value pairs).

        Returns:
            Tuple of (list of media items, total count).
        """
        stmt = select(MediaItemORM)
        count_stmt = select(func.count(MediaItemORM.id))

        if media_type:
            stmt = stmt.where(MediaItemORM.media_type == media_type)
            count_stmt = count_stmt.where(MediaItemORM.media_type == media_type)

        if filters:
            if "title" in filters:
                stmt = stmt.where(MediaItemORM.title.ilike(f"%{filters['title']}%"))
                count_stmt = count_stmt.where(MediaItemORM.title.ilike(f"%{filters['title']}%"))
            if "artist" in filters:
                stmt = stmt.where(MediaItemORM.artist.ilike(f"%{filters['artist']}%"))
                count_stmt = count_stmt.where(MediaItemORM.artist.ilike(f"%{filters['artist']}%"))
            if "genre" in filters:
                stmt = stmt.where(MediaItemORM.genre == filters["genre"])
                count_stmt = count_stmt.where(MediaItemORM.genre == filters["genre"])

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated results
        stmt = stmt.order_by(MediaItemORM.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        items = [self._orm_to_domain(orm) for orm in result.scalars().all()]

        return items, total

    async def update(self, media: MediaItem) -> None:
        """Update an existing media item.

        Args:
            media: The media item with updated values.
        """
        stmt = select(MediaItemORM).where(MediaItemORM.id == media.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ValueError(f"Media item {media.id} not found")

        # Update base fields
        orm.title = media.title
        orm.artist = media.artist
        orm.album = media.album
        orm.genre = media.genre
        orm.tags = media.tags
        orm.duration = media.duration
        orm.language = media.language
        orm.source_url = media.source_url
        orm.audio_path = media.audio_path
        orm.transcript_text = media.transcript_text
        orm.metadata_fields = media.metadata_fields
        orm.media_type = media.media_type.value
        orm.updated_at = datetime.now(timezone.utc)

        # Update type-specific fields
        if isinstance(media, Song):
            orm.lyrics = media.lyrics
            orm.bpm = media.bpm
            orm.musical_key = media.key
        elif isinstance(media, Podcast):
            orm.show_name = media.show_name
            orm.episode_number = media.episode_number
            orm.host = media.host
            orm.guests = media.guests
            orm.description = media.description
        elif isinstance(media, Video):
            orm.resolution = media.resolution
            orm.fps = media.fps
            orm.video_path = media.video_path

        await self._session.commit()
        logger.info("Updated media item", extra={"media_id": media.id})

    async def delete(self, media_id: str) -> None:
        """Delete a media item and all related records.

        Args:
            media_id: The ID of the media item to delete.
        """
        stmt = delete(MediaItemORM).where(MediaItemORM.id == media_id)
        await self._session.execute(stmt)
        await self._session.commit()
        logger.info("Deleted media item", extra={"media_id": media_id})

    async def exists(self, media_id: str) -> bool:
        """Check if a media item exists.

        Args:
            media_id: The ID to check.

        Returns:
            True if the media item exists, False otherwise.
        """
        stmt = select(func.count(MediaItemORM.id)).where(MediaItemORM.id == media_id)
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0

    async def get_modality_status(
        self, media_id: str, modality: Modality
    ) -> Optional[ModalityStatus]:
        """Get the modality status for a specific media item and modality.

        Args:
            media_id: The media item ID.
            modality: The modality to check.

        Returns:
            The modality status if found, None otherwise.
        """
        stmt = select(ModalityStatusORM).where(
            ModalityStatusORM.media_id == media_id,
            ModalityStatusORM.modality == modality.value,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._modality_status_to_domain(orm)

    async def save_modality_status(self, status: ModalityStatus) -> None:
        """Save or update a modality status.

        Uses upsert semantics — creates if not exists, updates if exists.

        Args:
            status: The modality status to save.
        """
        stmt = select(ModalityStatusORM).where(
            ModalityStatusORM.media_id == status.media_id,
            ModalityStatusORM.modality == status.modality.value,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            orm = ModalityStatusORM(
                media_id=status.media_id,
                modality=status.modality.value,
                data_available=status.data_available,
                embedding_status=status.embedding_status,
                embedding_version_id=status.embedding_version_id,
                last_processed=status.last_processed,
                error_message=status.error_message,
            )
            self._session.add(orm)
        else:
            orm.data_available = status.data_available
            orm.embedding_status = status.embedding_status
            orm.embedding_version_id = status.embedding_version_id
            orm.last_processed = status.last_processed
            orm.error_message = status.error_message

        await self._session.commit()
        logger.debug(
            "Saved modality status",
            extra={
                "media_id": status.media_id,
                "modality": status.modality.value,
                "status": status.embedding_status,
            },
        )

    async def list_modality_statuses(self, media_id: str) -> list[ModalityStatus]:
        """List all modality statuses for a media item.

        Args:
            media_id: The media item ID.

        Returns:
            List of modality statuses.
        """
        stmt = select(ModalityStatusORM).where(
            ModalityStatusORM.media_id == media_id
        )
        result = await self._session.execute(stmt)
        return [self._modality_status_to_domain(orm) for orm in result.scalars().all()]

    async def get_items_needing_processing(
        self, modality: Modality, limit: int = 100
    ) -> list[str]:
        """Get media IDs that have data available but unprocessed embeddings.

        Args:
            modality: The modality to check.
            limit: Maximum number of IDs to return.

        Returns:
            List of media item IDs needing processing.
        """
        stmt = (
            select(ModalityStatusORM.media_id)
            .where(
                ModalityStatusORM.modality == modality.value,
                ModalityStatusORM.data_available == True,
                ModalityStatusORM.embedding_status.in_(["pending", "failed"]),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
