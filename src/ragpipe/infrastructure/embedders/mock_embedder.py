"""
Mock Embedding Providers.

Provides deterministic dummy embeddings for testing and local development
without requiring GPUs or downloading large models.
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import numpy as np

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.embedding_provider import AudioEmbeddingProvider, TextEmbeddingProvider


class MockAudioEmbedder(AudioEmbeddingProvider):
    """Generates deterministic mock audio embeddings."""

    def __init__(self, delay_seconds: float = 0.1) -> None:
        """Initialize the mock embedder.

        Args:
            delay_seconds: Simulated processing delay.
        """
        self._delay = delay_seconds

    @property
    def model_name(self) -> str:
        return "mock-audio"

    @property
    def model_version(self) -> str:
        return "v1"

    @property
    def dimension(self) -> int:
        return 512

    @property
    def modality(self) -> Modality:
        return Modality.AUDIO

    def _generate_deterministic_vector(self, data: bytes) -> np.ndarray:
        """Generate a pseudo-random but deterministic vector based on input data."""
        seed = int(hashlib.sha256(data).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.uniform(-1.0, 1.0, self.dimension)
        return (vec / np.linalg.norm(vec)).astype(np.float32)

    async def embed_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Embed a single audio array."""
        await asyncio.sleep(self._delay)
        vec = self._generate_deterministic_vector(audio_data.tobytes())
        return vec.reshape(1, -1)

    async def embed_audio_file(self, file_path: str) -> np.ndarray:
        """Embed audio from a file."""
        await asyncio.sleep(self._delay)
        vec = self._generate_deterministic_vector(file_path.encode("utf-8"))
        return vec.reshape(1, -1)

    async def embed_audio_batch(self, audio_list: list[np.ndarray], sample_rate: int) -> np.ndarray:
        """Embed a batch of audio arrays."""
        await asyncio.sleep(self._delay * len(audio_list))
        vectors = [self._generate_deterministic_vector(a.tobytes()) for a in audio_list]
        return np.vstack(vectors)

    def embed(self, data: Any) -> np.ndarray:
        """Generate an embedding for a single input."""
        return self._generate_deterministic_vector(str(data).encode("utf-8")).reshape(1, -1)

    def embed_batch(self, data_list: list[Any]) -> np.ndarray:
        """Generate embeddings for a batch of inputs."""
        vectors = [self._generate_deterministic_vector(str(d).encode("utf-8")) for d in data_list]
        if not vectors:
            return np.empty((0, self.dimension), dtype=np.float32)
        return np.vstack(vectors)


class MockTextEmbedder(TextEmbeddingProvider):
    """Generates deterministic mock text embeddings."""

    def __init__(self, modality: Modality = Modality.TRANSCRIPT, delay_seconds: float = 0.05) -> None:
        """Initialize the mock embedder.

        Args:
            modality: The modality this embedder handles (TRANSCRIPT or METADATA).
            delay_seconds: Simulated processing delay.
        """
        self._modality = modality
        self._delay = delay_seconds

    @property
    def model_name(self) -> str:
        return "mock-text"

    @property
    def model_version(self) -> str:
        return "v1"

    @property
    def dimension(self) -> int:
        return 384

    @property
    def modality(self) -> Modality:
        return self._modality

    def _generate_deterministic_vector(self, text: str) -> np.ndarray:
        """Generate a pseudo-random but deterministic vector based on input text."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.uniform(-1.0, 1.0, self.dimension)
        return (vec / np.linalg.norm(vec)).astype(np.float32)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        await asyncio.sleep(self._delay)
        vec = self._generate_deterministic_vector(text)
        return vec.reshape(1, -1)

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of text strings."""
        await asyncio.sleep(self._delay * len(texts))
        vectors = [self._generate_deterministic_vector(t) for t in texts]
        if not vectors:
            return np.empty((0, self.dimension), dtype=np.float32)
        return np.vstack(vectors)

    def embed(self, data: Any) -> np.ndarray:
        """Generate an embedding for a single input."""
        return self._generate_deterministic_vector(str(data)).reshape(1, -1)

    def embed_batch(self, data_list: list[Any]) -> np.ndarray:
        """Generate embeddings for a batch of inputs."""
        vectors = [self._generate_deterministic_vector(str(d)) for d in data_list]
        if not vectors:
            return np.empty((0, self.dimension), dtype=np.float32)
        return np.vstack(vectors)
