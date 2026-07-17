"""
LAION CLAP Embedding Provider.

Adapter for the laion-clap package to generate audio embeddings.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.embedding_provider import AudioEmbeddingProvider

logger = logging.getLogger(__name__)


class CLAPEmbedder(AudioEmbeddingProvider):
    """LAION CLAP audio embedding provider."""

    def __init__(self, enable_fusion: bool = False, checkpoint_path: Optional[str] = None) -> None:
        """Initialize the CLAP embedder.

        Args:
            enable_fusion: Whether to use the fused model variant.
            checkpoint_path: Optional path to local checkpoint.
        """
        self._enable_fusion = enable_fusion
        self._checkpoint_path = checkpoint_path
        self._model = None
        self._load_lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        return "laion-clap"

    @property
    def model_version(self) -> str:
        return "v1"

    @property
    def dimension(self) -> int:
        return 512

    @property
    def modality(self) -> Modality:
        return Modality.AUDIO

    async def _ensure_loaded(self) -> None:
        """Load the model lazily on first use."""
        if self._model is not None:
            return

        async with self._load_lock:
            if self._model is not None:
                return

            try:
                import laion_clap
            except ImportError:
                raise ImportError(
                    "laion-clap is not installed. Install it with: pip install laion-clap"
                ) from None

            logger.info("Loading LAION CLAP model...")

            def load_sync():
                model = laion_clap.CLAP_Module(enable_fusion=self._enable_fusion)
                if self._checkpoint_path:
                    model.load_ckpt(ckpt=self._checkpoint_path)
                else:
                    model.load_ckpt()
                return model

            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(None, load_sync)
            logger.info("LAION CLAP model loaded successfully.")

    async def embed_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Embed a single audio array.

        Args:
            audio_data: Numpy array of audio samples.
            sample_rate: Sample rate of the audio data.

        Returns:
            Numpy array of shape (1, 512).
        """
        await self._ensure_loaded()

        def embed_sync():
            # CLAP expects 48kHz audio. We resample if needed.
            if sample_rate != 48000:
                try:
                    import librosa
                    audio = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=48000)
                except ImportError:
                    raise ImportError("librosa is required for resampling.") from None
            else:
                audio = audio_data

            # Ensure mono (average channels if 2D)
            if audio.ndim > 1:
                audio = audio.mean(axis=0)

            # Ensure float32 in [-1, 1]
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
                if np.max(np.abs(audio)) > 1.0:
                    audio = audio / max(np.max(np.abs(audio)), 1.0)

            # Reshape to (1, T) for batch dimension
            audio_batch = audio.reshape(1, -1)
            
            return self._model.get_audio_embedding_from_data(x=audio_batch, use_tensor=False)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, embed_sync)

    async def embed_audio_file(self, file_path: str) -> np.ndarray:
        """Embed audio from a file.

        Args:
            file_path: Path to the audio file.

        Returns:
            Numpy array of shape (1, 512).
        """
        await self._ensure_loaded()

        def embed_sync():
            return self._model.get_audio_embedding_from_filelist(x=[file_path], use_tensor=False)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, embed_sync)

    async def embed_audio_batch(self, audio_list: list[np.ndarray], sample_rate: int) -> np.ndarray:
        """Embed a batch of audio arrays.

        Args:
            audio_list: List of audio numpy arrays.
            sample_rate: Sample rate of the audio data.

        Returns:
            Numpy array of shape (N, 512).
        """
        if not audio_list:
            return np.empty((0, self.dimension), dtype=np.float32)

        # For simplicity in this implementation, we just process sequentially
        # A more optimized version would pad all arrays to the same length and batch them
        vectors = []
        for audio in audio_list:
            vec = await self.embed_audio(audio, sample_rate)
            vectors.append(vec[0])
            
        return np.vstack(vectors)
