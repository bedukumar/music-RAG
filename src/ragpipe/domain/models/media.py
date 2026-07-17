"""Media domain models for the RAG Data Ingestion Platform.

This module contains the core media entity hierarchy.  Every piece of content
ingested into the platform is represented as a ``MediaItem`` subtype.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ragpipe.domain.exceptions import ValidationError


class MediaType(Enum):
    """Supported media content types."""

    SONG = "song"
    PODCAST = "podcast"
    VIDEO = "video"


@dataclass(frozen=True)
class MediaItem:
    """Base media entity.

    Represents any piece of audio-visual content that can be ingested,
    chunked, embedded, and stored.  Immutable by design — mutations should
    produce new instances (or use ``dataclasses.replace``).

    Attributes:
        id: Unique identifier (UUID-4 string).
        media_type: The type of media content.
        title: Human-readable title of the media item.
        artist: Creator / primary artist.
        album: Album or collection name.
        genre: Genre classification.
        tags: Free-form tags for categorisation.
        duration: Duration in seconds.
        language: BCP-47 language tag (e.g. ``en``, ``hi``).
        source_url: Original source URL, if applicable.
        audio_path: Path to the raw audio file in storage.
        transcript_text: Full transcript text, if available.
        metadata_fields: Arbitrary key-value metadata.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    id: str
    media_type: MediaType
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    duration: Optional[float] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    metadata_fields: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "Media item id must not be empty")
        if not self.title or not self.title.strip():
            raise ValidationError("title", "Media item title must not be empty or blank")
        if self.duration is not None and self.duration < 0:
            raise ValidationError("duration", "Duration must be non-negative")


@dataclass(frozen=True)
class Song(MediaItem):
    """A song media item.

    Extends ``MediaItem`` with music-specific attributes such as lyrics,
    tempo, and musical key.

    Attributes:
        lyrics: Full lyrics text.
        bpm: Beats per minute.
        key: Musical key (e.g. ``C#m``, ``Amaj``).
    """

    lyrics: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate song-specific invariants."""
        super().__post_init__()
        if self.bpm is not None and self.bpm <= 0:
            raise ValidationError("bpm", "BPM must be a positive number")

    @classmethod
    def create(
        cls,
        title: str,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        tags: Optional[list[str]] = None,
        duration: Optional[float] = None,
        language: Optional[str] = None,
        source_url: Optional[str] = None,
        audio_path: Optional[str] = None,
        transcript_text: Optional[str] = None,
        metadata_fields: Optional[dict[str, object]] = None,
        lyrics: Optional[str] = None,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
    ) -> Song:
        """Factory method to create a new ``Song`` with a generated UUID.

        Args:
            title: Song title.
            artist: Performing artist.
            album: Album name.
            genre: Genre label.
            tags: Free-form tags.
            duration: Duration in seconds.
            language: BCP-47 language tag.
            source_url: Original source URL.
            audio_path: Storage path for the audio file.
            transcript_text: Transcript / lyrics text.
            metadata_fields: Extra metadata key-value pairs.
            lyrics: Full lyrics text.
            bpm: Tempo in beats per minute.
            key: Musical key.

        Returns:
            A fully initialised ``Song`` instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            media_type=MediaType.SONG,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            tags=tags or [],
            duration=duration,
            language=language,
            source_url=source_url,
            audio_path=audio_path,
            transcript_text=transcript_text,
            metadata_fields=metadata_fields or {},
            created_at=now,
            updated_at=now,
            lyrics=lyrics,
            bpm=bpm,
            key=key,
        )


