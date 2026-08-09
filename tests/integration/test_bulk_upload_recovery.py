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
from ragpipe.domain.ports.message_queue import Message

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

@pytest.mark.asyncio
async def test_recovery_after_partial_processing(repos):
    bulk_repo, media_repo = repos
    
    # We simulate a crash by having the worker fail halfway through.
    # Then we re-process the same message and expect idempotent success.
    bu = BulkUpload.create("test_crash.csv", "test-bucket", "test_crash.csv")
    await bulk_repo.save(bu)

    csv_data = b"title,media_type,artist,source_url\nSong1,song,Artist1,url1\nSong2,song,Artist2,url2\n"

    mock_queue = AsyncMock()
    # Return a message once
    msg = Message(
        message_id="msg1",
        receipt_handle="handle1",
        body={"event_type": "bulk_upload.created", "bulk_upload_id": bu.id}
    )
    mock_queue.receive_messages.return_value = [msg]

    mock_storage = AsyncMock()
    mock_storage.download.return_value = csv_data

    event_bus = AsyncMock()
    metrics = MagicMock()
    state_store = AsyncMock()
    registrar = MediaRegistrar(media_repo, state_store, event_bus, metrics)
    orchestrator = AsyncMock()
    
    # First worker - fails on Song2
    class CrashingRegistrar(MediaRegistrar):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.call_count = 0
            
        async def register_media(self, media):
            self.call_count += 1
            if self.call_count == 2:
                raise asyncio.CancelledError("Crash")
            return await super().register_media(media)
            
    crashing_registrar = CrashingRegistrar(media_repo, state_store, event_bus, metrics)

    crashing_worker = BulkUploadWorker(
        queue=mock_queue,
        object_storage=mock_storage,
        bulk_upload_repository=bulk_repo,
        media_registrar=crashing_registrar,
        pipeline_orchestrator=orchestrator,
        event_bus=event_bus,
        metrics=metrics
    )

    try:
        await crashing_worker._process_message_safe(msg)
    except asyncio.CancelledError:
        pass

            # Verify first row processed
        row1 = await bulk_repo.get_row(bu.id, 1)
        assert row1.status.value == "processed"
        
        # Second worker - normal
    normal_worker = BulkUploadWorker(
        queue=mock_queue,
        object_storage=mock_storage,
        bulk_upload_repository=bulk_repo,
        media_registrar=registrar,
        pipeline_orchestrator=orchestrator,
        event_bus=event_bus,
        metrics=metrics
    )

    await normal_worker._process_message_safe(msg)

    final_bu = await bulk_repo.get(bu.id)
    assert final_bu.status == BulkUploadStatus.COMPLETED
    assert final_bu.successful_rows == 2
