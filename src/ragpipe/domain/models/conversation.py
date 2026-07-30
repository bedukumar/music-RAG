"""Conversation domain models for the CUI backend."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ChatRole(Enum):
    """Chat roles supported by the conversation subsystem."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolInvocation:
    """Represents a tool call requested by the assistant."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    invocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: Optional[float] = None


@dataclass(frozen=True)
class ToolResult:
    """Represents the outcome of a tool invocation."""

    invocation_id: str
    tool_name: str
    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: Optional[float] = None


@dataclass(frozen=True)
class ConversationMessage:
    """Persisted message in a conversation thread."""

    id: str
    conversation_id: str
    role: ChatRole
    content: str
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    retrieval_context: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    system_prompt_version: str = "v1"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        conversation_id: str,
        role: ChatRole,
        content: str,
        *,
        tool_calls: Optional[list[ToolInvocation]] = None,
        tool_results: Optional[list[ToolResult]] = None,
        retrieval_context: Optional[list[dict[str, Any]]] = None,
        citations: Optional[list[dict[str, Any]]] = None,
        system_prompt_version: str = "v1",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Create a new conversation message with a generated UUID."""

        return cls(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
            retrieval_context=retrieval_context or [],
            citations=citations or [],
            system_prompt_version=system_prompt_version,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class ConversationMemory:
    """Windowed memory used to build prompts for the LLM."""

    conversation_id: str
    messages: list[ConversationMessage] = field(default_factory=list)
    retrieval_context: list[dict[str, Any]] = field(default_factory=list)
    system_prompt_version: str = "v1"
    window_size: int = 12
    compressed: bool = False

    def trim(self, max_messages: int) -> ConversationMemory:
        """Return a copy trimmed to the requested message count."""

        if max_messages <= 0:
            return replace(self, messages=[], compressed=True)
        if len(self.messages) <= max_messages:
            return self
        return replace(
            self,
            messages=self.messages[-max_messages:],
            compressed=True,
        )


@dataclass(frozen=True)
class Conversation:
    """Conversation aggregate."""

    id: str
    title: str
    system_prompt_version: str = "v1"
    memory_window: int = 12
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        title: str,
        *,
        system_prompt_version: str = "v1",
        memory_window: int = 12,
    ) -> Conversation:
        """Create a new conversation aggregate."""

        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            system_prompt_version=system_prompt_version,
            memory_window=memory_window,
            created_at=now,
            updated_at=now,
        )
