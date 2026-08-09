"""Integration tests for bulk upload using a real LocalStack instance.

These tests require:
  - LocalStack running: docker compose -f deployment/localstack/docker-compose.localstack.yml up -d
  - Environment variables from .env.localstack sourced
  - ragpipe[bulk] installed

Run with:
  pytest tests/integration/test_bulk_upload_localstack.py -m "integration and localstack" -v

The tests create real S3 objects and SQS messages and verify the end-to-end
state of the SQLite database after the worker processes a batch.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest

# Skip the entire module if boto3 is not installed
boto3 = pytest.importorskip("boto3")

# Only run when LOCALSTACK is explicitly available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.localstack,
]

ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://localhost:4566")
BUCKET = os.getenv("S3_BUCKET", "ragpipe-bulk-uploads")
QUEUE_URL = os.getenv("SQS_QUEUE_URL", "http://localhost:4566/000000000000/ragpipe-bulk-uploads-test")
REGION = os.getenv("AWS_REGION", "us-east-1")

CSV_CONTENT = b"title,media_type,artist,language,source_url\nTest Song A,song,Artist A,en\nTest Song B,song,Artist B,en\n"


@pytest.fixture(scope="module")
def s3_client():
    return boto3.client(
        "s3",
        region_name=REGION,
        endpoint_url=ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        verify=False,
    )


@pytest.fixture(scope="module")
def sqs_client():
    client = boto3.client(
        "sqs",
        region_name=REGION,
        endpoint_url=ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    # Ensure queue exists
    queue_name = QUEUE_URL.split("/")[-1]
    client.create_queue(QueueName=queue_name)
    return client


@pytest.fixture(scope="module")
def s3_storage():
    from ragpipe.infrastructure.storage.s3_object_storage import S3ObjectStorage
    return S3ObjectStorage(
        bucket=BUCKET,
        region=REGION,
        endpoint_url=ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture(scope="module")
def sqs_queue(sqs_client):
    from ragpipe.infrastructure.queue.sqs_message_queue import SQSMessageQueue
    return SQSMessageQueue(
        queue_url=QUEUE_URL,
        region=REGION,
        endpoint_url=ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


# ---------------------------------------------------------------------------
# S3 integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s3_upload_download_delete(s3_storage):
    """Upload, download, and delete a real S3 object via LocalStack."""
    key = f"test-integration/{uuid.uuid4()}/test.csv"
    content = b"hello,world\n1,2\n"

    returned_key = await s3_storage.upload(key=key, data=content, content_type="text/csv")
    assert returned_key == key

    downloaded = await s3_storage.download(key)
    assert downloaded == content

    meta = await s3_storage.get_metadata(key)
    assert meta["content_length"] == len(content)

    deleted = await s3_storage.delete(key)
    assert deleted is True


@pytest.mark.asyncio
async def test_s3_download_missing_key_raises(s3_storage):
    """Downloading a non-existent key should raise ObjectNotFoundError."""
    from ragpipe.domain.ports.object_storage import ObjectNotFoundError

    with pytest.raises(ObjectNotFoundError):
        await s3_storage.download("definitely/does/not/exist.csv")


# ---------------------------------------------------------------------------
# SQS integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sqs_send_receive_delete(sqs_queue):
    """Send a message, receive it, then delete it via LocalStack."""
    payload = {"event_type": "bulk_upload.created", "bulk_upload_id": str(uuid.uuid4())}

    msg_id = await sqs_queue.send_message(payload, delay_seconds=0)
    assert msg_id

    # Poll until message appears (up to 10 seconds)
    messages = []
    for _ in range(20):
        messages = await sqs_queue.receive_messages(max_messages=1, wait_seconds=1)
        if messages:
            break
        await asyncio.sleep(1)

    assert messages, "No message received from SQS within timeout"
    msg = messages[0]
    assert msg.body["bulk_upload_id"] == payload["bulk_upload_id"]

    await sqs_queue.delete_message(msg.receipt_handle)


@pytest.mark.asyncio
async def test_sqs_batch_send(sqs_queue):
    """Batch of 3 messages should all succeed."""
    from ragpipe.domain.ports.message_queue import BatchSendEntry

    entries = [
        BatchSendEntry(id=f"e{i}", body={"n": i})
        for i in range(3)
    ]
    result = await sqs_queue.send_message_batch(entries)

    assert len(result.successful) == 3
    assert result.failed == {}

    # Drain the messages so they don't affect other tests
    for _ in range(3):
        msgs = await sqs_queue.receive_messages(max_messages=1, wait_seconds=1)
        for m in msgs:
            await sqs_queue.delete_message(m.receipt_handle)
import os
import uuid
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadStatus
from ragpipe.workers.bulk_upload_worker import BulkUploadWorker
from ragpipe.infrastructure.database.engine import DatabaseEngine
from ragpipe.config.settings import Settings, DatabaseSettings
from ragpipe.infrastructure.database.bulk_upload_repository import SQLAlchemyBulkUploadRepository as BulkUploadRepository
from ragpipe.infrastructure.database.media_repository import SQLAlchemyMediaRepository as MediaRepository
from ragpipe.application.services.media_registrar import MediaRegistrar

@pytest.fixture(scope="function")
async def db_engine():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        settings = Settings(database=DatabaseSettings(database_url=f"sqlite+aiosqlite:///{tmp.name}"))
        engine = DatabaseEngine(settings)
        await engine.initialize()
        await engine.create_tables()
        yield engine
        await engine.dispose()

@pytest.fixture(scope="function")
async def repos(db_engine):
    from sqlalchemy.ext.asyncio import async_scoped_session
    from asyncio import current_task
    shared_session = async_scoped_session(
        db_engine.session_factory,
        scopefunc=current_task
    )
    bulk_repo = BulkUploadRepository(shared_session)
    media_repo = MediaRepository(shared_session)
    return bulk_repo, media_repo

@pytest.fixture(scope="function")
def worker(repos, s3_storage, sqs_queue):
    bulk_repo, media_repo = repos
    event_bus = AsyncMock()
    metrics = MagicMock()
    # Need state store for MediaRegistrar, mocked
    state_store = AsyncMock()
    registrar = MediaRegistrar(media_repo, state_store, event_bus, metrics)
    orchestrator = AsyncMock()
    
    return BulkUploadWorker(
        queue=sqs_queue,
        object_storage=s3_storage,
        bulk_upload_repository=bulk_repo,
        media_registrar=registrar,
        pipeline_orchestrator=orchestrator,
        event_bus=event_bus,
        metrics=metrics
    )

@pytest.mark.asyncio
async def test_full_pipeline_integration(worker, s3_storage, sqs_queue, repos):
    bulk_repo, media_repo = repos
    bu = BulkUpload.create("test.csv", "test-bucket", "test.csv")
    await bulk_repo.save(bu)

    csv_data = b"title,media_type,artist,language,source_url\nSong1,song,Artist1,en,url1\nSong2,song,Artist2,en,url2\n"
    await s3_storage.upload(bu.object_key, csv_data, "text/csv")

    payload = {"event_type": "bulk_upload.created", "bulk_upload_id": bu.id}
    await sqs_queue.send_message(payload)


    # run worker single step
    msgs = await sqs_queue.receive_messages(max_messages=1, wait_seconds=2)
    assert msgs, "No message received"
    await worker._process_message_safe(msgs[0])


    # Verify DB state
    updated_bu = await bulk_repo.get(bu.id)
    assert updated_bu.status == BulkUploadStatus.COMPLETED
    assert updated_bu.successful_rows == 2
    assert updated_bu.failed_rows == 0

@pytest.mark.asyncio
async def test_mixed_rows_completed_with_errors(worker, s3_storage, sqs_queue, repos):
    bulk_repo, media_repo = repos
    bu = BulkUpload.create("test2.csv", "test-bucket", "test2.csv")
    await bulk_repo.save(bu)

    # Missing title on second row
    csv_data = b"title,media_type,artist,source_url\nSong1,song,Artist1,url1\n,song,Artist2,url2\n"
    await s3_storage.upload(bu.object_key, csv_data, "text/csv")

    payload = {"event_type": "bulk_upload.created", "bulk_upload_id": bu.id}
    await sqs_queue.send_message(payload)


    # run worker single step
    msgs = await sqs_queue.receive_messages(max_messages=1, wait_seconds=2)
    assert msgs, "No message received"
    await worker._process_message_safe(msgs[0])


    updated_bu = await bulk_repo.get(bu.id)
    assert updated_bu.status == BulkUploadStatus.COMPLETED_WITH_ERRORS
    assert updated_bu.successful_rows == 1
    assert updated_bu.failed_rows == 1
