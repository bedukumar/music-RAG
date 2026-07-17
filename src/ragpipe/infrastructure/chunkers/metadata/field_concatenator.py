"""
Field Concatenator Metadata Chunker.

Creates a single text chunk from selected metadata fields.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import MetadataChunker


class FieldConcatenator(MetadataChunker):
    """Concatenates selected metadata fields into a single text block."""

    @property
    def strategy_name(self) -> str:
        return "field_concatenator"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def build_text(self, metadata: dict[str, Any], media_id: str, config: ChunkingConfig) -> list[Chunk]:
        """Build a text chunk from metadata fields.

        Args:
            metadata: Metadata dictionary.
            media_id: The media item ID.
            config: Configuration (extra_params['fields'] and extra_params['separator']).

        Returns:
            List with a single Chunk.
        """
        fields = config.extra_params.get("fields", [])
        separator = config.extra_params.get("separator", ". ")
        
        parts = []
        for field in fields:
            val = metadata.get(field)
            if val is not None:
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                parts.append(f"{field.capitalize()}: {val}")
                
        if not parts:
            return []
            
        content = separator.join(parts)
        now = datetime.now(timezone.utc)
        chunk_id = self._generate_id(media_id, Modality.METADATA, 0, config.version)
        
        chunk = Chunk(
            id=chunk_id,
            media_id=media_id,
            modality=Modality.METADATA,
            chunk_type=ChunkType.METADATA_BLOCK,
            chunk_index=0,
            content=content,
            start_offset=None,
            end_offset=None,
            metadata={"fields_included": fields},
            created_at=now,
        )
        
        return [chunk]
