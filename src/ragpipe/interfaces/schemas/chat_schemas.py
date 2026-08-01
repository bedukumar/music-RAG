"""Schemas for the conversational user interface backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolCallResponse(BaseModel):
    """Serialized tool call information."""

    invocation_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ToolResultResponse(BaseModel):
    """Serialized tool result information."""

    invocation_id: str
    tool_name: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CitationResponse(BaseModel):
    """Citation attached to an assistant answer."""

    media_id: Optional[str] = None
    title: Optional[str] = None
    chunk_id: Optional[str] = None
    modality: Optional[str] = None
    score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationMessageResponse(BaseModel):
    """Persisted conversation message."""

    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)
    tool_results: list[ToolResultResponse] = Field(default_factory=list)
    retrieval_context: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[CitationResponse] = Field(default_factory=list)
    system_prompt_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Conversation summary response."""

    id: str
    title: str
    system_prompt_version: str
    memory_window: int
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    message_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationCreateRequest(BaseModel):
    """Create a new conversation thread."""

    title: str = Field(default="New conversation", min_length=1, max_length=255)
    system_prompt_version: Optional[str] = None
    memory_window: Optional[int] = Field(default=None, ge=1, le=100)


class ChatRequest(BaseModel):
    """Incoming chat request."""

    conversation_id: Optional[str] = None
    title: Optional[str] = None
    message: str
    modalities: list[str] = Field(default_factory=lambda: ["audio", "transcript", "metadata"])
    filters: dict[str, Any] = Field(default_factory=dict)
    tag_matches: list[str] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=1, le=100)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    include_similarity_score: bool = True
    rerank: bool = True
    fusion_strategy: str = "rrf"
    search_mode: str = "hybrid"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    stream: bool = False
    debug: bool = False


class ChatResponse(BaseModel):
    """Structured response from the assistant."""

    conversation_id: str
    message_id: str
    assistant_message: str
    citations: list[CitationResponse] = Field(default_factory=list)
    retrieved_media_ids: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallResponse] = Field(default_factory=list)
    latency_ms: dict[str, float] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    conversation_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StreamingResponse(BaseModel):
    """SSE event envelope for the streaming endpoint."""

    event: str
    conversation_id: str
    message_id: Optional[str] = None
    delta: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    done: bool = False

    model_config = ConfigDict(from_attributes=True)
