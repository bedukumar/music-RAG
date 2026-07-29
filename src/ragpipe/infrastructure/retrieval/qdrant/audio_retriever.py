"""Qdrant specialized audio retriever implementation."""

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.retrieval.models import RetrievalResult
from ragpipe.domain.retrieval.ports import AudioRetriever


class QdrantAudioRetriever(AudioRetriever):
    """Adapter for retrieving audio vectors from Qdrant using strict Cosine Similarity."""

    def __init__(self, vector_repository: VectorRepository, collection_name: str):
        self.repo = vector_repository
        self.collection_name = collection_name
        self._modality = Modality.AUDIO

    async def search(
        self, 
        query_vector: list[float], 
        top_k: int, 
        score_threshold: float = 0.0,
        include_similarity_score: bool = True,
        filters: dict | None = None,
        query_text: str | None = None
    ) -> list[RetrievalResult]:
        """Search the Qdrant vector database using Cosine distance.
        
        Qdrant's Cosine distance returns scores in [-1.0, 1.0].
        This maps them to [0, 1] using (score + 1) / 2 and applies the threshold.
        """
        # We fetch potentially more results if filtering is high, but we'll stick to top_k 
        # for the database query and then filter post-retrieval as per requirements.
        # Note: In a production setting, you'd pass the threshold directly to Qdrant's query_points 
        # using `score_threshold` parameter if the native SDK supports it.
        results_raw = await self.repo.search(
            collection=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            filters=filters
        )

        results = []
        for res in results_raw:
            raw_score = float(res["score"])
            
            # Map Qdrant Cosine score [-1, 1] to [0, 1]
            normalized_score = (raw_score + 1.0) / 2.0
            
            # Discard results below threshold
            if normalized_score < score_threshold:
                continue

            payload = res.get("payload", {})
            
            # Conditionally include the score
            final_score = normalized_score if include_similarity_score else 0.0
            
            results.append(
                RetrievalResult(
                    modality=self._modality,
                    chunk_id=res["id"],
                    media_id=payload.get("media_id", ""),
                    score=final_score,
                    payload=payload
                )
            )

        return results

    @property
    def modality(self) -> Modality:
        return self._modality
