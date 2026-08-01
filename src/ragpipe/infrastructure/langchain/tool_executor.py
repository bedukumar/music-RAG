"""Tool planning and execution for conversational requests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from ragpipe.application.services.collection_service import CollectionService
from ragpipe.application.services.media_query_service import MediaQueryService
from ragpipe.application.services.status_service import StatusService
from ragpipe.domain.models.conversation import ConversationMemory, ToolInvocation, ToolResult
from ragpipe.domain.models.modality import Modality
from ragpipe.infrastructure.langchain.retriever_provider import RetrievalContext, RetrieverProvider
from ragpipe.infrastructure.langchain.tools import (
    BaseConversationTool,
    CollectionStatsTool,
    ConversationHistoryTool,
    MediaDetailsTool,
    PipelineStatusTool,
    SearchByArtistTool,
    SearchByGenreTool,
    SearchByYearTool,
    SearchTool,
    SimilarSongsTool,
    ToolExecutionContext,
)


@dataclass(frozen=True)
class ToolExecutionSummary:
    """Structured tool execution output."""

    tool_invocations: list[ToolInvocation]
    tool_result_objects: list[ToolResult]
    tool_results: list[dict[str, Any]]
    retrieval_context: Optional[RetrievalContext]
    latency_ms: float


class ToolExecutor:
    """Plan and run conversational tools."""

    def __init__(
        self,
        retriever_provider: RetrieverProvider,
        media_query_service: MediaQueryService,
        collection_service: CollectionService,
        status_service: StatusService,
    ) -> None:
        self.retriever_provider = retriever_provider
        self.media_query_service = media_query_service
        self.collection_service = collection_service
        self.status_service = status_service
        self._history_loader: Callable[[str], Awaitable[dict[str, Any]]] = self._default_history_loader
        self._tools: dict[str, BaseConversationTool] = {
            "SearchTool": SearchTool(self.retriever_provider),
            "MediaDetailsTool": MediaDetailsTool(self.media_query_service),
            "SearchByArtistTool": SearchByArtistTool(self.media_query_service),
            "SearchByGenreTool": SearchByGenreTool(self.media_query_service),
            "SearchByYearTool": SearchByYearTool(self.media_query_service),
            "SimilarSongsTool": SimilarSongsTool(self.media_query_service, self.retriever_provider),
            "PipelineStatusTool": PipelineStatusTool(self.status_service),
            "CollectionStatsTool": CollectionStatsTool(self.collection_service),
            "ConversationHistoryTool": ConversationHistoryTool(self._history_loader),
        }

    def bind_history_loader(self, loader: Callable[[str], Awaitable[dict[str, Any]]]) -> None:
        """Attach a conversation history loader after the conversation service exists."""

        self._history_loader = loader
        self._tools["ConversationHistoryTool"] = ConversationHistoryTool(self._history_loader)

    def describe_tools(self) -> str:
        """Return a human-readable tool inventory."""

        lines = []
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def langchain_tools(self) -> list[Any]:  # pragma: no cover - optional bridge
        tools = []
        for tool in self._tools.values():
            langchain_tool = tool.to_langchain_tool()
            if langchain_tool:
                tools.append(langchain_tool)
        return tools

    async def execute(self, context: ToolExecutionContext) -> dict[str, Any]:
        """Select and execute the appropriate tools for a request."""

        start = time.perf_counter()
        tool_names = self._select_tools(context)
        invocations: list[ToolInvocation] = []
        results: list[ToolResult] = []
        structured_results: list[dict[str, Any]] = []
        retrieval_context: Optional[RetrievalContext] = None

        for name in tool_names:
            tool = self._tools.get(name)
            if tool is None:
                continue
            invocation = ToolInvocation(
                tool_name=name,
                arguments={
                    "conversation_id": context.conversation_id,
                    "user_message": context.user_message,
                    "filters": context.filters,
                    "top_k": context.top_k,
                    "score_threshold": context.score_threshold,
                    "modalities": [mod.value for mod in context.modalities],
                },
            )
            result = await tool.run(context)
            result = ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=result.tool_name,
                success=result.success,
                result=result.result,
                error=result.error,
                created_at=result.created_at,
                latency_ms=result.latency_ms,
            )
            invocation = ToolInvocation(
                tool_name=invocation.tool_name,
                arguments=invocation.arguments,
                invocation_id=invocation.invocation_id,
                created_at=invocation.created_at,
                latency_ms=result.latency_ms,
            )
            invocations.append(invocation)
            results.append(result)
            structured_results.append(
                {
                    "invocation_id": result.invocation_id,
                    "tool_name": result.tool_name,
                    "success": result.success,
                    "result": result.result,
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                }
            )

            if retrieval_context is None:
                retrieval_payload = result.result.get("citations") or result.result.get("results")
                if retrieval_payload:
                    normalized_documents: list[dict[str, Any]] = []
                    for item in retrieval_payload:
                        if isinstance(item, dict) and "metadata" in item:
                            normalized_documents.append(item)
                            continue
                        if isinstance(item, dict) and "media" in item:
                            media = item.get("media", {}) or {}
                            normalized_documents.append(
                                {
                                    "content": "",
                                    "metadata": {
                                        "media_id": media.get("media_id"),
                                        "title": media.get("title"),
                                        "media_type": media.get("media_type"),
                                        "chunk_id": None,
                                        "modality": None,
                                        "score": item.get("overall_score", 0.0),
                                        "overall_score": item.get("overall_score", 0.0),
                                        "timestamps": None,
                                    },
                                    "raw": item,
                                }
                            )
                            continue
                        normalized_documents.append(
                            {
                                "content": str(item),
                                "metadata": {
                                    "media_id": None,
                                    "title": None,
                                    "chunk_id": None,
                                    "modality": None,
                                    "score": 0.0,
                                },
                                "raw": item,
                            }
                        )
                    retrieval_context = RetrievalContext(
                        documents=normalized_documents,
                        media_ids=list(dict.fromkeys(result.result.get("retrieved_media_ids", []))),
                        latency_ms=float(result.result.get("latency_ms", 0.0) or 0.0),
                        raw_results=[],
                    )

        return {
            "tool_invocations": invocations,
            "tool_result_objects": results,
            "tool_results": structured_results,
            "retrieval_context": retrieval_context,
            "latency_ms": (time.perf_counter() - start) * 1000,
        }

    def _select_tools(self, context: ToolExecutionContext) -> list[str]:
        message = context.user_message.lower()
        selected: list[str] = []
        import re

        search_keywords = [
            "media", "song", "songs", "lyrics", "transcript", "audio", 
            "metadata", "similar", "music", "track", "tracks", "beat", 
            "sound", "tune", "anthem"
        ]
        if any(keyword in message for keyword in search_keywords):
            selected.append("SearchTool")

        if re.search(r'\b(artist|singer|band)\b', message) or re.search(r'\b(?:song|track|music|album)s? by\b', message):
            selected.append("SearchByArtistTool")

        if "genre" in message:
            selected.append("SearchByGenreTool")

        if "year" in message or "released" in message:
            selected.append("SearchByYearTool")

        if "similar" in message:
            selected.append("SimilarSongsTool")

        if any(keyword in message for keyword in ["pipeline", "status", "job"]):
            selected.append("PipelineStatusTool")

        if any(keyword in message for keyword in ["collection", "collections", "index", "indices"]):
            selected.append("CollectionStatsTool")

        if any(keyword in message for keyword in ["conversation history", "previous messages", "our chat", "earlier"]):
            selected.append("ConversationHistoryTool")

        if context.filters.get("media_id") and "MediaDetailsTool" not in selected:
            selected.append("MediaDetailsTool")

        if not selected:
            selected.append("SearchTool")

        # Deduplicate while preserving order.
        return list(dict.fromkeys(selected))

    async def _default_history_loader(self, conversation_id: str) -> dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "note": "Conversation history provider is not yet bound.",
        }
