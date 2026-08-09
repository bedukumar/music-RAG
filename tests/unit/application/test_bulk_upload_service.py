"""Unit tests for BulkUploadService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ragpipe.application.services.bulk_upload_service import BulkUploadService
from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadStatus
from ragpipe.domain.ports.object_storage import ObjectStorageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_object_storage():
    s = AsyncMock()
    s.upload.return_value = "bulk-uploads/test-id/songs.csv"
    return s


@pytest.fixture()
def mock_message_queue():
    q = AsyncMock()
    q.send_message.return_value = "sqs-msg-123"
    return q


@pytest.fixture()
def mock_bulk_upload_repo():
    r = AsyncMock()
    r.save.side_effect = lambda bu: bu  # return the same object
    return r


@pytest.fixture()
def mock_event_bus():
    return AsyncMock()


@pytest.fixture()
def mock_metrics():
    m = MagicMock()
    m.increment = MagicMock()
    return m


@pytest.fixture()
def service(
    mock_object_storage,
    mock_message_queue,
    mock_bulk_upload_repo,
    mock_event_bus,
    mock_metrics,
):
    return BulkUploadService(
        object_storage=mock_object_storage,
        message_queue=mock_message_queue,
        bulk_upload_repository=mock_bulk_upload_repo,
        event_bus=mock_event_bus,
        metrics=mock_metrics,
        s3_bucket="ragpipe-bulk-uploads",
    )


# ---------------------------------------------------------------------------
# create_bulk_upload tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_bulk_upload_happy_path(
    service,
    mock_object_storage,
    mock_message_queue,
    mock_bulk_upload_repo,
):
    """Happy path: CSV file should be uploaded to S3, DB record created, SQS published."""
    file_bytes = b"title,media_type\nSong1,song\n"
    result = await service.create_bulk_upload(
        file_bytes=file_bytes,
        original_filename="songs.csv",
        content_type="text/csv",
    )

    # S3 upload called
    mock_object_storage.upload.assert_called_once()
    upload_kwargs = mock_object_storage.upload.call_args.kwargs
    assert upload_kwargs["data"] == file_bytes
    assert upload_kwargs["content_type"] == "text/csv"

    # DB record saved
    mock_bulk_upload_repo.save.assert_called_once()

    # SQS message published
    mock_message_queue.send_message.assert_called_once()
    sqs_body = mock_message_queue.send_message.call_args.args[0]
    assert sqs_body["event_type"] == "bulk_upload.created"
    assert "bulk_upload_id" in sqs_body

    # Result is a BulkUpload in PENDING state
    assert isinstance(result, BulkUpload)
    assert result.status == BulkUploadStatus.PENDING


@pytest.mark.asyncio
async def test_create_bulk_upload_rejects_invalid_type(service):
    """Non-CSV/XLSX files should raise ValueError before touching S3."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        await service.create_bulk_upload(
            file_bytes=b"binary data",
            original_filename="data.pdf",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_create_bulk_upload_accepts_xlsx(service, mock_object_storage):
    """XLSX files should be accepted."""
    file_bytes = b"PK\x03\x04"  # Minimal XLSX magic bytes
    await service.create_bulk_upload(
        file_bytes=file_bytes,
        original_filename="songs.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    mock_object_storage.upload.assert_called_once()


@pytest.mark.asyncio
async def test_create_bulk_upload_propagates_s3_error(service, mock_object_storage):
    """ObjectStorageError from S3 should propagate to the caller."""
    mock_object_storage.upload.side_effect = ObjectStorageError("S3 unreachable")

    with pytest.raises(ObjectStorageError):
        await service.create_bulk_upload(
            file_bytes=b"a,b\n1,2",
            original_filename="data.csv",
            content_type="text/csv",
        )


# ---------------------------------------------------------------------------
# cancel_bulk_upload tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_pending_upload(service, mock_bulk_upload_repo):
    """A PENDING upload should be cancellable."""
    bu = BulkUpload.create("k", "b", "f.csv")
    mock_bulk_upload_repo.get.return_value = bu

    result = await service.cancel_bulk_upload(bu.id)

    assert result.status == BulkUploadStatus.CANCELLED
    mock_bulk_upload_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_completed_upload_raises(service, mock_bulk_upload_repo):
    """Cancelling a terminal-state upload should raise ValueError."""
    bu = BulkUpload.create("k", "b", "f.csv")
    bu.mark_completed()
    mock_bulk_upload_repo.get.return_value = bu

    with pytest.raises(ValueError, match="terminal"):
        await service.cancel_bulk_upload(bu.id)


@pytest.mark.asyncio
async def test_cancel_missing_upload_raises(service, mock_bulk_upload_repo):
    """Cancelling a non-existent upload should raise ValueError."""
    mock_bulk_upload_repo.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await service.cancel_bulk_upload("nonexistent-id")

# ---------------------------------------------------------------------------
# Additional tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_bulk_upload_sqs_failure(service, mock_message_queue):
    from ragpipe.domain.ports.message_queue import MessageQueueError
    mock_message_queue.send_message.side_effect = MessageQueueError("Queue unavailable")
    
    with pytest.raises(MessageQueueError):
        await service.create_bulk_upload(
            file_bytes=b"a,b\n1,2",
            original_filename="data.csv",
            content_type="text/csv",
        )

@pytest.mark.asyncio
async def test_get_bulk_upload_found(service, mock_bulk_upload_repo):
    bu = BulkUpload.create("k", "b", "f.csv")
    mock_bulk_upload_repo.get.return_value = bu
    result = await service.get_bulk_upload(bu.id)
    assert result == bu

@pytest.mark.asyncio
async def test_get_bulk_upload_not_found(service, mock_bulk_upload_repo):
    mock_bulk_upload_repo.get.return_value = None
    result = await service.get_bulk_upload("missing")
    assert result is None

@pytest.mark.asyncio
async def test_list_bulk_uploads(service, mock_bulk_upload_repo):
    bu = BulkUpload.create("k", "b", "f.csv")
    mock_bulk_upload_repo.list.return_value = ([bu], 1)
    
    items, count = await service.list_bulk_uploads(status="PENDING", limit=10, offset=5)
    
    mock_bulk_upload_repo.list.assert_called_once_with(status="PENDING", limit=10, offset=5)
    assert items == [bu]
    assert count == 1

@pytest.mark.asyncio
async def test_list_bulk_upload_rows(service, mock_bulk_upload_repo):
    mock_bulk_upload_repo.list_rows.return_value = (["row1"], 1)
    
    items, count = await service.list_bulk_upload_rows(bulk_upload_id="123", status="failed", limit=50, offset=0)
    
    mock_bulk_upload_repo.list_rows.assert_called_once_with(bulk_upload_id="123", status="failed", limit=50, offset=0)
    assert items == ["row1"]
    assert count == 1
