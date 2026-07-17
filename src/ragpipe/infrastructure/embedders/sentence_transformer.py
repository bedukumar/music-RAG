"""
Sentence Transformers Text Embedding Provider.

Adapter for the sentence-transformers package to generate text embeddings.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.embedding_provider import TextEmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder(TextEmbeddingProvider):
    """Sentence Transformers text embedding provider."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model_version: str = "v1",
        modality: Modality = Modality.TRANSCRIPT,
    ) -> None:
        """Initialize the Sentence Transformer embedder.

        Args:
            model_name: Name of the sentence-transformers model.
            model_version: Version identifier for the model.
            modality: The modality this embedder handles (TRANSCRIPT or METADATA).
        """
        self._model_name = model_name
        self._model_version = model_version
        self._modality = modality
        self._model = None
        self._dimension = 0
        self._load_lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def modality(self) -> Modality:
        return self._modality

    async def _ensure_loaded(self) -> None:
        """Load the model lazily on first use."""
        if self._model is not None:
            return

        async with self._load_lock:
            if self._model is not None:
                return

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers is not installed. Install it with: pip install sentence-transformers"
                ) from None

            logger.info("Loading Sentence Transformer model %s...", self._model_name)

            def load_sync():
                model = SentenceTransformer(self._model_name)
                # Infer dimension
                dim = model.get_sentence_embedding_dimension()
                return model, dim

            loop = asyncio.get_event_loop()
            self._model, self._dimension = await loop.run_in_executor(None, load_sync)
            logger.info("Sentence Transformer model loaded successfully (dimension: %d).", self._dimension)

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Numpy array of shape (1, dimension).
        """
        await self._ensure_loaded()

        def embed_sync():
            # Return numpy array, normalize embeddings
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.reshape(1, -1)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, embed_sync)

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of text strings.

        Args:
            texts: List of strings to embed.

        Returns:
            Numpy array of shape (N, dimension).
        """
        if not texts:
            # If not loaded, we can't know dimension synchronously, but we assume it's loaded 
            # if we are doing batch embedding. Otherwise we just return empty array of dim 0.
            dim = self._dimension if self._dimension > 0 else 384
            return np.empty((0, dim), dtype=np.float32)

        await self._ensure_loaded()

        def embed_sync():
            # encode() naturally handles batches
            return self._model.encode(texts, normalize_embeddings=True)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, embed_sync)
