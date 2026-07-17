"""
Sentence Text Chunker.

Splits text into chunks of sentences.
"""

import hashlib
import re
from datetime import datetime, timezone

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import TextChunker


class SentenceChunker(TextChunker):
    """Chunks text by sentence boundaries."""

    @property
    def strategy_name(self) -> str:
        return "sentence"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using simple regex."""
        # Split on . ! ? followed by space or newline, but keep the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str, media_id: str, config: ChunkingConfig) -> list[Chunk]:
        """Split text into sentence-based chunks.

        Args:
            text: Text to chunk.
            media_id: The media item ID.
            config: Configuration (chunk_size is approx max chars, overlap is sentences).

        Returns:
            List of Chunk objects.
        """
        max_chars = int(config.chunk_size)
        overlap_sentences = int(config.overlap)
        
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []
            
        chunks = []
        now = datetime.now(timezone.utc)
        
        current_chunk_sentences = []
        current_length = 0
        chunk_index = 0
        
        def finalize_chunk(sentences_to_include):
            nonlocal chunk_index
            content = " ".join(sentences_to_include)
            chunk_id = self._generate_id(media_id, Modality.TRANSCRIPT, chunk_index, config.version)
            
            chunk = Chunk(
                id=chunk_id,
                media_id=media_id,
                modality=Modality.TRANSCRIPT,
                chunk_type=ChunkType.TEXT_SENTENCE,
                chunk_index=chunk_index,
                content=content,
                start_offset=None, # In a real system we'd track char offsets
                end_offset=None,
                metadata={"sentence_count": len(sentences_to_include)},
                created_at=now,
            )
            chunks.append(chunk)
            chunk_index += 1

        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_len = len(sentence)
            
            if not current_chunk_sentences:
                current_chunk_sentences.append(sentence)
                current_length = sentence_len
                i += 1
                continue
                
            # If adding this sentence exceeds the limit, output current chunk
            if current_length + 1 + sentence_len > max_chars:
                finalize_chunk(current_chunk_sentences)
                
                # Start new chunk, incorporating overlap
                if overlap_sentences > 0 and len(current_chunk_sentences) >= overlap_sentences:
                    current_chunk_sentences = current_chunk_sentences[-overlap_sentences:]
                    current_length = sum(len(s) for s in current_chunk_sentences) + len(current_chunk_sentences) - 1
                else:
                    current_chunk_sentences = []
                    current_length = 0
            else:
                current_chunk_sentences.append(sentence)
                current_length += 1 + sentence_len
                i += 1
                
        # Output any remaining sentences
        if current_chunk_sentences:
            finalize_chunk(current_chunk_sentences)
            
        return chunks
