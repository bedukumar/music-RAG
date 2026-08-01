"""Prompt construction helpers for the conversation chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ragpipe.domain.models.conversation import Conversation, ConversationMemory


class PromptBuilder:
    """Loads prompt templates and assembles final prompt text."""

    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir or Path(__file__).resolve().parent / "prompts"

    def _load(self, name: str) -> str:
        return (self.prompt_dir / f"{name}.txt").read_text(encoding="utf-8")

    def build_system_prompt(self, conversation: Conversation) -> str:
        system_template = self._load("system_prompt")
        formatting_template = self._load("response_formatting_prompt")
        return (
            system_template.format(system_prompt_version=conversation.system_prompt_version)
            + "\n"
            + formatting_template
        )

    def build_conversation_prompt(
        self,
        memory: ConversationMemory,
        user_message: str,
    ) -> str:
        template = self._load("conversation_prompt")
        history = self._format_history(memory)
        return template.format(conversation_history=history, user_message=user_message)

    def build_search_prompt(self, search_config: dict[str, Any], retrieved_context: str) -> str:
        template = self._load("search_prompt")
        return template.format(
            search_config=self._stringify(search_config),
            retrieved_context=retrieved_context or "No retrieval context available.",
        )

    def build_tool_prompt(self, tool_descriptions: str, tool_outputs: str) -> str:
        template = self._load("tool_prompt")
        return template.format(
            tool_descriptions=tool_descriptions or "No tools executed.",
            tool_outputs=tool_outputs or "No tool outputs available.",
        )

    def build_messages(
        self,
        conversation: Conversation,
        memory: ConversationMemory,
        user_message: str,
        search_config: dict[str, Any],
        retrieved_context: str,
        tool_descriptions: str,
        tool_outputs: str,
    ) -> list[dict[str, str]]:
        system_prompt = self.build_system_prompt(conversation)
        conversation_prompt = self.build_conversation_prompt(memory, user_message)
        search_prompt = self.build_search_prompt(search_config, retrieved_context)
        tool_prompt = self.build_tool_prompt(tool_descriptions, tool_outputs)
        return [
            {
                "role": "system",
                "content": "\n\n".join(
                    [system_prompt, search_prompt, tool_prompt]
                ),
            },
            {
                "role": "user",
                "content": conversation_prompt,
            },
        ]

    def _format_history(self, memory: ConversationMemory) -> str:
        lines: list[str] = []
        for message in memory.messages:
            lines.append(f"{message.role.value}: {message.content}")
            if message.tool_calls:
                lines.append(
                    f"tool_calls: {self._stringify([tool.get('tool_name') if isinstance(tool, dict) else getattr(tool, 'tool_name', '') for tool in message.tool_calls])}"
                )
            if message.citations:
                lines.append(f"citations: {self._stringify(message.citations)}")
        if memory.retrieval_context:
            lines.append(f"retrieval_context: {self._stringify(memory.retrieval_context)}")
        return "\n".join(lines) if lines else "No prior conversation history."

    def _stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, tuple)):
            return repr(value)
        return str(value)
