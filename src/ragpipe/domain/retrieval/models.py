"""Retrieval domain models for the RAG Data Ingestion Platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from ragpipe.domain.models.modality import Modality


class RetrievalStage(Enum):
    """Execution stages of the retrieval pipeline."""
    VALIDATION = "validation"
    QUERY_NORMALIZATION = "query_normalization"
    QUERY_EXPANSION = "query_expansion"
    MODALITY_SELECTION = "modality_selection"
    EMBEDDING_GENERATION = "embedding_generation"
    VECTOR_RETRIEVAL = "vector_retrieval"
    PAYLOAD_LOADING = "payload_loading"
    RESULT_FUSION = "result_fusion"
    RERANKING = "reranking"
    POST_PROCESSING = "post_processing"
    RESPONSE_BUILDING = "response_building"


@dataclass(frozen=True)
class SearchFilters:
    """Filters to apply during retrieval."""
    exact_matches: dict[str, Any] = field(default_factory=dict)
    tag_matches: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchQuery:
    """Encapsulates a parsed user query."""
    text: str
    active_modalities: list[Modality] = field(default_factory=list)
    filters: SearchFilters = field(default_factory=SearchFilters)
    top_k: int = 10
    score_threshold: float = 0.0
    include_similarity_score: bool = True
    rerank: bool = False
    fusion_strategy: str = "rrf"


@dataclass(frozen=True)
class QueryEmbedding:
    """Vectors generated for a search query."""
    modality: Modality
    vector: list[float]


@dataclass(frozen=True)
class RetrievedChunk:
    """A specific chunk retrieved from the vector store."""
    chunk_id: str
    modality: Modality
    score: float
    content: str
    timestamps: Optional[tuple[float, float]] = None


@dataclass(frozen=True)
class RetrievedMedia:
    """Rich payload representation of a matched media item."""
    media_id: str
    title: str
    media_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    """Container for matched media and chunks."""
    media: RetrievedMedia
    matched_chunks: list[RetrievedChunk] = field(default_factory=list)
    overall_score: float = 0.0


@dataclass(frozen=True)
class RetrievalResult:
    """Intermediate result from a single retriever."""
    modality: Modality
    chunk_id: str
    media_id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchSession:
    """Container for an entire search request's context and results."""
    session_id: str
    query: SearchQuery
    results: list[SearchResult] = field(default_factory=list)
    latency_ms: dict[str, float] = field(default_factory=dict)
