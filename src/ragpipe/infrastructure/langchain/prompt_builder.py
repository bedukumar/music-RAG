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

    def build_search_prompt(self, retrieved_context: str) -> str:
        template = self._load("search_prompt")
        return template.format(
            retrieved_context=retrieved_context or "No matching songs found.",
        )

    def build_tool_prompt(self, tool_outputs: str) -> str:
        template = self._load("tool_prompt")
        return template.format(
            tool_outputs=tool_outputs or "No additional context.",
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
        search_prompt = self.build_search_prompt(retrieved_context)
        tool_prompt = self.build_tool_prompt(tool_outputs)
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
        """Format conversation history cleanly without exposing internal metadata."""

        lines: list[str] = []
        for message in memory.messages:
            role = message.role.value
            lines.append(f"{role}: {message.content}")
        return "\n".join(lines) if lines else "No prior conversation history."

    def _stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, tuple)):
            return repr(value)
        return str(value)
