# CUI API Test Plan

## Scope

This plan covers the conversational backend APIs under `/api/v1/chat`:

- `POST /chat`
- `POST /chat/stream`
- `POST /chat/conversation`
- `GET /chat/conversation/{id}`
- `GET /chat/conversation/{id}/messages`
- `DELETE /chat/conversation/{id}`

## Goals

- Verify request validation for chat and conversation creation.
- Verify happy-path conversation lifecycle behavior.
- Verify SSE streaming format and event ordering.
- Verify error handling for missing conversations and invalid payloads.
- Verify routing uses the conversation service dependency rather than direct infrastructure access.

## Test Matrix

| Area | Scenario | Expected Result |
|---|---|---|
| Conversation creation | Create a conversation with title, memory window, and prompt version | Returns `200` and a conversation payload |
| Conversation lookup | Fetch an existing conversation | Returns `200` with `message_count` populated |
| Missing conversation | Fetch a nonexistent conversation | Returns `404` |
| Message listing | Fetch messages for a conversation | Returns ordered message list |
| Conversation delete | Delete an existing conversation | Returns `200` and delete confirmation |
| Chat happy path | Submit a chat request | Returns assistant response, citations, tool calls, and latency |
| Chat invalid conversation | Submit with a bad conversation ID | Returns `404` |
| Chat validation error | Submit an invalid request | Returns `422` |
| Streaming chat | Submit `/chat/stream` | Returns SSE events for `tool`, `retrieval`, `delta`, `completion` |

## Test Levels

- Unit tests: route-level tests with mocked conversation service.
- Integration tests: optional future tests against a test database and a mocked Gemini provider.

## Execution

Run the focused suite:

```bash
pytest tests/unit/interfaces/api/test_chat_routes.py -q
```

If you want broader backend coverage:

```bash
pytest tests/unit -q
```

## Risks

- Streaming behavior depends on the async generator contract, so mocking must stay aligned with the event envelope.
- Gemini-backed end-to-end tests require an API key and should be isolated behind an integration marker.

