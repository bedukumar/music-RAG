"""Conversation repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ragpipe.domain.models.conversation import Conversation, ConversationMessage


class ConversationRepository(ABC):
    """Persistence contract for conversations and messages."""

    @abstractmethod
    async def create_conversation(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation."""

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load a conversation by id."""

    @abstractmethod
    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """List conversations with pagination."""

    @abstractmethod
    async def update_conversation(self, conversation: Conversation) -> Conversation:
        """Persist conversation metadata updates."""

    @abstractmethod
    async def add_message(self, message: ConversationMessage) -> ConversationMessage:
        """Append a conversation message."""

    @abstractmethod
    async def list_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ConversationMessage]:
        """List messages for a conversation."""

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and its messages."""

    @abstractmethod
    async def truncate_conversation(self, conversation_id: str, message_id: str) -> None:
        """Delete a specific message and all subsequent messages in a conversation."""
