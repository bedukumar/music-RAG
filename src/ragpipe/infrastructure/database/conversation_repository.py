"""SQLAlchemy conversation repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragpipe.domain.models.conversation import (
    ChatRole,
    Conversation,
    ConversationMessage,
    ToolInvocation,
    ToolResult,
)
from ragpipe.domain.ports.conversation_repository import ConversationRepository
from ragpipe.infrastructure.database.models import ConversationMessageORM, ConversationORM


class SQLAlchemyConversationRepository(ConversationRepository):
    """Persist conversations and messages in SQLite via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _conversation_to_orm(self, conversation: Conversation) -> ConversationORM:
        return ConversationORM(
            id=conversation.id,
            title=conversation.title,
            system_prompt_version=conversation.system_prompt_version,
            memory_window=conversation.memory_window,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at,
        )

    def _orm_to_conversation(self, orm: ConversationORM) -> Conversation:
        return Conversation(
            id=orm.id,
            title=orm.title,
            system_prompt_version=orm.system_prompt_version,
            memory_window=orm.memory_window,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            last_message_at=orm.last_message_at,
        )

    def _tool_invocation_from_dict(self, data: dict) -> ToolInvocation:
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return ToolInvocation(
            invocation_id=data.get("invocation_id", ""),
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments", {}) or {},
            created_at=created_at or datetime.now(timezone.utc),
            latency_ms=data.get("latency_ms"),
        )

    def _tool_result_from_dict(self, data: dict) -> ToolResult:
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return ToolResult(
            invocation_id=data.get("invocation_id", ""),
            tool_name=data.get("tool_name", ""),
            success=bool(data.get("success", False)),
            result=data.get("result", {}) or {},
            error=data.get("error"),
            created_at=created_at or datetime.now(timezone.utc),
            latency_ms=data.get("latency_ms"),
        )

    def _message_to_orm(self, message: ConversationMessage) -> ConversationMessageORM:
        return ConversationMessageORM(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role.value,
            content=message.content,
            tool_calls=[
                {
                    "invocation_id": tool.invocation_id,
                    "tool_name": tool.tool_name,
                    "arguments": tool.arguments,
                    "created_at": tool.created_at.isoformat(),
                    "latency_ms": tool.latency_ms,
                }
                for tool in message.tool_calls
            ],
            tool_results=[
                {
                    "invocation_id": result.invocation_id,
                    "tool_name": result.tool_name,
                    "success": result.success,
                    "result": result.result,
                    "error": result.error,
                    "created_at": result.created_at.isoformat(),
                    "latency_ms": result.latency_ms,
                }
                for result in message.tool_results
            ],
            retrieval_context=message.retrieval_context,
            citations=message.citations,
            system_prompt_version=message.system_prompt_version,
            message_metadata=message.metadata,
            created_at=message.created_at,
        )

    def _orm_to_message(self, orm: ConversationMessageORM) -> ConversationMessage:
        tool_calls = [self._tool_invocation_from_dict(item) for item in orm.tool_calls or []]
        tool_results = [self._tool_result_from_dict(item) for item in orm.tool_results or []]
        return ConversationMessage(
            id=orm.id,
            conversation_id=orm.conversation_id,
            role=ChatRole(orm.role),
            content=orm.content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            retrieval_context=orm.retrieval_context or [],
            citations=orm.citations or [],
            system_prompt_version=orm.system_prompt_version,
            metadata=orm.message_metadata or {},
            created_at=orm.created_at,
        )

    async def create_conversation(self, conversation: Conversation) -> Conversation:
        self._session.add(self._conversation_to_orm(conversation))
        await self._session.commit()
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        stmt = select(ConversationORM).where(ConversationORM.id == conversation_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._orm_to_conversation(orm) if orm else None

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        count_stmt = select(func.count(ConversationORM.id))
        total = (await self._session.execute(count_stmt)).scalar() or 0
        stmt = (
            select(ConversationORM)
            .order_by(ConversationORM.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        items = [self._orm_to_conversation(row) for row in result.scalars().all()]
        return items, total

    async def update_conversation(self, conversation: Conversation) -> Conversation:
        stmt = select(ConversationORM).where(ConversationORM.id == conversation.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = self._conversation_to_orm(conversation)
            self._session.add(orm)
        else:
            orm.title = conversation.title
            orm.system_prompt_version = conversation.system_prompt_version
            orm.memory_window = conversation.memory_window
            orm.updated_at = conversation.updated_at
            orm.last_message_at = conversation.last_message_at
        await self._session.commit()
        return conversation

    async def add_message(self, message: ConversationMessage) -> ConversationMessage:
        self._session.add(self._message_to_orm(message))
        stmt = select(ConversationORM).where(ConversationORM.id == message.conversation_id)
        result = await self._session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.updated_at = message.created_at
            conversation.last_message_at = message.created_at
        await self._session.commit()
        return message

    async def list_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessageORM)
            .where(ConversationMessageORM.conversation_id == conversation_id)
            .order_by(ConversationMessageORM.created_at.asc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [self._orm_to_message(row) for row in result.scalars().all()]

    async def delete_conversation(self, conversation_id: str) -> None:
        await self._session.execute(
            delete(ConversationORM).where(ConversationORM.id == conversation_id)
        )
        await self._session.commit()
