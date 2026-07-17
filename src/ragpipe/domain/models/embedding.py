"""Embedding domain models for the RAG Data Ingestion Platform.

This module contains the ``EmbeddingVersion`` (schema for a set of embeddings)
and ``EmbeddingRecord`` (individual vector record) value objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ragpipe.domain.exceptions import ValidationError
from ragpipe.domain.models.modality import Modality


@dataclass(frozen=True)
class EmbeddingVersion:
    """Describes the embedding schema and model for a modality.

    An embedding version captures *how* embeddings were generated — the model,
    its version, the chunking strategy, and the vector dimension. Only one
    version per modality is active at any time; migrations switch from one
    version to another.

    Attributes:
        id: Unique version identifier (UUID-4 string).
        modality: The modality this version applies to.
        model_name: Name of the embedding model (e.g. ``openai/text-embedding-3-small``).
        model_version: Semantic version of the model.
        dimension: Vector dimensionality.
        chunking_strategy: Chunking strategy identifier.
        chunking_version: Chunking strategy version string.
        pipeline_version: Overall pipeline version string.
        is_active: Whether this version is the current active version.
        created_at: Timestamp of creation.
    """

    id: str
    modality: Modality
    model_name: str
    model_version: str
    dimension: int
    chunking_strategy: str
    chunking_version: str
    pipeline_version: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "EmbeddingVersion id must not be empty")
        if not self.model_name or not self.model_name.strip():
            raise ValidationError("model_name", "Model name must not be empty")
        if self.dimension <= 0:
            raise ValidationError(
                "dimension", f"Dimension must be positive, got {self.dimension}"
            )

    @classmethod
    def create(
        cls,
        modality: Modality,
        model_name: str,
        model_version: str,
        dimension: int,
        chunking_strategy: str,
        chunking_version: str,
        pipeline_version: str,
        is_active: bool = True,
    ) -> EmbeddingVersion:
        """Factory method to create a new ``EmbeddingVersion`` with a generated UUID.

        Args:
            modality: Target modality.
            model_name: Embedding model name.
            model_version: Embedding model version.
            dimension: Vector dimensionality.
            chunking_strategy: Name of the chunking strategy.
            chunking_version: Version of the chunking strategy.
            pipeline_version: Overall pipeline version.
            is_active: Whether to mark as active on creation.

        Returns:
            A fully initialised ``EmbeddingVersion`` instance.
        """
        return cls(
            id=str(uuid.uuid4()),
            modality=modality,
            model_name=model_name,
            model_version=model_version,
            dimension=dimension,
            chunking_strategy=chunking_strategy,
            chunking_version=chunking_version,
            pipeline_version=pipeline_version,
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class EmbeddingRecord:
    """Maps a single chunk to its vector in the vector database.

    Attributes:
        id: Unique record identifier (UUID-4 string).
        media_id: The parent media item.
        modality: Which modality this embedding belongs to.
        version_id: The ``EmbeddingVersion.id`` under which this was generated.
        chunk_index: The index of the chunk within the media item.
        vector_id: The vector identifier in the external vector database.
        chunk_metadata: Metadata payload stored alongside the vector.
        created_at: Timestamp of creation.
    """

    id: str
    media_id: str
    modality: Modality
    version_id: str
    chunk_index: int
    vector_id: str
    chunk_metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "EmbeddingRecord id must not be empty")
        if not self.media_id:
            raise ValidationError("media_id", "media_id must not be empty")
        if not self.vector_id:
            raise ValidationError("vector_id", "vector_id must not be empty")
        if self.chunk_index < 0:
            raise ValidationError(
                "chunk_index",
                f"chunk_index must be non-negative, got {self.chunk_index}",
            )

    @classmethod
    def create(
        cls,
        media_id: str,
        modality: Modality,
        version_id: str,
        chunk_index: int,
        vector_id: str,
        chunk_metadata: dict[str, object] | None = None,
    ) -> EmbeddingRecord:
        """Factory method to create a new ``EmbeddingRecord`` with a generated UUID.

        Args:
            media_id: Parent media item identifier.
            modality: Modality of the embedding.
            version_id: Embedding version used.
            chunk_index: Index of the chunk.
            vector_id: ID of the vector in the vector DB.
            chunk_metadata: Optional metadata dict.

        Returns:
            A fully initialised ``EmbeddingRecord`` instance.
        """
        return cls(
            id=str(uuid.uuid4()),
            media_id=media_id,
            modality=modality,
            version_id=version_id,
            chunk_index=chunk_index,
            vector_id=vector_id,
            chunk_metadata=chunk_metadata or {},
            created_at=datetime.now(timezone.utc),
        )
