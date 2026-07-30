"""LLM provider port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for chat-oriented LLM providers."""

    @abstractmethod
    async def acomplete(self, messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Generate a non-streaming completion."""

    @abstractmethod
    async def astream(
        self, messages: Sequence[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream completion deltas."""

    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name."""
