"""LangChain-friendly tool implementations for conversational search."""

from __future__ import annotations

import time
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from ragpipe.application.services.collection_service import CollectionService
from ragpipe.application.services.media_query_service import MediaQueryService
from ragpipe.application.services.status_service import StatusService
from ragpipe.domain.models.conversation import ConversationMemory, ToolInvocation, ToolResult
from ragpipe.domain.models.modality import Modality
from ragpipe.infrastructure.langchain.retriever_provider import RetrieverProvider

try:  # pragma: no cover - optional dependency
    from langchain_core.tools import StructuredTool
except ImportError:  # pragma: no cover - optional dependency
    StructuredTool = None  # type: ignore[assignment]


@dataclass
class ToolExecutionContext:
    """Runtime context passed to conversation tools."""

    conversation_id: str
    user_message: str
    memory: ConversationMemory
    modalities: list[Modality]
    filters: dict[str, Any] = field(default_factory=dict)
    tag_matches: list[str] = field(default_factory=list)
    top_k: int = 8
    score_threshold: float = 0.0
    include_similarity_score: bool = True
    rerank: bool = True
    fusion_strategy: str = "rrf"
    search_mode: str = "hybrid"
    page: int = 1
    page_size: int = 10


class BaseConversationTool:
    """Common tool wrapper."""

    name: str = ""
    description: str = ""

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        raise NotImplementedError

    def to_langchain_tool(self):  # pragma: no cover - optional wrapper
        if StructuredTool is None:
            return None

        async def _invoke(payload: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError(
                f"{self.name} expects execution through ToolExecutor in this backend"
            )

        return StructuredTool.from_function(
            coroutine=_invoke,
            name=self.name,
            description=self.description,
        )


class SearchTool(BaseConversationTool):
    name = "SearchTool"
    description = "Search music, media, lyrics, transcripts, or metadata using the retrieval pipeline."

    def __init__(self, retriever_provider: RetrieverProvider) -> None:
        self.retriever_provider = retriever_provider

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        try:
            retrieval = await self.retriever_provider.retrieve(
                context.user_message,
                top_k=context.top_k,
                score_threshold=context.score_threshold,
                modalities=context.modalities,
                filters=context.filters,
                tag_matches=context.tag_matches,
                rerank=context.rerank,
                fusion_strategy=context.fusion_strategy,
                include_similarity_score=context.include_similarity_score,
            )
            start_index = max(context.page - 1, 0) * context.page_size
            end_index = start_index + context.page_size
            paged_documents = retrieval.documents[start_index:end_index]
            paged_media_ids = list(
                dict.fromkeys(
                    [
                        str(item.get("metadata", {}).get("media_id"))
                        for item in paged_documents
                        if item.get("metadata", {}).get("media_id")
                    ]
                )
            )
            payload = {
                "retrieved_media_ids": paged_media_ids,
                "citations": paged_documents,
                "latency_ms": retrieval.latency_ms,
                "results": paged_documents,
                "search_mode": context.search_mode,
                "page": context.page,
                "page_size": context.page_size,
            }
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )


