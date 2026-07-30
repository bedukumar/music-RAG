from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ragpipe.domain.models.modality import Modality
from ragpipe.interfaces.api.chat_routes import get_conversation_service, router


@dataclass
class MockConversation:
    id: str = "conv-123"
    title: str = "Test Convo"
    system_prompt_version: str = "v1"
    memory_window: int = 10
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime | None = None


@dataclass
class MockMessage:
    id: str = "msg-1"
    conversation_id: str = "conv-123"
    role: object = field(default_factory=lambda: type("Role", (), {"value": "user"})())
    content: str = "Hello"
    tool_calls: list[object] = field(default_factory=list)
    tool_results: list[object] = field(default_factory=list)
    retrieval_context: list[dict[str, object]] = field(default_factory=list)
    citations: list[dict[str, object]] = field(default_factory=list)
    system_prompt_version: str = "v1"
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class StubConversationService:
    def __init__(self) -> None:
        self.create_conversation_result: MockConversation | None = None
        self.get_conversation_result: MockConversation | None = MockConversation()
        self.list_messages_result: list[object] = []
        self.chat_result: dict[str, object] = {
            "conversation_id": "conv-123",
            "message_id": "msg-1",
            "assistant_message": "Hi there!",
            "citations": [],
            "retrieved_media_ids": [],
            "tool_calls": [],
            "latency_ms": {"total": 100.0},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "conversation_title": "New Chat",
        }
        self.stream_events: list[dict[str, object]] = []
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def create_conversation(
        self,
        title: str,
        *,
        system_prompt_version: str | None = None,
        memory_window: int | None = None,
    ) -> MockConversation:
        self.calls.append(
            (
                "create_conversation",
                (title,),
                {
                    "system_prompt_version": system_prompt_version,
                    "memory_window": memory_window,
                },
            )
        )
        return self.create_conversation_result or MockConversation(title=title)

    async def get_conversation(self, conversation_id: str) -> MockConversation | None:
        self.calls.append(("get_conversation", (conversation_id,), {}))
        return self.get_conversation_result

    async def list_messages(self, conversation_id: str) -> list[object]:
        self.calls.append(("list_messages", (conversation_id,), {}))
        return self.list_messages_result

    async def delete_conversation(self, conversation_id: str) -> None:
        self.calls.append(("delete_conversation", (conversation_id,), {}))

    async def chat(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("chat", (), kwargs))
        return self.chat_result

    async def stream_chat(self, **kwargs: object):
        self.calls.append(("stream_chat", (), kwargs))
        for event in self.stream_events:
            yield event


@pytest.fixture
def mock_conversation_service() -> StubConversationService:
    return StubConversationService()


@pytest.fixture
def app(mock_conversation_service: StubConversationService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    async def override_conversation_service() -> StubConversationService:
        return mock_conversation_service

    app.dependency_overrides[get_conversation_service] = override_conversation_service
    return app


def test_create_conversation(app: FastAPI, mock_conversation_service: StubConversationService):
    mock_conversation_service.create_conversation_result = MockConversation()
    mock_conversation_service.create_conversation_result.title = "Test Convo"

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat/conversation",
                json={
                    "title": "Test Convo",
                    "system_prompt_version": "v1",
                    "memory_window": 10,
                },
            )

    response = asyncio.run(run_request())

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "conv-123"
    assert data["title"] == "Test Convo"
    assert data["system_prompt_version"] == "v1"
    assert data["memory_window"] == 10
    assert mock_conversation_service.calls == [
        (
            "create_conversation",
            ("Test Convo",),
            {"system_prompt_version": "v1", "memory_window": 10},
        )
    ]


def test_get_conversation_success(app: FastAPI, mock_conversation_service: StubConversationService):
    mock_conversation_service.get_conversation_result = MockConversation()
    mock_conversation_service.list_messages_result = ["msg1", "msg2"]

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/chat/conversation/conv-123")

    response = asyncio.run(run_request())

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "conv-123"
    assert data["message_count"] == 2
    assert mock_conversation_service.calls == [
        ("get_conversation", ("conv-123",), {}),
        ("list_messages", ("conv-123",), {}),
    ]


def test_get_conversation_not_found(app: FastAPI, mock_conversation_service: StubConversationService):
    mock_conversation_service.get_conversation_result = None

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/chat/conversation/invalid-id")

    response = asyncio.run(run_request())

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_get_messages(app: FastAPI, mock_conversation_service: StubConversationService):
    mock_conversation_service.list_messages_result = [MockMessage()]

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/chat/conversation/conv-123/messages")

    response = asyncio.run(run_request())

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "msg-1"
    assert data[0]["content"] == "Hello"
    assert mock_conversation_service.calls == [("list_messages", ("conv-123",), {})]


def test_delete_conversation(app: FastAPI, mock_conversation_service: StubConversationService):
    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.delete("/chat/conversation/conv-123")

    response = asyncio.run(run_request())

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "conversation_id": "conv-123"}
    assert mock_conversation_service.calls == [("delete_conversation", ("conv-123",), {})]


def test_chat_success(app: FastAPI, mock_conversation_service: StubConversationService):
    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                json={
                    "message": "Hi",
                    "conversation_id": "conv-123",
                    "modalities": ["transcript"],
                },
            )

    response = asyncio.run(run_request())

    assert response.status_code == 200
    data = response.json()
    assert data["assistant_message"] == "Hi there!"
    assert mock_conversation_service.calls[0][0] == "chat"
    kwargs = mock_conversation_service.calls[0][2]
    assert kwargs["message"] == "Hi"
    assert kwargs["conversation_id"] == "conv-123"
    assert kwargs["modalities"] == [Modality.TRANSCRIPT]


def test_chat_value_error_not_found(app: FastAPI, mock_conversation_service: StubConversationService):
    async def failing_chat(**kwargs: object) -> dict[str, object]:
        raise ValueError("Conversation not found")

    mock_conversation_service.chat = failing_chat

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat", json={"message": "Hi"})

    response = asyncio.run(run_request())

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_chat_value_error_bad_request(app: FastAPI, mock_conversation_service: StubConversationService):
    async def failing_chat(**kwargs: object) -> dict[str, object]:
        raise ValueError("Invalid modality")

    mock_conversation_service.chat = failing_chat

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat", json={"message": "Hi"})

    response = asyncio.run(run_request())

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid modality"


def test_chat_stream(app: FastAPI, mock_conversation_service: StubConversationService):
    mock_conversation_service.stream_events = [
        {
            "event": "delta",
            "conversation_id": "conv-1",
            "data": {"delta": "Hello"},
        },
        {
            "event": "completion",
            "conversation_id": "conv-1",
        },
    ]

    async def run_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat/stream", json={"message": "Hi"})

    response = asyncio.run(run_request())

    assert response.status_code == 200
    text = response.text
    assert "event: delta" in text
    assert "event: completion" in text
    assert "Hello" in text
