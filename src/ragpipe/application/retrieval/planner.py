"""Retrieval Planner for executing multi-modal searches."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from ragpipe.application.retrieval.base_pipeline import BaseRetrievalPipeline
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.events import FusionCompleted, ResultsRanked
from ragpipe.domain.retrieval.models import (
    QueryEmbedding,
    RetrievalResult,
    RetrievalStage,
    SearchQuery,
    SearchResult,
)
from ragpipe.domain.retrieval.ports import (
    AudioRetriever,
    FusionStrategy,
    MetadataRetriever,
    PayloadLoader,
    QueryEmbedder,
    Reranker,
    VectorRetriever,
)

logger = logging.getLogger(__name__)


class RetrievalPlanner(BaseRetrievalPipeline):
    """Coordinates the retrieval stages across different modalities.

    Optimizations applied:
    - Query is embedded **once per unique embedder** at the start of the
      pipeline. Results are shared across all modalities that use the same
      underlying model (e.g. TRANSCRIPT and METADATA both share the
      SentenceTransformer embedder).
    - All modality retrievals execute in parallel via asyncio.gather.
    - Every stage is individually timed and returned for observability.
    """

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

    async def plan_and_execute(
        self, query: SearchQuery
    ) -> Tuple[List[SearchResult], Dict[str, float]]:
        """Execute the entire retrieval pipeline.

        Returns:
            A tuple of (search_results, latency_breakdown_ms) where
            latency_breakdown_ms contains per-stage timings.
        """
        stage_latencies: Dict[str, float] = {}

        await self._emit_stage_completed(RetrievalStage.QUERY_NORMALIZATION, 0.0)
        await self._emit_stage_completed(RetrievalStage.MODALITY_SELECTION, 0.0)

        # ------------------------------------------------------------------ #
        # Stage 1: Embed the query ONCE per unique embedder instance.         #
        # TRANSCRIPT and METADATA share the same SentenceTransformer model,  #
        # so we deduplicate by embedder identity before launching tasks.      #
        # ------------------------------------------------------------------ #
        embed_start = time.perf_counter()
        precomputed: Dict[Modality, QueryEmbedding] = {}
        if query.text:
            # Build a map from embedder id → (first modality, embedder) so we
            # call embed_query exactly once per distinct model object.
            seen_embedder_ids: Dict[int, Modality] = {}
            representative_mod: Dict[int, Modality] = {}
            for mod in query.active_modalities:
                emb = self.embedders.get(mod)
                if emb is None:
                    continue
                eid = id(emb)
                if eid not in seen_embedder_ids:
                    seen_embedder_ids[eid] = mod
                    representative_mod[eid] = mod

            # Fire all unique embed_query calls concurrently.
            unique_embedder_list = [
                (mod, self.embedders[mod])
                for eid, mod in representative_mod.items()
                if mod in self.embedders
            ]
            embed_results = await asyncio.gather(
                *(emb.embed_query(query.text) for _, emb in unique_embedder_list),
                return_exceptions=False,
            )

            # Build: unique modality → embedding result.
            rep_mod_to_embedding: Dict[Modality, QueryEmbedding] = {
                mod: result
                for (mod, _), result in zip(unique_embedder_list, embed_results)
            }

            # Map every active modality to the representative's embedding.
            for mod in query.active_modalities:
                emb = self.embedders.get(mod)
                if emb is None:
                    continue
                eid = id(emb)
                rep_mod = representative_mod.get(eid)
                if rep_mod is not None and rep_mod in rep_mod_to_embedding:
                    precomputed[mod] = rep_mod_to_embedding[rep_mod]

        stage_latencies["query_embedding_ms"] = (time.perf_counter() - embed_start) * 1000

        # ------------------------------------------------------------------ #
        # Stage 2: Parallel retrieval across all active modalities.           #
        # Pre-computed embeddings are passed in — no repeated model calls.   #
        # ------------------------------------------------------------------ #
        retrieval_start = time.perf_counter()

        async def fetch_modality(
            modality: Modality,
        ) -> Tuple[Modality, List[RetrievalResult], float]:
            t0 = time.perf_counter()
            if modality == Modality.METADATA and not query.text:
                results = await self.metadata_retriever.search(query, query.top_k)
                return modality, results, (time.perf_counter() - t0) * 1000

            embedding = precomputed.get(modality)
            retriever = self.vector_retrievers.get(modality)
            if embedding is None or retriever is None:
                return modality, [], (time.perf_counter() - t0) * 1000

            if isinstance(retriever, AudioRetriever):
                results = await retriever.search(
                    query_vector=embedding.vector,
                    top_k=query.top_k,
                    score_threshold=query.score_threshold,
                    include_similarity_score=query.include_similarity_score,
                    filters=query.filters.exact_matches,
                    query_text=query.text,
                )
            elif hasattr(retriever, "search"):
                try:
                    results = await retriever.search(
                        query_vector=embedding.vector,
                        top_k=query.top_k,
                        filters=query.filters.exact_matches,
                        query_text=query.text,
                    )
                except TypeError:
                    results = await retriever.search(
                        embedding.vector,
                        query.top_k,
                        query.filters.exact_matches,
                        query.text,
                    )
            else:
                results = []

            return modality, results, (time.perf_counter() - t0) * 1000

        gathered = await asyncio.gather(
            *(fetch_modality(mod) for mod in query.active_modalities)
        )

        modality_results: Dict[Modality, List[RetrievalResult]] = {}
        for modality, results, mod_latency in gathered:
            if results:
                modality_results[modality] = results
            stage_latencies[f"{modality.value}_retrieval_ms"] = mod_latency

        stage_latencies["total_retrieval_ms"] = (time.perf_counter() - retrieval_start) * 1000
        await self._emit_stage_completed(
            RetrievalStage.VECTOR_RETRIEVAL, stage_latencies["total_retrieval_ms"]
        )

        # ------------------------------------------------------------------ #
        # Stage 3: Result Fusion                                               #
        # ------------------------------------------------------------------ #
        fusion_start = time.perf_counter()
        fusion_strategy = self.fusion_strategies.get(query.fusion_strategy)
        if not fusion_strategy:
            fusion_strategy = list(self.fusion_strategies.values())[0]

        fused_results = fusion_strategy.fuse(modality_results, query.top_k)
        stage_latencies["fusion_ms"] = (time.perf_counter() - fusion_start) * 1000

        await self._emit_stage_completed(
            RetrievalStage.RESULT_FUSION, stage_latencies["fusion_ms"]
        )
        await self.event_bus.publish(
            FusionCompleted(
                strategy=query.fusion_strategy,
                latency_ms=stage_latencies["fusion_ms"],
            )
        )

        # ------------------------------------------------------------------ #
        # Stage 4: Reranking (top-N candidates only)                          #
        # ------------------------------------------------------------------ #
        stage_latencies["reranking_ms"] = 0.0
        if query.rerank and self.reranker:
            rerank_start = time.perf_counter()
            # Rerank only the fused top candidates (capped at 50) to avoid
            # passing every retrieved result through the cross-encoder.
            candidates_to_rerank = fused_results[:50]
            fused_results = await self.reranker.rerank(
                query.text, candidates_to_rerank, query.top_k
            )
            stage_latencies["reranking_ms"] = (time.perf_counter() - rerank_start) * 1000
            await self._emit_stage_completed(
                RetrievalStage.RERANKING, stage_latencies["reranking_ms"]
            )
            await self.event_bus.publish(
                ResultsRanked(latency_ms=stage_latencies["reranking_ms"])
            )

        # ------------------------------------------------------------------ #
        # Stage 5: Payload Loading                                            #
        # ------------------------------------------------------------------ #
        payload_start = time.perf_counter()
        search_results = await self.payload_loader.load_payloads(fused_results)
        stage_latencies["payload_loading_ms"] = (time.perf_counter() - payload_start) * 1000
        await self._emit_stage_completed(
            RetrievalStage.PAYLOAD_LOADING, stage_latencies["payload_loading_ms"]
        )

        stage_latencies["total_ms"] = sum(
            v for k, v in stage_latencies.items() if not k.startswith("total_") and k != "total_ms"
        )

        logger.debug(
            "retrieval_stage_breakdown: %s",
            {k: round(v, 2) for k, v in stage_latencies.items()},
        )

        return search_results, stage_latencies