class MediaDetailsTool(BaseConversationTool):
    name = "MediaDetailsTool"
    description = "Fetch detailed metadata for a media item by ID."

    def __init__(self, media_query_service: MediaQueryService) -> None:
        self.media_query_service = media_query_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        media_id = self._extract_media_id(context)
        try:
            payload = await self.media_query_service.get_media_details(str(media_id))
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_media_id(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("media_id")
        if candidate:
            return str(candidate)
        match = re.search(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            context.user_message,
            re.IGNORECASE,
        )
        if match:
            return match.group(0)
        return context.user_message.strip()


class SearchByArtistTool(BaseConversationTool):
    name = "SearchByArtistTool"
    description = "Search media by artist name."

    def __init__(self, media_query_service: MediaQueryService) -> None:
        self.media_query_service = media_query_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        artist = self._extract_artist(context)
        try:
            payload = await self.media_query_service.search_by_artist(
                artist,
                top_k=context.top_k,
                score_threshold=context.score_threshold,
                modalities=context.modalities,
            )
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_artist(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("artist")
        if candidate:
            return str(candidate)
        match = re.search(r"\b(?:by|artist|singer|band)\s+(?:is\s+)?(.+)$", context.user_message, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ?!.,")
        return context.user_message.strip()


class SearchByGenreTool(BaseConversationTool):
    name = "SearchByGenreTool"
    description = "Search media by genre."

    def __init__(self, media_query_service: MediaQueryService) -> None:
        self.media_query_service = media_query_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        genre = self._extract_genre(context)
        try:
            payload = await self.media_query_service.search_by_genre(
                genre,
                top_k=context.top_k,
                score_threshold=context.score_threshold,
            )
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_genre(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("genre")
        if candidate:
            return str(candidate)
        match = re.search(r"\bgenre\s*(?:is|:)?\s*(.+)$", context.user_message, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ?!.,")
        return context.user_message.strip()


class SearchByYearTool(BaseConversationTool):
    name = "SearchByYearTool"
    description = "Search media by release year or year-like metadata."

    def __init__(self, media_query_service: MediaQueryService) -> None:
        self.media_query_service = media_query_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        year = self._extract_year(context)
        try:
            payload = await self.media_query_service.search_by_year(
                year,
                top_k=context.top_k,
                score_threshold=context.score_threshold,
            )
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_year(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("year")
        if candidate:
            return str(candidate)
        match = re.search(r"\b(19|20)\d{2}\b", context.user_message)
        if match:
            return match.group(0)
        return context.user_message.strip()


class SimilarSongsTool(BaseConversationTool):
    name = "SimilarSongsTool"
    description = "Find songs or media that are similar to a seed item."

    def __init__(
        self,
        media_query_service: MediaQueryService,
        retriever_provider: RetrieverProvider,
    ) -> None:
        self.media_query_service = media_query_service
        self.retriever_provider = retriever_provider

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        seed = self._extract_seed(context)
        try:
            retrieval = await self.retriever_provider.retrieve(
                seed,
                top_k=context.top_k,
                score_threshold=context.score_threshold,
                modalities=context.modalities,
                filters=context.filters,
                tag_matches=context.tag_matches,
                rerank=True,
                fusion_strategy=context.fusion_strategy,
                include_similarity_score=context.include_similarity_score,
            )
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result={
                    "retrieved_media_ids": retrieval.media_ids,
                    "citations": retrieval.documents,
                    "latency_ms": retrieval.latency_ms,
                },
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_seed(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("seed")
        if candidate:
            return str(candidate)
        match = re.search(r"\bsimilar to\s+(.+)$", context.user_message, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ?!.,")
        return context.user_message.strip()


class PipelineStatusTool(BaseConversationTool):
    name = "PipelineStatusTool"
    description = "Inspect the processing status of a media item or job."

    def __init__(self, status_service: StatusService) -> None:
        self.status_service = status_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        media_id = self._extract_media_id(context)
        try:
            payload = await self.status_service.get_pipeline_status(media_id)
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )

    def _extract_media_id(self, context: ToolExecutionContext) -> str:
        candidate = context.filters.get("media_id")
        if candidate:
            return str(candidate)
        match = re.search(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            context.user_message,
            re.IGNORECASE,
        )
        if match:
            return match.group(0)
        return context.user_message.strip()


class CollectionStatsTool(BaseConversationTool):
    name = "CollectionStatsTool"
    description = "Summarize vector collection statistics."

    def __init__(self, collection_service: CollectionService) -> None:
        self.collection_service = collection_service

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        try:
            payload = await self.collection_service.get_collection_stats()
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )


class ConversationHistoryTool(BaseConversationTool):
    name = "ConversationHistoryTool"
    description = "Retrieve prior messages from the current conversation."

    def __init__(
        self,
        history_loader: Callable[[str], Awaitable[dict[str, Any]]],
    ) -> None:
        self.history_loader = history_loader

    async def run(self, context: ToolExecutionContext) -> ToolResult:
        start = time.perf_counter()
        try:
            payload = await self.history_loader(context.conversation_id)
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=True,
                result=payload,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                invocation_id="",
                tool_name=self.name,
                success=False,
                result={},
                error=str(exc),
                latency_ms=(time.perf_counter() - start) * 1000,
            )
