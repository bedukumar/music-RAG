"""
Template Builder Metadata Chunker.

Creates a single text chunk by formatting a template with metadata values.
"""

import hashlib
import string
from datetime import datetime, timezone
from typing import Any

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import MetadataChunker


class SafeFormatter(string.Formatter):
    """String formatter that ignores missing keys."""
    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except KeyError:
            return ""


class TemplateBuilder(MetadataChunker):
    """Builds text using a template string."""

    @property
    def strategy_name(self) -> str:
        return "template"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def build_text(self, metadata: dict[str, Any], media_id: str, config: ChunkingConfig) -> list[Chunk]:
        """Build a text chunk from a metadata template.

        Args:
            metadata: Metadata dictionary.
            media_id: The media item ID.
            config: Configuration (extra_params['template']).

        Returns:
            List with a single Chunk.
        """
        template = config.extra_params.get("template", "")
        if not template:
            return []
            
        formatter = SafeFormatter()
        content = formatter.format(template, **metadata)
        
        now = datetime.now(timezone.utc)
        chunk_id = self._generate_id(media_id, Modality.METADATA, 0, config.version)
        
        chunk = Chunk(
            id=chunk_id,
            media_id=media_id,
            modality=Modality.METADATA,
            chunk_type=ChunkType.METADATA_BLOCK,
            chunk_index=0,
            content=content.strip(),
            start_offset=None,
            end_offset=None,
            metadata={"template_used": True},
            created_at=now,
        )
        
        return [chunk]
