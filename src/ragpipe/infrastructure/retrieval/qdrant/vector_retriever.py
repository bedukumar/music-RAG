"""Qdrant vector retriever implementation."""

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.retrieval.models import RetrievalResult
from ragpipe.domain.retrieval.ports import VectorRetriever


class QdrantVectorRetriever(VectorRetriever):
    """Adapter for retrieving vectors from Qdrant."""

    def __init__(self, vector_repository: VectorRepository, modality: Modality, collection_name: str):
        self.repo = vector_repository
        self._modality = modality
        self.collection_name = collection_name

    async def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[RetrievalResult]:
        """Search the Qdrant vector database."""
        # Using the existing QdrantVectorRepository's search method
        results_raw = await self.repo.search(
            collection=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            filters=filters
        )

        results = []
        for res in results_raw:
            payload = res.get("payload", {})
            results.append(
                RetrievalResult(
                    modality=self._modality,
                    chunk_id=res["id"],
                    media_id=payload.get("media_id", ""),
                    score=res["score"],
                    payload=payload
                )
            )

        return results

    @property
    def modality(self) -> Modality:
        return self._modality
