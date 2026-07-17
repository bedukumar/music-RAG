"""
Overlap Audio Chunker.

Splits audio into segments with a configurable overlap.
"""

import hashlib
from datetime import datetime, timezone

import numpy as np

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig, ChunkType
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import AudioChunker


class OverlapChunker(AudioChunker):
    """Chunks audio into segments with overlap."""

    @property
    def strategy_name(self) -> str:
        return "overlap"

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
        """Split audio into chunks with overlap.

        Args:
            audio_data: Numpy array of audio data.
            sample_rate: Audio sample rate.
            media_id: The media item ID.
            config: Chunking configuration (chunk_size and overlap in seconds).

        Returns:
            List of Chunk objects.
        """
        duration_sec = float(config.chunk_size)
        overlap_sec = float(config.overlap)
        
        if overlap_sec >= duration_sec:
            raise ValueError("Overlap must be less than chunk_size")
            
        samples_per_chunk = int(duration_sec * sample_rate)
        samples_per_overlap = int(overlap_sec * sample_rate)
        step_size = samples_per_chunk - samples_per_overlap
        
        step_size = max(1, step_size)
        
        total_samples = len(audio_data) if audio_data.ndim == 1 else audio_data.shape[0]
        
        chunks = []
        now = datetime.now(timezone.utc)
        
        # If the audio is shorter than a chunk, we just output one chunk
        if total_samples <= samples_per_chunk:
            chunk_data = audio_data
            chunk_id = self._generate_id(media_id, Modality.AUDIO, 0, config.version)
            return [Chunk(
                id=chunk_id,
                media_id=media_id,
                modality=Modality.AUDIO,
                chunk_type=ChunkType.AUDIO_SEGMENT,
                chunk_index=0,
                content=chunk_data.tobytes(),
                start_offset=0.0,
                end_offset=total_samples / sample_rate,
                metadata={"sample_rate": sample_rate, "samples": total_samples},
                created_at=now,
            )]
        
        for i in range(0, total_samples, step_size):
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
                    "is_partial": len(chunk_data) < samples_per_chunk
                },
                created_at=now,
            )
            chunks.append(chunk)
            
            # If we've reached the end, break (to avoid tiny final chunks if they fit within previous step)
            if end_idx == total_samples:
                break
                
        return chunks
