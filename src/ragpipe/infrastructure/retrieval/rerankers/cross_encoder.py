"""Cross-Encoder reranker."""

from ragpipe.domain.retrieval.models import RetrievalResult
from ragpipe.domain.retrieval.ports import Reranker


class MockCrossEncoderReranker(Reranker):
    """A mock reranker to fulfill the architecture without heavy dependencies."""

    async def rerank(
        self, query: str, candidates: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        """Mock re-ranking (just sorts by original score)."""
        # In a real implementation, we would format query + text and pass to a cross-encoder model
        ranked = sorted(candidates, key=lambda x: x.score, reverse=True)
        return ranked[:top_k]
