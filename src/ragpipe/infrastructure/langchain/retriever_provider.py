"""Retriever adapter backed by the existing RetrievalPlanner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ragpipe.application.retrieval.orchestrator import RetrievalOrchestrator
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import RetrievalResult, SearchFilters, SearchQuery

try:  # pragma: no cover - optional dependency
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
except ImportError:  # pragma: no cover - optional dependency
    Document = None  # type: ignore[assignment]
    BaseRetriever = object  # type: ignore[assignment]


@dataclass(frozen=True)
class RetrievalContext:
    """Normalized retrieval output used by prompts and citations."""

    documents: list[dict[str, Any]]
    media_ids: list[str]
    latency_ms: float
    raw_results: list[RetrievalResult]


class PlannerLangChainRetriever(BaseRetriever):  # type: ignore[misc]
    """LangChain-compatible wrapper around RetrievalPlanner."""

    def __init__(self, provider: "RetrieverProvider") -> None:
        super().__init__()
        object.__setattr__(self, "provider", provider)

    async def _aget_relevant_documents(self, query: str):  # pragma: no cover - thin adapter
        context = await self.provider.retrieve(query)
        if Document is None:
            return context.documents
        return [
            Document(
                page_content=item["content"],
                metadata=item["metadata"],
            )
            for item in context.documents
        ]

    def _get_relevant_documents(self, query: str):  # pragma: no cover - sync fallback
        raise RuntimeError("Use aget_relevant_documents() for the async retrieval pipeline")


class RetrieverProvider:
    """Adapter exposing RetrievalPlanner as a retriever."""

    def __init__(
        self,
        orchestrator: RetrievalOrchestrator,
        default_modalities: Optional[list[Modality]] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.default_modalities = default_modalities or [
            Modality.AUDIO,
            Modality.TRANSCRIPT,
            Modality.METADATA,
        ]
        self._langchain_retriever = PlannerLangChainRetriever(self)

    def as_retriever(self) -> PlannerLangChainRetriever:
        """Return a LangChain retriever wrapper."""

        return self._langchain_retriever

    async def retrieve(
        self,
        query_text: str,
        *,
        top_k: int = 8,
        score_threshold: float = 0.0,
        modalities: Optional[list[Modality]] = None,
        filters: Optional[dict[str, Any]] = None,
        tag_matches: Optional[list[str]] = None,
        rerank: bool = False,
        fusion_strategy: str = "rrf",
        include_similarity_score: bool = True,
    ) -> RetrievalContext:
        """Run the retrieval pipeline and normalize results."""

        search_query = SearchQuery(
            text=query_text,
            active_modalities=modalities or self.default_modalities,
            filters=SearchFilters(
                exact_matches=filters or {},
                tag_matches=tag_matches or [],
            ),
            top_k=top_k,
            score_threshold=score_threshold,
            include_similarity_score=include_similarity_score,
            rerank=rerank,
            fusion_strategy=fusion_strategy,
        )
        session = await self.orchestrator.execute_search(search_query)
        documents: list[dict[str, Any]] = []
        media_ids: list[str] = []
        for result in session.results:
            media_ids.append(result.media.media_id)
            for chunk in result.matched_chunks:
                content = chunk.content
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")
                    if not content.strip():
                        content = f"<binary chunk {len(chunk.content)} bytes>"
                documents.append(
                    {
                        "content": content,
                        "metadata": {
                            "media_id": result.media.media_id,
                            "title": result.media.title,
                            "media_type": result.media.media_type.value
                            if hasattr(result.media.media_type, "value")
                            else result.media.media_type,
                            "chunk_id": chunk.chunk_id,
                            "modality": chunk.modality.value,
                            "score": chunk.score,
                            "overall_score": result.overall_score,
                            "timestamps": chunk.timestamps,
                            "retrieval_latency_ms": session.latency_ms.get("total", 0.0),
                        },
                    }
                )

        return RetrievalContext(
            documents=documents,
            media_ids=media_ids,
            latency_ms=session.latency_ms.get("total", 0.0),
            raw_results=session.results,
        )
