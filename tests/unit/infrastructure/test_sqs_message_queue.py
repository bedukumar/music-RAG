"""Unit tests for SQSMessageQueue adapter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ragpipe.domain.ports.message_queue import BatchSendEntry, MessageQueueError


@pytest.fixture()
def mock_sqs_client():
    return MagicMock()


@pytest.fixture()
def sqs_queue(mock_sqs_client):
    from ragpipe.infrastructure.queue.sqs_message_queue import SQSMessageQueue

    q = SQSMessageQueue.__new__(SQSMessageQueue)
    q._queue_url = "http://localhost:4566/000000000000/test-queue"
    q._visibility_timeout = 300
    q._wait_time_seconds = 20
    q._client = mock_sqs_client
    return q



# ---------------------------------------------------------------------------
# send_message tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_returns_message_id(sqs_queue, mock_sqs_client):
    """send_message() should return the broker-assigned MessageId."""
    mock_sqs_client.send_message.return_value = {"MessageId": "msg-123"}

    msg_id = await sqs_queue.send_message({"event_type": "bulk_upload.created", "bulk_upload_id": "abc"})

    assert msg_id == "msg-123"
    mock_sqs_client.send_message.assert_called_once()
    call_kwargs = mock_sqs_client.send_message.call_args.kwargs
    body = json.loads(call_kwargs["MessageBody"])
    assert body["bulk_upload_id"] == "abc"


@pytest.mark.asyncio
async def test_send_message_raises_on_failure(sqs_queue, mock_sqs_client):
    mock_sqs_client.send_message.side_effect = Exception("SQS unavailable")

    with pytest.raises(MessageQueueError):
        await sqs_queue.send_message({"key": "value"})


# ---------------------------------------------------------------------------
# send_message_batch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_batch_success(sqs_queue, mock_sqs_client):
    """Batch of 2 messages should return 2 successful IDs."""
    mock_sqs_client.send_message_batch.return_value = {
        "Successful": [{"Id": "e1", "MessageId": "m1"}, {"Id": "e2", "MessageId": "m2"}],
        "Failed": [],
    }

    entries = [
        BatchSendEntry(id="e1", body={"n": 1}),
        BatchSendEntry(id="e2", body={"n": 2}),
    ]
    result = await sqs_queue.send_message_batch(entries)

    assert result.successful == ["e1", "e2"]
    assert result.failed == {}


@pytest.mark.asyncio
async def test_send_message_batch_rejects_more_than_10():
    """Passing > 10 entries should raise ValueError before calling SQS."""
    from ragpipe.infrastructure.queue.sqs_message_queue import SQSMessageQueue

    q = SQSMessageQueue.__new__(SQSMessageQueue)
    q._queue_url = "http://example.com"

    with pytest.raises(ValueError, match="max 10"):
        await q.send_message_batch([BatchSendEntry(id=str(i), body={}) for i in range(11)])


# ---------------------------------------------------------------------------
# receive_messages tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receive_messages_parses_json_body(sqs_queue, mock_sqs_client):
    """receive_messages() should deserialise the JSON body and set receive_count."""
    payload = {"event_type": "bulk_upload.created", "bulk_upload_id": "xyz"}
    mock_sqs_client.receive_message.return_value = {
        "Messages": [
            {
                "MessageId": "msg-1",
                "ReceiptHandle": "rh-1",
                "Body": json.dumps(payload),
                "Attributes": {"ApproximateReceiveCount": "2"},
            }
        ]
    }

    messages = await sqs_queue.receive_messages(max_messages=1, wait_seconds=0)

    assert len(messages) == 1
    msg = messages[0]
    assert msg.message_id == "msg-1"
    assert msg.receipt_handle == "rh-1"
    assert msg.body["bulk_upload_id"] == "xyz"
    assert msg.receive_count == 2


@pytest.mark.asyncio
async def test_receive_messages_empty_queue(sqs_queue, mock_sqs_client):
    """receive_messages() should return an empty list when the queue is empty."""
    mock_sqs_client.receive_message.return_value = {}

    messages = await sqs_queue.receive_messages()

    assert messages == []


# ---------------------------------------------------------------------------
# delete_message tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_message_calls_sqs(sqs_queue, mock_sqs_client):
    """delete_message() should call the SQS delete_message API."""
    mock_sqs_client.delete_message.return_value = {}

    await sqs_queue.delete_message("rh-abc")

    mock_sqs_client.delete_message.assert_called_once_with(
        QueueUrl=sqs_queue._queue_url,
        ReceiptHandle="rh-abc",
    )


@pytest.mark.asyncio
async def test_delete_message_raises_on_failure(sqs_queue, mock_sqs_client):
    mock_sqs_client.delete_message.side_effect = Exception("Forbidden")

    with pytest.raises(MessageQueueError):
        await sqs_queue.delete_message("rh-bad")


# ---------------------------------------------------------------------------
# change_visibility tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_change_visibility_does_not_raise_on_failure(sqs_queue, mock_sqs_client):
    """change_visibility is best-effort — failures should be logged but not raised."""
    mock_sqs_client.change_message_visibility.side_effect = Exception("Network error")

    # Should NOT raise
    await sqs_queue.change_visibility("rh-xyz", 60)