@dataclass(frozen=True)
class Podcast(MediaItem):
    """A podcast episode media item.

    Extends ``MediaItem`` with podcast-specific attributes such as the
    show name, episode number, host, and guest list.

    Attributes:
        show_name: Name of the podcast show.
        episode_number: Episode number within the show.
        host: Primary host of the episode.
        guests: List of guest names.
    """

    show_name: Optional[str] = None
    episode_number: Optional[int] = None
    host: Optional[str] = None
    guests: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate podcast-specific invariants."""
        super().__post_init__()
        if self.episode_number is not None and self.episode_number < 0:
            raise ValidationError(
                "episode_number", "Episode number must be non-negative"
            )

    @classmethod
    def create(
        cls,
        title: str,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        tags: Optional[list[str]] = None,
        duration: Optional[float] = None,
        language: Optional[str] = None,
        source_url: Optional[str] = None,
        audio_path: Optional[str] = None,
        transcript_text: Optional[str] = None,
        metadata_fields: Optional[dict[str, object]] = None,
        show_name: Optional[str] = None,
        episode_number: Optional[int] = None,
        host: Optional[str] = None,
        guests: Optional[list[str]] = None,
    ) -> Podcast:
        """Factory method to create a new ``Podcast`` with a generated UUID.

        Args:
            title: Episode title.
            artist: Creator or producer.
            album: Series or season identifier.
            genre: Genre label.
            tags: Free-form tags.
            duration: Duration in seconds.
            language: BCP-47 language tag.
            source_url: Original source URL.
            audio_path: Storage path for the audio file.
            transcript_text: Episode transcript.
            metadata_fields: Extra metadata key-value pairs.
            show_name: The podcast show name.
            episode_number: Episode number.
            host: Primary host name.
            guests: Guest names list.

        Returns:
            A fully initialised ``Podcast`` instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            media_type=MediaType.PODCAST,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            tags=tags or [],
            duration=duration,
            language=language,
            source_url=source_url,
            audio_path=audio_path,
            transcript_text=transcript_text,
            metadata_fields=metadata_fields or {},
            created_at=now,
            updated_at=now,
            show_name=show_name,
            episode_number=episode_number,
            host=host,
            guests=guests or [],
        )


@dataclass(frozen=True)
class Video(MediaItem):
    """A video media item.

    Extends ``MediaItem`` with video-specific attributes such as resolution,
    frame rate, and a path to the video file.

    Attributes:
        resolution: Video resolution string (e.g. ``1920x1080``).
        fps: Frames per second.
        video_path: Storage path for the video file.
    """

    resolution: Optional[str] = None
    fps: Optional[float] = None
    video_path: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate video-specific invariants."""
        super().__post_init__()
        if self.fps is not None and self.fps <= 0:
            raise ValidationError("fps", "FPS must be a positive number")

    @classmethod
    def create(
        cls,
        title: str,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        tags: Optional[list[str]] = None,
        duration: Optional[float] = None,
        language: Optional[str] = None,
        source_url: Optional[str] = None,
        audio_path: Optional[str] = None,
        transcript_text: Optional[str] = None,
        metadata_fields: Optional[dict[str, object]] = None,
        resolution: Optional[str] = None,
        fps: Optional[float] = None,
        video_path: Optional[str] = None,
    ) -> Video:
        """Factory method to create a new ``Video`` with a generated UUID.

        Args:
            title: Video title.
            artist: Creator or uploader.
            album: Playlist or series name.
            genre: Genre label.
            tags: Free-form tags.
            duration: Duration in seconds.
            language: BCP-47 language tag.
            source_url: Original source URL.
            audio_path: Storage path for the extracted audio track.
            transcript_text: Video transcript.
            metadata_fields: Extra metadata key-value pairs.
            resolution: Resolution string (e.g. ``1920x1080``).
            fps: Frames per second.
            video_path: Storage path for the video file.

        Returns:
            A fully initialised ``Video`` instance.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            media_type=MediaType.VIDEO,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            tags=tags or [],
            duration=duration,
            language=language,
            source_url=source_url,
            audio_path=audio_path,
            transcript_text=transcript_text,
            metadata_fields=metadata_fields or {},
            created_at=now,
            updated_at=now,
            resolution=resolution,
            fps=fps,
            video_path=video_path,
        )
