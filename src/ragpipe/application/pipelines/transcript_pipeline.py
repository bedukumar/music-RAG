"""
Transcript processing pipeline.
"""

from __future__ import annotations

import re
import html
from datetime import datetime, timezone
from typing import Any

from ragpipe.application.pipelines.base_pipeline import BasePipeline
from ragpipe.domain.events.events import ChunkingCompleted, EmbeddingCompleted
from ragpipe.domain.models.chunk import ChunkingConfig
from ragpipe.domain.models.embedding import EmbeddingRecord, EmbeddingVersion
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.chunker import TextChunker
from ragpipe.domain.ports.embedding_provider import TextEmbeddingProvider
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.lock_manager import LockManager
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.exceptions import InvalidMediaError


class TranscriptPipeline(BasePipeline):
    """Pipeline for processing transcript/lyrics data."""

    def __init__(
        self,
        media_repository: MediaRepository,
        state_store: StateStore,
        vector_repository: VectorRepository,
        event_bus: EventBus,
        metrics: MetricsCollector,
        lock_manager: LockManager,
        embedding_version: EmbeddingVersion,
        text_embedder: TextEmbeddingProvider,
        text_chunker: TextChunker,
        chunking_config: ChunkingConfig,
    ) -> None:
        super().__init__(
            media_repository, state_store, vector_repository, event_bus, metrics, lock_manager, embedding_version
        )
        self.embedder = text_embedder
        self.chunker = text_chunker
        self.config = chunking_config

    @property
    def modality(self) -> Modality:
        return Modality.TRANSCRIPT

    async def _validate(self, context: dict[str, Any]) -> dict[str, Any]:
        media = await self.media_repo.get(context["media_id"])
        if not media:
            raise InvalidMediaError("Media not found")
            
        text = media.transcript_text
        if not text and hasattr(media, "lyrics"):
            text = media.lyrics
            
        if not text or not str(text).strip():
            raise InvalidMediaError("Media has no transcript or lyrics")
            
        context["raw_text"] = str(text)
        context["media"] = media
        return {"text_length": len(context["raw_text"])}

    async def _normalize(self, context: dict[str, Any]) -> dict[str, Any]:
        text = context["raw_text"]
        
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Unescape HTML entities
        text = html.unescape(text)
        # Normalize whitespace (replace multiple spaces/newlines with single space/newline)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        context["normalized_text"] = text
        return {"normalized_length": len(text)}

    async def _preprocess(self, context: dict[str, Any]) -> dict[str, Any]:
        # Passthrough - could add language detection, translating, etc.
        return {}

    async def _chunk(self, context: dict[str, Any]) -> dict[str, Any]:
        text = context["normalized_text"]
        media_id = context["media_id"]
        
        chunks = self.chunker.chunk_text(text, media_id, self.config)
        context["chunks"] = chunks
        
        await self.event_bus.publish(ChunkingCompleted(
            media_id=media_id,
            modality=self.modality,
            chunk_count=len(chunks),
            strategy=self.config.strategy_name,
        ))
        
        return {"chunks_created": len(chunks)}

    async def _embed(self, context: dict[str, Any]) -> dict[str, Any]:
        chunks = context["chunks"]
        
        texts_to_embed = [str(c.content) for c in chunks]
        embeddings = await self.embedder.embed_texts(texts_to_embed)
        
        context["embeddings"] = embeddings
        return {"embeddings_created": len(embeddings)}

    async def _post_process(self, context: dict[str, Any]) -> dict[str, Any]:
        # Embeddings usually normalized by the provider, but double check
        import numpy as np
        embeddings = context["embeddings"]
        if len(embeddings) > 0:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            normalized = embeddings / norms
            context["embeddings"] = normalized.astype(np.float32)
        return {"normalized": True}

    async def _store_vectors(self, context: dict[str, Any]) -> dict[str, Any]:
        chunks = context["chunks"]
        embeddings = context["embeddings"]
        media_id = context["media_id"]
        media = context["media"]
        
        collection_name = f"{self.modality.value}_{self.embedding_version.id}"
        
        vectors_to_upsert = []
        records = []
        now = datetime.now(timezone.utc)
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = self._generate_vector_id(media_id, chunk.chunk_index)
            
            payload = {
                "media_id": media_id,
                "media_type": media.media_type.value,
                "chunk_index": chunk.chunk_index,
                "text_content": str(chunk.content),
            }
            payload.update(media.metadata_fields)
            
            vectors_to_upsert.append((vector_id, embedding.tolist(), payload))
            
            record = EmbeddingRecord(
                id=f"rec-{vector_id}",
                media_id=media_id,
                modality=self.modality,
                version_id=self.embedding_version.id,
                chunk_index=chunk.chunk_index,
                vector_id=vector_id,
                chunk_metadata=chunk.metadata,
                created_at=now,
            )
            records.append(record)
            
        if vectors_to_upsert:
            await self.vector_repo.upsert_vectors(collection_name, vectors_to_upsert)
            
        for record in records:
            await self.state_store.save_embedding_record(record)
            
        await self.event_bus.publish(EmbeddingCompleted(
            media_id=media_id,
            modality=self.modality,
            version_id=self.embedding_version.id,
            vector_count=len(records),
            duration_ms=0.0,
        ))
            
        return {"vectors_stored": len(records)}
