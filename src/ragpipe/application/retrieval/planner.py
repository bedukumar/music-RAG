"""Retrieval Planner for executing multi-modal searches."""

import asyncio
import time
from typing import Dict, List, Optional

from ragpipe.application.retrieval.base_pipeline import BaseRetrievalPipeline
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.events import FusionCompleted, ResultsRanked
from ragpipe.domain.retrieval.models import (
    RetrievalResult,
    RetrievalStage,
    SearchQuery,
    SearchResult,
)
from ragpipe.domain.retrieval.ports import (
    FusionStrategy,
    MetadataRetriever,
    PayloadLoader,
    QueryEmbedder,
    Reranker,
    VectorRetriever,
)


class RetrievalPlanner(BaseRetrievalPipeline):
    """Coordinates the retrieval stages across different modalities."""

    def __init__(
        self,
        event_bus: EventBus,
        embedders: Dict[Modality, QueryEmbedder],
        vector_retrievers: Dict[Modality, VectorRetriever],
        metadata_retriever: MetadataRetriever,
        fusion_strategies: Dict[str, FusionStrategy],
        reranker: Optional[Reranker],
        payload_loader: PayloadLoader,
    ):
        super().__init__(event_bus)
        self.embedders = embedders
        self.vector_retrievers = vector_retrievers
        self.metadata_retriever = metadata_retriever
        self.fusion_strategies = fusion_strategies
        self.reranker = reranker
        self.payload_loader = payload_loader

    async def plan_and_execute(self, query: SearchQuery) -> List[SearchResult]:
        """Execute the entire retrieval pipeline."""
        # 1. Understanding (Mocked as immediate for now)
        start_time = time.time()
        await self._emit_stage_completed(RetrievalStage.QUERY_NORMALIZATION, 0.0)
        await self._emit_stage_completed(RetrievalStage.MODALITY_SELECTION, 0.0)

        # 2. Parallel Retrieval Execution
        async def fetch_modality(modality: Modality) -> tuple[Modality, List[RetrievalResult]]:
            if modality == Modality.METADATA and not query.text:
                results = await self.metadata_retriever.search(query, query.top_k)
                return modality, results
            
            embedder = self.embedders.get(modality)
            retriever = self.vector_retrievers.get(modality)
            if embedder and retriever:
                embedding = await embedder.embed_query(query.text)
                if hasattr(retriever, "score_threshold") or modality == Modality.AUDIO:
                    from ragpipe.domain.retrieval.ports import AudioRetriever
                    if isinstance(retriever, AudioRetriever):
                        results = await retriever.search(
                            query_vector=embedding.vector,
                            top_k=query.top_k,
                            score_threshold=query.score_threshold,
                            include_similarity_score=query.include_similarity_score,
                            filters=query.filters.exact_matches,
                            query_text=query.text
                        )
                    else:
                        results = await retriever.search(
                            query_vector=embedding.vector, 
                            top_k=query.top_k, 
                            filters=query.filters.exact_matches,
                            query_text=query.text
                        )
                else:
                    results = await retriever.search(
                        embedding.vector, query.top_k, query.filters.exact_matches, query.text
                    )
                return modality, results
            return modality, []

        tasks = [fetch_modality(mod) for mod in query.active_modalities]
        gathered_results = await asyncio.gather(*tasks)
        modality_results: Dict[Modality, List[RetrievalResult]] = {
            mod: results for mod, results in gathered_results if results
        }

        await self._emit_stage_completed(
            RetrievalStage.VECTOR_RETRIEVAL, (time.time() - start_time) * 1000
        )

        # 3. Result Fusion
        start_time = time.time()
        fusion_strategy = self.fusion_strategies.get(query.fusion_strategy)
        if not fusion_strategy:
            # Fallback to first available or RRF
            fusion_strategy = list(self.fusion_strategies.values())[0]

        fused_results = fusion_strategy.fuse(modality_results, query.top_k)

        await self._emit_stage_completed(
            RetrievalStage.RESULT_FUSION, (time.time() - start_time) * 1000
        )
        await self.event_bus.publish(
            FusionCompleted(
                strategy=query.fusion_strategy,
                latency_ms=(time.time() - start_time) * 1000,
            )
        )

        # 4. Reranking
        if query.rerank and self.reranker:
            start_time = time.time()
            fused_results = await self.reranker.rerank(
                query.text, fused_results, query.top_k
            )
            await self._emit_stage_completed(
                RetrievalStage.RERANKING, (time.time() - start_time) * 1000
            )
            await self.event_bus.publish(
                ResultsRanked(latency_ms=(time.time() - start_time) * 1000)
            )

        # 5. Payload Loading
        start_time = time.time()
        search_results = await self.payload_loader.load_payloads(fused_results)
        await self._emit_stage_completed(
            RetrievalStage.PAYLOAD_LOADING, (time.time() - start_time) * 1000
        )

        return search_results
