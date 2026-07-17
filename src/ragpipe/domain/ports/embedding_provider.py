"""Embedding provider port interfaces for the RAG Data Ingestion Platform.

This module defines abstract base classes for embedding providers. The
domain layer depends only on these abstractions; concrete implementations
live in the infrastructure layer.

NumPy types are imported under ``TYPE_CHECKING`` to avoid a hard runtime
dependency on NumPy in the domain layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Sequence

from ragpipe.domain.models.modality import Modality

if TYPE_CHECKING:
    import numpy as np


class EmbeddingProvider(ABC):
    """Base abstract class for all embedding providers.

    Defines the contract that every embedding model adapter must satisfy,
    regardless of modality.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the embedding model.

        Returns:
            Model name string (e.g. ``openai/text-embedding-3-small``).
        """

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the version of the embedding model.

        Returns:
            Semantic version string.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the output embeddings.

        Returns:
            Positive integer representing vector dimension.
        """

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """Return the modality this provider handles.

        Returns:
            The target ``Modality``.
        """

    @abstractmethod
    def embed(self, data: object) -> np.ndarray:
        """Generate an embedding for a single input.

        Args:
            data: Input data appropriate for the provider's modality.

        Returns:
            A 1-D NumPy array of shape ``(dimension,)``.
        """

    @abstractmethod
    def embed_batch(self, data_list: Sequence[object]) -> np.ndarray:
        """Generate embeddings for a batch of inputs.

        Args:
            data_list: Sequence of inputs appropriate for the provider's
                modality.

        Returns:
            A 2-D NumPy array of shape ``(len(data_list), dimension)``.
        """


class AudioEmbeddingProvider(EmbeddingProvider):
    """Abstract embedding provider specialised for audio data.

    Extends ``EmbeddingProvider`` with audio-specific methods that accept
    raw waveform arrays and file paths.
    """

    @abstractmethod
    def embed_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Generate an embedding from raw audio waveform data.

        Args:
            audio_data: 1-D NumPy array of audio samples.
            sample_rate: Sample rate in Hz.

        Returns:
            A 1-D NumPy array of shape ``(dimension,)``.
        """

    @abstractmethod
    def embed_audio_file(self, file_path: str) -> np.ndarray:
        """Generate an embedding from an audio file on disk.

        Args:
            file_path: Absolute path to the audio file.

        Returns:
            A 1-D NumPy array of shape ``(dimension,)``.
        """

    @abstractmethod
    def embed_audio_batch(
        self, audio_list: Sequence[tuple[np.ndarray, int]]
    ) -> np.ndarray:
        """Generate embeddings for a batch of audio waveforms.

        Args:
            audio_list: Sequence of ``(audio_data, sample_rate)`` tuples.

        Returns:
            A 2-D NumPy array of shape ``(len(audio_list), dimension)``.
        """


class TextEmbeddingProvider(EmbeddingProvider):
    """Abstract embedding provider specialised for text data.

    Extends ``EmbeddingProvider`` with text-specific methods for single
    strings and batches.
    """

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Generate an embedding from a text string.

        Args:
            text: Input text.

        Returns:
            A 1-D NumPy array of shape ``(dimension,)``.
        """

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a batch of text strings.

        Args:
            texts: List of input texts.

        Returns:
            A 2-D NumPy array of shape ``(len(texts), dimension)``.
        """
