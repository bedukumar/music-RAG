"""Conversation memory loading and compression helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from ragpipe.domain.models.conversation import ConversationMemory
from ragpipe.domain.ports.conversation_repository import ConversationRepository


class MemoryProvider:
    """Loads windowed memory from the conversation repository."""

    def __init__(self, repository: ConversationRepository, default_window: int = 12) -> None:
        self.repository = repository
        self.default_window = default_window

    async def load_memory(
        self,
        conversation_id: str,
        *,
        window_size: Optional[int] = None,
        system_prompt_version: str = "v1",
    ) -> ConversationMemory:
        """Load recent messages and aggregate retrieval context."""

        window = window_size or self.default_window
        messages = await self.repository.list_messages(conversation_id, limit=window)
        retrieval_context: list[dict[str, object]] = []
        for message in messages:
            retrieval_context.extend(message.retrieval_context)

        memory = ConversationMemory(
            conversation_id=conversation_id,
            messages=messages,
            retrieval_context=retrieval_context,
            system_prompt_version=system_prompt_version,
            window_size=window,
        )
        return self.compress(memory)

    def compress(self, memory: ConversationMemory, max_tokens: int = 6000) -> ConversationMemory:
        """Trim history until it roughly fits within the requested token budget."""

        if not memory.messages:
            return memory

        total_tokens = 0
        kept: list = []
        for message in reversed(memory.messages):
            total_tokens += self._estimate_tokens(message.content)
            if total_tokens > max_tokens:
                break
            kept.append(message)

        kept.reverse()
        if len(kept) == len(memory.messages):
            return memory
        return replace(memory, messages=kept, compressed=True)

    def _estimate_tokens(self, text: str) -> int:
        """Very rough token estimate used for safety trimming."""

        words = max(len(text.split()), 1)
        return int(words * 1.3)
