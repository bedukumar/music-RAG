"""
Token Text Chunker.

Splits text into chunks by tokens (words).
"""

import hashlib
from datetime import datetime, timezone

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import TextChunker


class TokenChunker(TextChunker):
    """Chunks text by word tokens."""

    @property
    def strategy_name(self) -> str:
        return "token"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def chunk_text(self, text: str, media_id: str, config: ChunkingConfig) -> list[Chunk]:
        """Split text into token-based chunks.

        Args:
            text: Text to chunk.
            media_id: The media item ID.
            config: Configuration (chunk_size is tokens, overlap is tokens).

        Returns:
            List of Chunk objects.
        """
        tokens_per_chunk = int(config.chunk_size)
        overlap = int(config.overlap)
        
        # Simple whitespace tokenization
        # In a real system, we'd use tiktoken or similar
        tokens = text.split()
        if not tokens:
            return []
            
        chunks = []
        now = datetime.now(timezone.utc)
        
        step_size = max(1, tokens_per_chunk - overlap)
        chunk_index = 0
        
        for i in range(0, len(tokens), step_size):
            end_idx = min(i + tokens_per_chunk, len(tokens))
            chunk_tokens = tokens[i:end_idx]
            
            content = " ".join(chunk_tokens)
            chunk_id = self._generate_id(media_id, Modality.TRANSCRIPT, chunk_index, config.version)
            
            chunk = Chunk(
                id=chunk_id,
                media_id=media_id,
                modality=Modality.TRANSCRIPT,
                chunk_type=ChunkType.TEXT_TOKEN,
                chunk_index=chunk_index,
                content=content,
                start_offset=None,
                end_offset=None,
                metadata={"token_count": len(chunk_tokens)},
                created_at=now,
            )
            chunks.append(chunk)
            chunk_index += 1
            
            if end_idx == len(tokens):
                break
                
        return chunks
