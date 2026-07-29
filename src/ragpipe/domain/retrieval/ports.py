"""Retrieval ports (interfaces) for the RAG Data Ingestion Platform."""

from abc import ABC, abstractmethod
from typing import Sequence

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import (
    QueryEmbedding,
    RetrievalResult,
    RetrievedMedia,
    SearchQuery,
    SearchResult,
)


class QueryEmbedder(ABC):
    """Abstract interface for embedding search queries."""

    @abstractmethod
    async def embed_query(self, query: str) -> QueryEmbedding:
        """Generate an embedding for the given query."""
        pass

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """The modality this embedder targets."""
        pass


class VectorRetriever(ABC):
    """Abstract interface for retrieving vectors."""

    @abstractmethod
    async def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None, query_text: str | None = None
    ) -> list[RetrievalResult]:
        """Search the vector database."""
        pass

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """The modality this retriever handles."""
        pass


class AudioRetriever(VectorRetriever):
    """Abstract interface specifically for Audio retrieval operations."""
    
    @abstractmethod
    async def search(
        self, 
        query_vector: list[float], 
        top_k: int, 
        score_threshold: float = 0.0,
        include_similarity_score: bool = True,
        filters: dict | None = None,
        query_text: str | None = None
    ) -> list[RetrievalResult]:
        """Search the audio vector database.
        
        Args:
            query_vector: L2-normalized query vector.
            top_k: Max number of results.
            score_threshold: Minimum normalized similarity score [0,1].
            include_similarity_score: Whether to keep the score in output.
            filters: Optional metadata filters.
        """
        pass


class MetadataRetriever(ABC):
    """Abstract interface for retrieving via metadata filters."""

    @abstractmethod
    async def search(
        self, query: SearchQuery, top_k: int
    ) -> list[RetrievalResult]:
        """Search the metadata store (e.g., Qdrant payloads)."""
        pass


class FusionStrategy(ABC):
    """Abstract interface for result fusion."""

    @abstractmethod
    def fuse(
        self, modality_results: dict[Modality, list[RetrievalResult]], top_k: int
    ) -> list[RetrievalResult]:
        """Fuse results from multiple modalities."""
        pass


class Reranker(ABC):
    """Abstract interface for re-ranking results."""

    @abstractmethod
    async def rerank(
        self, query: str, candidates: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        """Re-rank candidate results based on the query."""
        pass


class PayloadLoader(ABC):
    """Abstract interface for hydrating media payloads."""

    @abstractmethod
    async def load_payloads(
        self, results: list[RetrievalResult]
    ) -> list[SearchResult]:
        """Load rich media objects for the retrieved chunks."""
        pass


class SearchHistoryRepository(ABC):
    """Abstract interface for storing search history."""

    @abstractmethod
    async def save_search(self, session_data: dict) -> None:
        """Persist a search session."""
        pass
