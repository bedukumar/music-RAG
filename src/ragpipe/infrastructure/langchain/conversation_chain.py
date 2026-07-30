"""Composable conversation chain built from the LangChain adapters."""

from __future__ import annotations

from typing import Any, Optional

from ragpipe.domain.models.conversation import Conversation, ConversationMemory
from ragpipe.infrastructure.langchain.memory_provider import MemoryProvider
from ragpipe.infrastructure.langchain.prompt_builder import PromptBuilder
from ragpipe.infrastructure.langchain.provider import GeminiChatProvider
from ragpipe.infrastructure.langchain.retriever_provider import RetrieverProvider, RetrievalContext
from ragpipe.infrastructure.langchain.tool_executor import ToolExecutionContext, ToolExecutor


class ConversationChain:
    """Build prompts, execute tools, retrieve context, and call the LLM."""

    def __init__(
        self,
        llm_provider: GeminiChatProvider,
        prompt_builder: PromptBuilder,
        memory_provider: MemoryProvider,
        retriever_provider: RetrieverProvider,
        tool_executor: ToolExecutor,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_builder = prompt_builder
        self.memory_provider = memory_provider
        self.retriever_provider = retriever_provider
        self.tool_executor = tool_executor

    async def build_memory(
        self,
        conversation_id: str,
        *,
        system_prompt_version: str = "v1",
        window_size: Optional[int] = None,
    ) -> ConversationMemory:
        """Load and compress conversation memory."""

        return await self.memory_provider.load_memory(
            conversation_id,
            system_prompt_version=system_prompt_version,
            window_size=window_size,
        )

    def build_prompt_messages(
        self,
        conversation: Conversation,
        memory: ConversationMemory,
        user_message: str,
        search_config: dict[str, Any],
        retrieved_context: RetrievalContext | None,
        tool_outputs: str,
    ) -> list[dict[str, str]]:
        """Assemble the prompt payload for Gemini."""

        retrieved_text = ""
        if retrieved_context and retrieved_context.documents:
            retrieved_text = "\n".join(
                f"- {doc['metadata'].get('title', 'Unknown')} ({doc['metadata'].get('media_id')})"
                for doc in retrieved_context.documents[:8]
            )

        return self.prompt_builder.build_messages(
            conversation=conversation,
            memory=memory,
            user_message=user_message,
            search_config=search_config,
            retrieved_context=retrieved_text,
            tool_descriptions=self.tool_executor.describe_tools(),
            tool_outputs=tool_outputs,
        )

    async def complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Invoke the configured LLM provider."""

        return await self.llm_provider.acomplete(messages)

    async def stream(self, messages: list[dict[str, str]]):
        """Stream completion deltas."""

        async for delta in self.llm_provider.astream(messages):
            yield delta
