"""Conversation orchestration service for the CUI backend."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import replace
from typing import Any, AsyncIterator, Optional

from ragpipe.application.services.collection_service import CollectionService
from ragpipe.application.services.media_query_service import MediaQueryService
from ragpipe.application.services.status_service import StatusService
from ragpipe.domain.models.conversation import (
    ChatRole,
    Conversation,
    ConversationMemory,
    ConversationMessage,
    ToolInvocation,
    ToolResult,
)
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.conversation_repository import ConversationRepository
from ragpipe.domain.ports.llm_provider import LLMProvider
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.infrastructure.langchain.memory_provider import MemoryProvider
from ragpipe.infrastructure.langchain.prompt_builder import PromptBuilder
from ragpipe.infrastructure.langchain.retriever_provider import RetrievalContext, RetrieverProvider
from ragpipe.infrastructure.langchain.tool_executor import ToolExecutionContext, ToolExecutor


class ConversationService:
    """Top-level orchestration for conversational requests."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        llm_provider: LLMProvider,
        prompt_builder: PromptBuilder,
        memory_provider: MemoryProvider,
        retriever_provider: RetrieverProvider,
        tool_executor: ToolExecutor,
        media_query_service: MediaQueryService,
        collection_service: CollectionService,
        status_service: StatusService,
        metrics: MetricsCollector,
        *,
        default_memory_window: int = 12,
        default_system_prompt_version: str = "v1",
    ) -> None:
        self.conversation_repo = conversation_repo
        self.llm_provider = llm_provider
        self.prompt_builder = prompt_builder
        self.memory_provider = memory_provider
        self.retriever_provider = retriever_provider
        self.tool_executor = tool_executor
        self.media_query_service = media_query_service
        self.collection_service = collection_service
        self.status_service = status_service
        self.metrics = metrics
        self.default_memory_window = default_memory_window
        self.default_system_prompt_version = default_system_prompt_version

    async def create_conversation(
        self,
        title: str,
        *,
        system_prompt_version: Optional[str] = None,
        memory_window: Optional[int] = None,
    ) -> Conversation:
        """Create a new conversation."""

        conversation = Conversation.create(
            title=title,
            system_prompt_version=system_prompt_version or self.default_system_prompt_version,
            memory_window=memory_window or self.default_memory_window,
        )
        return await self.conversation_repo.create_conversation(conversation)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return await self.conversation_repo.get_conversation(conversation_id)

    async def list_messages(
        self,
        conversation_id: str,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ConversationMessage]:
        return await self.conversation_repo.list_messages(conversation_id, limit=limit, offset=offset)

    async def delete_conversation(self, conversation_id: str) -> None:
        await self.conversation_repo.delete_conversation(conversation_id)

    async def chat(
        self,
        *,
        message: str,
        conversation_id: Optional[str] = None,
        title: Optional[str] = None,
        modalities: Optional[list[Modality]] = None,
        filters: Optional[dict[str, Any]] = None,
        tag_matches: Optional[list[str]] = None,
        top_k: int = 8,
        score_threshold: float = 0.0,
        include_similarity_score: bool = True,
        rerank: bool = True,
        fusion_strategy: str = "rrf",
        search_mode: str = "hybrid",
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Execute a complete conversational turn."""

        start_time = time.perf_counter()
        conversation = await self._get_or_create_conversation(
            conversation_id=conversation_id,
            title=title or self._derive_title(message),
        )
        user_message = ConversationMessage.create(
            conversation_id=conversation.id,
            role=ChatRole.USER,
            content=message,
            system_prompt_version=conversation.system_prompt_version,
        )
        await self.conversation_repo.add_message(user_message)

        memory = await self.memory_provider.load_memory(
            conversation.id,
            window_size=conversation.memory_window,
            system_prompt_version=conversation.system_prompt_version,
        )

        tool_context = ToolExecutionContext(
            conversation_id=conversation.id,
            user_message=message,
            memory=memory,
            modalities=modalities or [Modality.AUDIO, Modality.TRANSCRIPT, Modality.METADATA],
            filters=filters or {},
            tag_matches=tag_matches or [],
            top_k=top_k,
            score_threshold=score_threshold,
            include_similarity_score=include_similarity_score,
            rerank=rerank,
            fusion_strategy=fusion_strategy,
            search_mode=search_mode,
            page=page,
            page_size=page_size,
        )
        tool_summary = await self.tool_executor.execute(tool_context)

        retrieval_context = tool_summary.get("retrieval_context")
        if retrieval_context is None and self._should_use_retrieval(message):
            retrieval_context = await self._run_retrieval(
                message=message,
                modalities=modalities,
                filters=filters,
                tag_matches=tag_matches,
                top_k=top_k,
                score_threshold=score_threshold,
                include_similarity_score=include_similarity_score,
                rerank=rerank,
                fusion_strategy=fusion_strategy,
            )

        retrieved_context_text = self._render_retrieval_context(retrieval_context)
        tool_outputs_text = self._render_tool_outputs(tool_summary.get("tool_result_objects", []))

        search_config = {
            "modalities": [mod.value for mod in (modalities or [Modality.AUDIO, Modality.TRANSCRIPT, Modality.METADATA])],
            "filters": filters or {},
            "tag_matches": tag_matches or [],
            "top_k": top_k,
            "score_threshold": score_threshold,
            "include_similarity_score": include_similarity_score,
            "rerank": rerank,
            "fusion_strategy": fusion_strategy,
            "search_mode": search_mode,
            "page": page,
            "page_size": page_size,
        }
        prompt_messages = self.prompt_builder.build_messages(
            conversation=conversation,
            memory=memory,
            user_message=message,
            search_config=search_config,
            retrieved_context=retrieved_context_text,
            tool_descriptions=self.tool_executor.describe_tools(),
            tool_outputs=tool_outputs_text,
        )

        llm_start = time.perf_counter()
        llm_response = await self.llm_provider.acomplete(prompt_messages)
        llm_latency_ms = (time.perf_counter() - llm_start) * 1000
        answer_text = str(llm_response.get("content", "")).strip()
        usage = llm_response.get("usage", {}) or {}
        metadata = llm_response.get("metadata", {}) or {}

        citations = self._build_citations(retrieval_context)
        tool_calls = tool_summary.get("tool_invocations", [])
        retrieved_media_ids = self._collect_media_ids(retrieval_context)

        retrieval_documents = retrieval_context.documents if retrieval_context else []

        assistant_message = ConversationMessage.create(
            conversation_id=conversation.id,
            role=ChatRole.ASSISTANT,
            content=answer_text,
            tool_calls=tool_calls,
            tool_results=tool_summary.get("tool_result_objects", []),
            retrieval_context=retrieval_documents,
            citations=citations,
            system_prompt_version=conversation.system_prompt_version,
            metadata={
                "llm_model": self.llm_provider.model_name(),
                "llm_metadata": metadata,
                "search_mode": search_mode,
            },
        )
        await self.conversation_repo.add_message(assistant_message)
        await self.conversation_repo.update_conversation(
            replace(
                conversation,
                updated_at=assistant_message.created_at,
                last_message_at=assistant_message.created_at,
            )
        )

        total_latency_ms = (time.perf_counter() - start_time) * 1000
        self._record_metrics(
            total_latency_ms=total_latency_ms,
            llm_latency_ms=llm_latency_ms,
            retrieval_latency_ms=float(retrieval_context.latency_ms) if retrieval_context else 0.0,
            tool_latency_ms=tool_summary.get("latency_ms", 0.0),
            token_usage=usage,
            conversation_id=conversation.id,
        )
        return {
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "assistant_message": answer_text,
            "citations": citations,
            "retrieved_media_ids": retrieved_media_ids,
            "tool_calls": [self._tool_call_to_dict(tool) for tool in tool_calls],
            "latency_ms": {
                "total": total_latency_ms,
                "llm": llm_latency_ms,
                "retrieval": float(retrieval_context.latency_ms) if retrieval_context else 0.0,
                "tools": tool_summary.get("latency_ms", 0.0),
            },
            "token_usage": self._normalize_usage(usage),
            "conversation_title": conversation.title,
        }

    async def stream_chat(
        self,
        *,
        message: str,
        conversation_id: Optional[str] = None,
        title: Optional[str] = None,
        modalities: Optional[list[Modality]] = None,
        filters: Optional[dict[str, Any]] = None,
        tag_matches: Optional[list[str]] = None,
        top_k: int = 8,
        score_threshold: float = 0.0,
        include_similarity_score: bool = True,
        rerank: bool = True,
        fusion_strategy: str = "rrf",
        search_mode: str = "hybrid",
        page: int = 1,
        page_size: int = 10,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat turn as SSE-friendly event payloads."""
        start_time = time.perf_counter()
        conversation = await self._get_or_create_conversation(
            conversation_id=conversation_id,
            title=title or self._derive_title(message),
        )
        user_message = ConversationMessage.create(
            conversation_id=conversation.id,
            role=ChatRole.USER,
            content=message,
            system_prompt_version=conversation.system_prompt_version,
        )
        await self.conversation_repo.add_message(user_message)

        memory = await self.memory_provider.load_memory(
            conversation.id,
            window_size=conversation.memory_window,
            system_prompt_version=conversation.system_prompt_version,
        )

        tool_context = ToolExecutionContext(
            conversation_id=conversation.id,
            user_message=message,
            memory=memory,
            modalities=modalities or [Modality.AUDIO, Modality.TRANSCRIPT, Modality.METADATA],
            filters=filters or {},
            tag_matches=tag_matches or [],
            top_k=top_k,
            score_threshold=score_threshold,
            include_similarity_score=include_similarity_score,
            rerank=rerank,
            fusion_strategy=fusion_strategy,
            search_mode=search_mode,
            page=page,
            page_size=page_size,
        )
        tool_summary = await self.tool_executor.execute(tool_context)
        retrieval_context = tool_summary.get("retrieval_context")
        if retrieval_context is None and self._should_use_retrieval(message):
            retrieval_context = await self._run_retrieval(
                message=message,
                modalities=modalities,
                filters=filters,
                tag_matches=tag_matches,
                top_k=top_k,
                score_threshold=score_threshold,
                include_similarity_score=include_similarity_score,
                rerank=rerank,
                fusion_strategy=fusion_strategy,
            )

        retrieved_context_text = self._render_retrieval_context(retrieval_context)
        tool_outputs_text = self._render_tool_outputs(tool_summary.get("tool_result_objects", []))
        search_config = {
            "modalities": [mod.value for mod in (modalities or [Modality.AUDIO, Modality.TRANSCRIPT, Modality.METADATA])],
            "filters": filters or {},
            "tag_matches": tag_matches or [],
            "top_k": top_k,
            "score_threshold": score_threshold,
            "include_similarity_score": include_similarity_score,
            "rerank": rerank,
            "fusion_strategy": fusion_strategy,
            "search_mode": search_mode,
            "page": page,
            "page_size": page_size,
        }
        prompt_messages = self.prompt_builder.build_messages(
            conversation=conversation,
            memory=memory,
            user_message=message,
            search_config=search_config,
            retrieved_context=retrieved_context_text,
            tool_descriptions=self.tool_executor.describe_tools(),
            tool_outputs=tool_outputs_text,
        )

        tool_calls = tool_summary.get("tool_invocations", [])
        for tool_call in tool_calls:
            yield {
                "event": "tool",
                "conversation_id": conversation.id,
                "message_id": user_message.id,
                "data": self._tool_call_to_dict(tool_call),
            }

        citations = self._build_citations(retrieval_context)
        for citation in citations:
            yield {
                "event": "retrieval",
                "conversation_id": conversation.id,
                "message_id": user_message.id,
                "data": citation,
            }

        llm_start = time.perf_counter()
        answer_parts: list[str] = []
        try:
            async for chunk in self.llm_provider.astream(prompt_messages):
                delta = str(chunk.get("delta", ""))
                if not delta:
                    continue
                answer_parts.append(delta)
                yield {
                    "event": "delta",
                    "conversation_id": conversation.id,
                    "message_id": user_message.id,
                    "data": {"delta": delta},
                }
        except Exception as exc:
            yield {
                "event": "error",
                "conversation_id": conversation.id,
                "message_id": user_message.id,
                "error": str(exc),
            }
            return

        answer_text = "".join(answer_parts).strip()
        llm_latency_ms = (time.perf_counter() - llm_start) * 1000
        retrieval_documents = retrieval_context.documents if retrieval_context else []
        assistant_message = ConversationMessage.create(
            conversation_id=conversation.id,
            role=ChatRole.ASSISTANT,
            content=answer_text,
            tool_calls=tool_calls,
            tool_results=tool_summary.get("tool_result_objects", []),
            retrieval_context=retrieval_documents,
            citations=citations,
            system_prompt_version=conversation.system_prompt_version,
            metadata={
                "llm_model": self.llm_provider.model_name(),
                "search_mode": search_mode,
            },
        )
        await self.conversation_repo.add_message(assistant_message)
        await self.conversation_repo.update_conversation(
            replace(
                conversation,
                updated_at=assistant_message.created_at,
                last_message_at=assistant_message.created_at,
            )
        )
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        self._record_metrics(
            total_latency_ms=total_latency_ms,
            llm_latency_ms=llm_latency_ms,
            retrieval_latency_ms=float(retrieval_context.latency_ms) if retrieval_context else 0.0,
            tool_latency_ms=tool_summary.get("latency_ms", 0.0),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            conversation_id=conversation.id,
        )
        yield {
            "event": "completion",
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "data": {
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
                "assistant_message": answer_text,
                "citations": citations,
                "retrieved_media_ids": self._collect_media_ids(retrieval_context),
                "tool_calls": [self._tool_call_to_dict(tool) for tool in tool_calls],
                "latency_ms": {
                    "total": total_latency_ms,
                    "llm": llm_latency_ms,
                    "retrieval": float(retrieval_context.latency_ms) if retrieval_context else 0.0,
                    "tools": tool_summary.get("latency_ms", 0.0),
                },
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "conversation_title": conversation.title,
            },
        }

    async def get_history_payload(self, conversation_id: str) -> dict[str, Any]:
        conversation = await self.conversation_repo.get_conversation(conversation_id)
        if not conversation:
            return {}
        messages = await self.conversation_repo.list_messages(conversation_id)
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "system_prompt_version": conversation.system_prompt_version,
                "memory_window": conversation.memory_window,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
            },
            "messages": [
                {
                    "id": message.id,
                    "conversation_id": message.conversation_id,
                    "role": message.role.value,
                    "content": message.content,
                    "tool_calls": [self._tool_call_to_dict(tool) for tool in message.tool_calls],
                    "tool_results": [
                        {
                            "invocation_id": result.invocation_id,
                            "tool_name": result.tool_name,
                            "success": result.success,
                            "result": result.result,
                            "error": result.error,
                            "created_at": result.created_at.isoformat(),
                            "latency_ms": result.latency_ms,
                        }
                        for result in message.tool_results
                    ],
                    "retrieval_context": message.retrieval_context,
                    "citations": message.citations,
                    "system_prompt_version": message.system_prompt_version,
                    "metadata": message.metadata,
                    "created_at": message.created_at.isoformat(),
                }
                for message in messages
            ],
        }

    async def _get_or_create_conversation(self, conversation_id: Optional[str], title: str) -> Conversation:
        if conversation_id:
            conversation = await self.conversation_repo.get_conversation(conversation_id)
            if conversation:
                return conversation
            raise ValueError(f"Conversation not found: {conversation_id}")
        return await self.create_conversation(title)

    async def _run_retrieval(
        self,
        *,
        message: str,
        modalities: Optional[list[Modality]],
        filters: Optional[dict[str, Any]],
        tag_matches: Optional[list[str]],
        top_k: int,
        score_threshold: float,
        include_similarity_score: bool,
        rerank: bool,
        fusion_strategy: str,
    ) -> RetrievalContext:
        return await self.retriever_provider.retrieve(
            message,
            top_k=top_k,
            score_threshold=score_threshold,
            modalities=modalities,
            filters=filters,
            tag_matches=tag_matches,
            rerank=rerank,
            fusion_strategy=fusion_strategy,
            include_similarity_score=include_similarity_score,
        )

    def _should_use_retrieval(self, message: str) -> bool:
        lowered = message.lower()
        keywords = [
            "song",
            "songs",
            "media",
            "lyrics",
            "lyric",
            "transcript",
            "metadata",
            "audio",
            "artist",
            "album",
            "genre",
            "year",
            "similar",
            "collection",
            "pipeline",
        ]
        return any(keyword in lowered for keyword in keywords)

    def _derive_title(self, message: str) -> str:
        return message.strip()[:64] or "New conversation"

    def _render_retrieval_context(self, retrieval_context: Optional[RetrievalContext]) -> str:
        if not retrieval_context or not retrieval_context.documents:
            return "No retrieval context."
        lines = []
        for item in retrieval_context.documents[:8]:
            meta = item["metadata"]
            lines.append(
                f"- {meta.get('title', 'Unknown')} [{meta.get('media_id')}] "
                f"chunk={meta.get('chunk_id')} modality={meta.get('modality')} score={meta.get('score')}"
            )
        return "\n".join(lines)

    def _render_tool_outputs(self, tool_results: list[ToolResult]) -> str:
        if not tool_results:
            return "No tool outputs."
        return "\n".join(
            f"- {result.tool_name}: {'ok' if result.success else 'error'} {result.result or result.error or ''}"
            for result in tool_results
        )

    def _build_citations(self, retrieval_context: Optional[RetrievalContext]) -> list[dict[str, Any]]:
        if not retrieval_context:
            return []
        citations: list[dict[str, Any]] = []
        for item in retrieval_context.documents:
            meta = item["metadata"]
            citations.append(
                {
                    "media_id": meta.get("media_id"),
                    "title": meta.get("title"),
                    "chunk_id": meta.get("chunk_id"),
                    "modality": meta.get("modality"),
                    "score": meta.get("score"),
                }
            )
        return citations

    def _collect_media_ids(self, retrieval_context: Optional[RetrievalContext]) -> list[str]:
        if not retrieval_context:
            return []
        return list(dict.fromkeys(retrieval_context.media_ids))

    def _tool_call_to_dict(self, tool_call: Any) -> dict[str, Any]:
        if isinstance(tool_call, dict):
            return {
                "invocation_id": tool_call.get("invocation_id", ""),
                "tool_name": tool_call.get("tool_name", ""),
                "arguments": tool_call.get("arguments", {}),
                "created_at": tool_call.get("created_at", ""),
                "latency_ms": tool_call.get("latency_ms", None),
            }
        
        created_at_val = getattr(tool_call, "created_at", None)
        created_at_str = created_at_val.isoformat() if hasattr(created_at_val, "isoformat") else str(created_at_val or "")
        
        return {
            "invocation_id": getattr(tool_call, "invocation_id", ""),
            "tool_name": getattr(tool_call, "tool_name", ""),
            "arguments": getattr(tool_call, "arguments", {}),
            "created_at": created_at_str,
            "latency_ms": getattr(tool_call, "latency_ms", None),
        }

    def _normalize_usage(self, usage: dict[str, Any]) -> dict[str, int]:
        normalized = {
            "prompt_tokens": int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0),
            "completion_tokens": int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
        if normalized["total_tokens"] == 0:
            normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]
        return normalized

    def _record_metrics(
        self,
        *,
        total_latency_ms: float,
        llm_latency_ms: float,
        retrieval_latency_ms: float,
        tool_latency_ms: float,
        token_usage: dict[str, Any],
        conversation_id: str,
    ) -> None:
        self.metrics.increment("conversation_turns_total", tags={"conversation_id": conversation_id})
        self.metrics.histogram("conversation_total_latency_ms", total_latency_ms, tags={"conversation_id": conversation_id})
        self.metrics.histogram("conversation_llm_latency_ms", llm_latency_ms, tags={"conversation_id": conversation_id})
        self.metrics.histogram("conversation_retrieval_latency_ms", retrieval_latency_ms, tags={"conversation_id": conversation_id})
        self.metrics.histogram("conversation_tool_latency_ms", tool_latency_ms, tags={"conversation_id": conversation_id})
        self.metrics.gauge("conversation_prompt_tokens", float(token_usage.get("prompt_tokens", 0)), tags={"conversation_id": conversation_id})
        self.metrics.gauge("conversation_completion_tokens", float(token_usage.get("completion_tokens", 0)), tags={"conversation_id": conversation_id})
        self.metrics.gauge("conversation_total_tokens", float(token_usage.get("total_tokens", 0)), tags={"conversation_id": conversation_id})

    def _chunk_text(self, text: str, size: int = 24) -> list[str]:
        tokens = text.split()
        if not tokens:
            return []
        return [" ".join(tokens[i:i + size]) for i in range(0, len(tokens), size)]
