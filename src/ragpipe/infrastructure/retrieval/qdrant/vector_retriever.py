"""Qdrant vector retriever implementation."""

import logging

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.retrieval.models import RetrievalResult
from ragpipe.domain.retrieval.ports import VectorRetriever

logger = logging.getLogger(__name__)


class QdrantVectorRetriever(VectorRetriever):
    """Adapter for retrieving vectors from Qdrant."""

    def __init__(self, vector_repository: VectorRepository, modality: Modality, collection_name: str):
        self.repo = vector_repository
        self._modality = modality
        self.collection_name = collection_name

    async def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None, query_text: str | None = None
    ) -> list[RetrievalResult]:
        """Search the Qdrant vector database using a Hybrid Semantic + Keyword approach."""
        # 1. Semantic Vector Search
        results_raw = await self.repo.search(
            collection=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            filters=filters
        )
        
        semantic_results = []
        for res in results_raw:
            payload = res.get("payload", {})
            semantic_results.append(
                RetrievalResult(
                    modality=self._modality,
                    chunk_id=res["id"],
                    media_id=payload.get("media_id", ""),
                    score=res["score"],
                    payload=payload
                )
            )

        # 2. Full-Text Keyword Search
        keyword_results = []
        if query_text:
            from qdrant_client.http import models
            import asyncio

            must_conditions = [models.FieldCondition(key="text_content", match=models.MatchText(text=query_text))]
            if filters:
                for k, v in filters.items():
                    must_conditions.append(models.FieldCondition(key=k, match=models.MatchValue(value=v)))
            
            qdrant_filter = models.Filter(must=must_conditions)
            
            def sync_scroll():
                res, _ = self.repo._client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=qdrant_filter,
                    limit=top_k,
                    with_payload=True
                )
                return res
            
            loop = asyncio.get_event_loop()
            try:
                text_records = await loop.run_in_executor(None, sync_scroll)
                for rec in text_records:
                    payload = rec.payload or {}
                    keyword_results.append(
                        RetrievalResult(
                            modality=self._modality,
                            chunk_id=str(rec.id),
                            media_id=payload.get("media_id", ""),
                            score=1.0,
                            payload=payload
                        )
                    )
            except Exception as e:
                # Fallback if scroll fails (e.g. index not ready)
                logger.warning("keyword_search_failed for collection %s: %s", self.collection_name, str(e))

        logger.debug("hybrid_search_results: semantic_count=%d, keyword_count=%d", len(semantic_results), len(keyword_results))
        # 3. Native RRF Fusion
        score_map = {}
        result_map = {}
        
        for rank, res in enumerate(semantic_results, start=1):
            cid = res.chunk_id
            score_map[cid] = 1.0 / (60 + rank)
            result_map[cid] = res
            
        for rank, res in enumerate(keyword_results, start=1):
            cid = res.chunk_id
            if cid not in score_map:
                score_map[cid] = 0.0
                result_map[cid] = res
            # Boost score mathematically if they matched both!
            score_map[cid] += 1.0 / (60 + rank)
            
        # Sort by accumulated hybrid score
        fused = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        
        final_results = []
        for cid, score in fused[:top_k]:
            res = result_map[cid]
            final_results.append(
                RetrievalResult(
                    modality=res.modality,
                    chunk_id=res.chunk_id,
                    media_id=res.media_id,
                    score=score,
                    payload=res.payload
                )
            )
            
        return final_results

    @property
    def modality(self) -> Modality:
        return self._modality
