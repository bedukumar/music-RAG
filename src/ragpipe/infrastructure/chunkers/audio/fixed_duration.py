"""
Fixed Duration Audio Chunker.

Splits audio into fixed-duration segments.
"""

import hashlib
from datetime import datetime, timezone

import numpy as np

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import AudioChunker


class FixedDurationChunker(AudioChunker):
    """Chunks audio into fixed-duration non-overlapping segments."""

    @property
    def strategy_name(self) -> str:
        return "fixed_duration"

    @property
    def version(self) -> str:
        return "v1"

    def _generate_id(self, media_id: str, modality: Modality, chunk_index: int, version: str) -> str:
        """Generate a deterministic chunk ID."""
        key = f"{media_id}:{modality.value}:{chunk_index}:{version}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def chunk_audio(
        self, audio_data: np.ndarray, sample_rate: int, media_id: str, config: ChunkingConfig
    ) -> list[Chunk]:
        """Split audio into fixed-duration chunks.

        Args:
            audio_data: Numpy array of audio data.
            sample_rate: Audio sample rate.
            media_id: The media item ID.
            config: Chunking configuration containing chunk_size (seconds).

        Returns:
            List of Chunk objects.
        """
        duration_sec = float(config.chunk_size)
        samples_per_chunk = int(duration_sec * sample_rate)
        
        # Ensure we have at least one sample per chunk
        samples_per_chunk = max(1, samples_per_chunk)
        
        total_samples = len(audio_data) if audio_data.ndim == 1 else audio_data.shape[0]
        
        chunks = []
        now = datetime.now(timezone.utc)
        
        for i in range(0, total_samples, samples_per_chunk):
            end_idx = min(i + samples_per_chunk, total_samples)
            chunk_data = audio_data[i:end_idx]
            
            chunk_index = len(chunks)
            start_offset = i / sample_rate
            end_offset = end_idx / sample_rate
            
            chunk_id = self._generate_id(media_id, Modality.AUDIO, chunk_index, config.version)
            
            chunk = Chunk(
                id=chunk_id,
                media_id=media_id,
                modality=Modality.AUDIO,
                chunk_type=ChunkType.AUDIO_SEGMENT,
                chunk_index=chunk_index,
                content=chunk_data.tobytes(),
                start_offset=start_offset,
                end_offset=end_offset,
                metadata={
                    "sample_rate": sample_rate,
                    "samples": len(chunk_data),
                },
                created_at=now,
            )
            chunks.append(chunk)
            
        return chunks
