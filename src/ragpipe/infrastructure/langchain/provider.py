"""Gemini chat provider abstraction built on top of LangChain."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from typing import Any, Optional

from ragpipe.domain.ports.llm_provider import LLMProvider


class GeminiChatProvider(LLMProvider):
    """Reusable Gemini chat provider with lazy LangChain imports."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise RuntimeError(
                "GeminiChatProvider requires GOOGLE_API_KEY or GEMINI_API_KEY"
            )

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "langchain-google-genai is required for GeminiChatProvider"
            ) from exc

        self._client = ChatGoogleGenerativeAI(
            model=self._model,
            google_api_key=self._api_key,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
        )
        return self._client

    def model_name(self) -> str:
        return self._model

    async def acomplete(self, messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
        client = self._get_client()
        response = await client.ainvoke(messages)
        content = getattr(response, "content", "")
        metadata = getattr(response, "response_metadata", {}) or {}
        usage = getattr(response, "usage_metadata", {}) or {}
        return {
            "content": content,
            "raw": response,
            "model": self._model,
            "usage": usage,
            "metadata": metadata,
        }

    async def astream(
        self, messages: Sequence[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._get_client()
        async for chunk in client.astream(messages):
            yield {
                "delta": getattr(chunk, "content", ""),
                "raw": chunk,
                "model": self._model,
            }
