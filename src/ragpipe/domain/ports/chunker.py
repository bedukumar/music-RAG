"""Chunker port interfaces for the RAG Data Ingestion Platform.

This module defines abstract base classes for content chunking strategies.
Each modality has its own chunker interface.  Concrete implementations live
in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ragpipe.domain.models.chunk import Chunk, ChunkingConfig

if TYPE_CHECKING:
    import numpy as np


class AudioChunker(ABC):
    """Abstract chunker for audio content.

    Implementations split raw audio waveform data into overlapping or
    non-overlapping segments according to the supplied ``ChunkingConfig``.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of the chunking strategy.

        Returns:
            Strategy name string.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the chunking strategy.

        Returns:
            Version string.
        """

    @abstractmethod
    def chunk_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        config: ChunkingConfig,
    ) -> list[Chunk]:
        """Split raw audio data into chunks.

        Args:
            audio_data: 1-D NumPy array of audio samples.
            sample_rate: Sample rate in Hz.
            config: Chunking configuration.

        Returns:
            Ordered list of ``Chunk`` instances.
        """


class TextChunker(ABC):
    """Abstract chunker for text content.

    Implementations split text (transcripts, lyrics, etc.) into chunks
    according to the supplied ``ChunkingConfig``.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of the chunking strategy.

        Returns:
            Strategy name string.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the chunking strategy.

        Returns:
            Version string.
        """

    @abstractmethod
    def chunk_text(
        self,
        text: str,
        config: ChunkingConfig,
    ) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Input text content.
            config: Chunking configuration.

        Returns:
            Ordered list of ``Chunk`` instances.
        """


class MetadataChunker(ABC):
    """Abstract chunker for metadata content.

    Implementations convert structured metadata dictionaries into text
    chunks suitable for embedding.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of the chunking strategy.

        Returns:
            Strategy name string.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the chunking strategy.

        Returns:
            Version string.
        """

    @abstractmethod
    def build_text(
        self,
        metadata: dict[str, object],
        config: ChunkingConfig,
    ) -> list[Chunk]:
        """Convert metadata into text chunks.

        Args:
            metadata: Structured metadata dictionary.
            config: Chunking configuration.

        Returns:
            Ordered list of ``Chunk`` instances.
        """
