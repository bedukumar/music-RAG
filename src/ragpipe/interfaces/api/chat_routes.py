"""Conversational user interface routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse as SSEStreamingResponse

from ragpipe.domain.models.modality import Modality
from ragpipe.interfaces.schemas.chat_schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationMessageResponse,
    ConversationResponse,
    StreamingResponse,
    ToolCallResponse,
    ToolResultResponse,
    CitationResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_conversation_service(request: Request):
    return request.app.state.container.conversation_service


def _modality_list(raw_modalities: list[str]) -> list[Modality]:
    modalities: list[Modality] = []
    for modality in raw_modalities:
        modalities.append(Modality(modality))
    return modalities


def _serialize_conversation(conversation, message_count: int | None = None) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        system_prompt_version=conversation.system_prompt_version,
        memory_window=conversation.memory_window,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        message_count=message_count,
    )


def _serialize_message(message) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role.value,
        content=message.content,
        tool_calls=[
            ToolCallResponse(
                invocation_id=tool.get("invocation_id", "") if isinstance(tool, dict) else getattr(tool, "invocation_id", ""),
                tool_name=tool.get("tool_name", "") if isinstance(tool, dict) else getattr(tool, "tool_name", ""),
                arguments=tool.get("arguments", {}) if isinstance(tool, dict) else getattr(tool, "arguments", {}),
                latency_ms=tool.get("latency_ms") if isinstance(tool, dict) else getattr(tool, "latency_ms", None),
            )
            for tool in message.tool_calls
        ],
        tool_results=[
            ToolResultResponse(
                invocation_id=result.get("invocation_id", "") if isinstance(result, dict) else getattr(result, "invocation_id", ""),
                tool_name=result.get("tool_name", "") if isinstance(result, dict) else getattr(result, "tool_name", ""),
                success=result.get("success", False) if isinstance(result, dict) else getattr(result, "success", False),
                result=result.get("result", {}) if isinstance(result, dict) else getattr(result, "result", {}),
                error=result.get("error") if isinstance(result, dict) else getattr(result, "error", None),
                latency_ms=result.get("latency_ms") if isinstance(result, dict) else getattr(result, "latency_ms", None),
            )
            for result in message.tool_results
        ],
        retrieval_context=message.retrieval_context,
        citations=[
            CitationResponse(**citation) for citation in message.citations
        ],
        system_prompt_version=message.system_prompt_version,
        metadata=message.metadata,
        created_at=message.created_at,
    )


@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    conversation_service=Depends(get_conversation_service),
):
    conversation = await conversation_service.create_conversation(
        request.title,
        system_prompt_version=request.system_prompt_version,
        memory_window=request.memory_window,
    )
    return _serialize_conversation(conversation)


@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    conversation_service=Depends(get_conversation_service),
):
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await conversation_service.list_messages(conversation_id)
    return _serialize_conversation(conversation, len(messages))


@router.get("/conversation/{conversation_id}/messages", response_model=list[ConversationMessageResponse])
async def get_messages(
    conversation_id: str,
    conversation_service=Depends(get_conversation_service),
):
    messages = await conversation_service.list_messages(conversation_id)
    return [_serialize_message(message) for message in messages]


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    conversation_service=Depends(get_conversation_service),
):
    await conversation_service.delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}


@router.delete("/conversation/{conversation_id}/truncate/{message_id}")
async def truncate_conversation(
    conversation_id: str,
    message_id: str,
    conversation_service=Depends(get_conversation_service),
):
    await conversation_service.truncate_conversation(conversation_id, message_id)
    return {"status": "truncated", "conversation_id": conversation_id, "message_id": message_id}


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    conversation_service=Depends(get_conversation_service),
    x_debug_response: str | None = Header(default=None),
):
    debug = request.debug or (x_debug_response is not None and x_debug_response.lower() in ("true", "1", "yes"))
    try:
        response = await conversation_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            title=request.title,
            modalities=_modality_list(request.modalities),
            filters=request.filters,
            tag_matches=request.tag_matches,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            include_similarity_score=request.include_similarity_score,
            rerank=request.rerank,
            fusion_strategy=request.fusion_strategy,
            search_mode=request.search_mode,
            page=request.page,
            page_size=request.page_size,
            debug=debug,
        )
        citations = [CitationResponse(**c) for c in response.get("citations", [])] if response.get("citations") else []
        tool_calls = [ToolCallResponse(**t) for t in response.get("tool_calls", [])] if response.get("tool_calls") else []
        return ChatResponse(
            conversation_id=response["conversation_id"],
            message_id=response["message_id"],
            assistant_message=response["assistant_message"],
            citations=citations,
            retrieved_media_ids=response.get("retrieved_media_ids", []),
            tool_calls=tool_calls,
            latency_ms=response.get("latency_ms", {}),
            token_usage=response.get("token_usage", {}),
            conversation_title=response.get("conversation_title"),
        )
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    conversation_service=Depends(get_conversation_service),
    x_debug_response: str | None = Header(default=None),
):
    debug = request.debug or (x_debug_response is not None and x_debug_response.lower() in ("true", "1", "yes"))

    async def event_stream():
        try:
            async for event in conversation_service.stream_chat(
                message=request.message,
                conversation_id=request.conversation_id,
                title=request.title,
                modalities=_modality_list(request.modalities),
                filters=request.filters,
                tag_matches=request.tag_matches,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
                include_similarity_score=request.include_similarity_score,
                rerank=request.rerank,
                fusion_strategy=request.fusion_strategy,
                search_mode=request.search_mode,
                page=request.page,
                page_size=request.page_size,
                debug=debug,
            ):
                payload = StreamingResponse(
                    event=event["event"],
                    conversation_id=event["conversation_id"],
                    message_id=event.get("message_id"),
                    delta=event.get("data", {}).get("delta"),
                    data=event.get("data") if isinstance(event.get("data"), dict) else None,
                    error=event.get("error"),
                    done=event["event"] == "completion",
                )
                yield f"event: {payload.event}\ndata: {payload.model_dump_json()}\n\n"
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("SSE router error: %s", str(exc), exc_info=True)
            payload = StreamingResponse(
                event="error",
                conversation_id=request.conversation_id or "",
                error=str(exc),
                done=True,
            )
            yield f"event: error\ndata: {payload.model_dump_json()}\n\n"

    return SSEStreamingResponse(event_stream(), media_type="text/event-stream")
