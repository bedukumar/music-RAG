"""
Paragraph Text Chunker.

Splits text into chunks of paragraphs.
"""

import hashlib
import re
from datetime import datetime, timezone

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import TextChunker


class ParagraphChunker(TextChunker):
    """Chunks text by paragraph boundaries."""

    @property
    def strategy_name(self) -> str:
        return "paragraph"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def chunk_text(self, text: str, media_id: str, config: ChunkingConfig) -> list[Chunk]:
        """Split text into paragraph-based chunks.

        Args:
            text: Text to chunk.
            media_id: The media item ID.
            config: Configuration (chunk_size is max chars, overlap not supported for paragraphs currently).

        Returns:
            List of Chunk objects.
        """
        max_chars = int(config.chunk_size)
        
        # Split by double newlines or more
        paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return []
            
        chunks = []
        now = datetime.now(timezone.utc)
        
        current_chunk_paragraphs = []
        current_length = 0
        chunk_index = 0
        
        def finalize_chunk(paras_to_include):
            nonlocal chunk_index
            content = "\n\n".join(paras_to_include)
            chunk_id = self._generate_id(media_id, Modality.TRANSCRIPT, chunk_index, config.version)
            
            chunk = Chunk(
                id=chunk_id,
                media_id=media_id,
                modality=Modality.TRANSCRIPT,
                chunk_type=ChunkType.TEXT_PARAGRAPH,
                chunk_index=chunk_index,
                content=content,
                start_offset=None,
                end_offset=None,
                metadata={"paragraph_count": len(paras_to_include)},
                created_at=now,
            )
            chunks.append(chunk)
            chunk_index += 1

        for para in paragraphs:
            para_len = len(para)
            
            if not current_chunk_paragraphs:
                current_chunk_paragraphs.append(para)
                current_length = para_len
                continue
                
            if current_length + 2 + para_len > max_chars:
                finalize_chunk(current_chunk_paragraphs)
                current_chunk_paragraphs = [para]
                current_length = para_len
            else:
                current_chunk_paragraphs.append(para)
                current_length += 2 + para_len
                
        if current_chunk_paragraphs:
            finalize_chunk(current_chunk_paragraphs)
            
        return chunks
