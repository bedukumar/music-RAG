"""
Media Schemas.

Pydantic models for media requests and responses.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from ragpipe.domain.models.media import MediaType
from ragpipe.domain.models.modality import Modality


class ModalityStatusResponse(BaseModel):
    """Schema for modality status."""
    modality: str
    data_available: bool
    embedding_status: str
    last_processed: Optional[datetime] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MediaCreateRequest(BaseModel):
    """Schema for creating a media item."""
    title: str
    media_type: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[list[str]] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    metadata_fields: Optional[dict[str, Any]] = None
    # Subclass specific fields
    lyrics: Optional[str] = None
    bpm: Optional[int] = None
    musical_key: Optional[str] = None
    show_name: Optional[str] = None
    episode_number: Optional[int] = None
    host: Optional[str] = None
    guests: Optional[list[str]] = None
    description: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    video_path: Optional[str] = None


class MediaUpdateRequest(BaseModel):
    """Schema for updating a media item."""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[list[str]] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    metadata_fields: Optional[dict[str, Any]] = None
    # Subclass fields...
    lyrics: Optional[str] = None


class MediaResponse(BaseModel):
    """Schema for returning a media item."""
    id: str
    media_type: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    duration: Optional[float] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_text: Optional[str] = None
    metadata_fields: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    # Nested statuses
    modality_statuses: list[ModalityStatusResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class MediaListResponse(BaseModel):
    """Schema for paginated media items."""
    items: list[MediaResponse]
    total: int
    offset: int
    limit: int
