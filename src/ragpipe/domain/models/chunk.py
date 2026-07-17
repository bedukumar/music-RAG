"""Chunk domain models for the RAG Data Ingestion Platform.

This module defines content chunks — the atomic units of data that get
embedded and stored in the vector database.  Chunk IDs are generated
deterministically so that re-processing the same input with the same
configuration yields identical identifiers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Union

from ragpipe.domain.exceptions import ValidationError
from ragpipe.domain.models.modality import Modality


class ChunkType(Enum):
    """Classification of chunk content type.

    Determines the nature and format of the data held in the chunk.
    """

    AUDIO_SEGMENT = "audio_segment"
    TEXT_SENTENCE = "text_sentence"
    TEXT_PARAGRAPH = "text_paragraph"
    TEXT_TOKEN = "text_token"
    METADATA_BLOCK = "metadata_block"


def _generate_deterministic_id(
    media_id: str,
    modality: Modality,
    chunk_index: int,
    chunking_version: str,
) -> str:
    """Generate a deterministic chunk identifier.

    The ID is a SHA-256 hex digest of the concatenation of the media ID,
    modality value, chunk index, and chunking version.  This ensures that
    re-processing the same content with the same configuration produces the
    same chunk ID.

    Args:
        media_id: Parent media item identifier.
        modality: Content modality.
        chunk_index: Zero-based index of the chunk.
        chunking_version: Chunking strategy version.

    Returns:
        A 64-character lowercase hex string.
    """
    raw = f"{media_id}:{modality.value}:{chunk_index}:{chunking_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChunkingConfig:
    """Configuration for a chunking operation.

    Immutable value object that fully describes how content should be split
    into chunks.

    Attributes:
        strategy_name: Identifier of the chunking strategy.
        version: Version of the chunking strategy.
        chunk_size: Size of each chunk (seconds for audio, characters/tokens for text).
        overlap: Overlap between consecutive chunks.
        extra_params: Additional strategy-specific parameters.
    """

    strategy_name: str
    version: str
    chunk_size: Union[int, float]
    overlap: Union[int, float]
    extra_params: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.strategy_name or not self.strategy_name.strip():
            raise ValidationError(
                "strategy_name", "Chunking strategy name must not be empty"
            )
        if not self.version or not self.version.strip():
            raise ValidationError("version", "Chunking version must not be empty")
        if self.chunk_size <= 0:
            raise ValidationError(
                "chunk_size",
                f"chunk_size must be positive, got {self.chunk_size}",
            )
        if self.overlap < 0:
            raise ValidationError(
                "overlap",
                f"overlap must be non-negative, got {self.overlap}",
            )


@dataclass(frozen=True)
class Chunk:
    """An atomic unit of content destined for embedding and vector storage.

    Chunk IDs are deterministic — derived from the media ID, modality,
    chunk index, and the chunking version stored in the metadata.

    Attributes:
        id: Deterministic SHA-256 identifier.
        media_id: Parent media item identifier.
        modality: Content modality.
        chunk_type: Type classification of the chunk content.
        chunk_index: Zero-based positional index within the media item.
        content: Raw chunk payload (bytes for audio, str for text).
        start_offset: Start offset (seconds for audio, character index for text).
        end_offset: End offset.
        metadata: Arbitrary chunk-level metadata.
        created_at: Timestamp of creation.
    """

    id: str
    media_id: str
    modality: Modality
    chunk_type: ChunkType
    chunk_index: int
    content: Union[bytes, str]
    start_offset: Optional[Union[float, int]] = None
    end_offset: Optional[Union[float, int]] = None
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "Chunk id must not be empty")
        if not self.media_id:
            raise ValidationError("media_id", "media_id must not be empty")
        if self.chunk_index < 0:
            raise ValidationError(
                "chunk_index",
                f"chunk_index must be non-negative, got {self.chunk_index}",
            )
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.start_offset > self.end_offset
        ):
            raise ValidationError(
                "start_offset",
                f"start_offset ({self.start_offset}) must not exceed "
                f"end_offset ({self.end_offset})",
            )

    @classmethod
    def create(
        cls,
        media_id: str,
        modality: Modality,
        chunk_type: ChunkType,
        chunk_index: int,
        content: Union[bytes, str],
        chunking_version: str,
        start_offset: Optional[Union[float, int]] = None,
        end_offset: Optional[Union[float, int]] = None,
        metadata: dict[str, object] | None = None,
    ) -> Chunk:
        """Factory method to create a chunk with a deterministic ID.

        Args:
            media_id: Parent media item identifier.
            modality: Content modality.
            chunk_type: Type classification.
            chunk_index: Zero-based index.
            content: Raw data (bytes for audio, str for text).
            chunking_version: Version string for deterministic ID generation.
            start_offset: Optional start position.
            end_offset: Optional end position.
            metadata: Optional metadata dict.

        Returns:
            A fully initialised ``Chunk`` with a deterministic ``id``.
        """
        chunk_id = _generate_deterministic_id(
            media_id=media_id,
            modality=modality,
            chunk_index=chunk_index,
            chunking_version=chunking_version,
        )
        merged_metadata = metadata.copy() if metadata else {}
        merged_metadata.setdefault("chunking_version", chunking_version)
        return cls(
            id=chunk_id,
            media_id=media_id,
            modality=modality,
            chunk_type=chunk_type,
            chunk_index=chunk_index,
            content=content,
            start_offset=start_offset,
            end_offset=end_offset,
            metadata=merged_metadata,
            created_at=datetime.now(timezone.utc),
        )
