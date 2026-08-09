import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ragpipe.application.services.pipeline_orchestrator import PipelineOrchestrator
from ragpipe.domain.models.modality import Modality, ModalityStatus, ProcessingStatus
from ragpipe.domain.models.pipeline import Job
from ragpipe.domain.exceptions import LockError

@pytest.fixture
def media_repo():
    return AsyncMock()

@pytest.fixture
def state_store():
    return AsyncMock()

@pytest.fixture
def event_bus():
    return AsyncMock()

@pytest.fixture
def metrics():
    metrics = MagicMock()
    # Support metrics.timer context manager
    timer_mock = MagicMock()
    timer_mock.__enter__.return_value = None
    timer_mock.__exit__.return_value = None
    metrics.timer.return_value = timer_mock
    return metrics

@pytest.fixture
def lock_manager():
    mgr = AsyncMock()
    mgr.acquire.return_value = True
    return mgr

@pytest.fixture
def pipeline_factory():
    def _factory(modality):
        pipeline = AsyncMock()
        # Mock pipeline execution result
        pipeline_state = MagicMock()
        pipeline_state.id = f"mock-state-{uuid.uuid4()}"
        pipeline.execute.return_value = pipeline_state
        pipeline.embedding_version.id = "v1"
        return pipeline
    return _factory

@pytest.fixture
def orchestrator(media_repo, state_store, event_bus, metrics, lock_manager, pipeline_factory):
    return PipelineOrchestrator(
        media_repository=media_repo,
        state_store=state_store,
        event_bus=event_bus,
        metrics=metrics,
        lock_manager=lock_manager,
        pipeline_factory=pipeline_factory,
    )

@pytest.mark.asyncio
async def test_process_media_creates_modality_specific_jobs(orchestrator, media_repo):
    media_id = "test-media"
    statuses = [
        ModalityStatus(media_id=media_id, modality=Modality.AUDIO, data_available=True, embedding_status="pending"),
        ModalityStatus(media_id=media_id, modality=Modality.TRANSCRIPT, data_available=True, embedding_status="pending"),
        ModalityStatus(media_id=media_id, modality=Modality.METADATA, data_available=False, embedding_status="pending"),
    ]
    media_repo.list_modality_statuses.return_value = statuses

    jobs = await orchestrator.process_media(media_id)
    
    assert len(jobs) == 2
    modalities = {j.modality for j in jobs}
    assert modalities == {Modality.AUDIO, Modality.TRANSCRIPT}
    
    for job in jobs:
        assert job.media_id == media_id
        assert job.status == ProcessingStatus.PENDING

@pytest.mark.asyncio
async def test_execute_job_success_state_transitions(orchestrator, state_store, media_repo, lock_manager):
    job = Job(
        id="test-job",
        media_id="test-media",
        modality=Modality.AUDIO,
        status=ProcessingStatus.PENDING,
        priority=0,
        created_at=datetime.now(timezone.utc),
        max_retries=3
    )
    
    status = ModalityStatus(media_id="test-media", modality=Modality.AUDIO, data_available=True, embedding_status="pending")
    media_repo.get_modality_status.return_value = status
    
    await orchestrator.execute_job(job)
    
    # Check lock acquired and released
    lock_manager.acquire.assert_called_once()
    lock_manager.release.assert_called_once()
    
    assert state_store.update_job.call_count == 2
    # First update sets PROCESSING
    # Second update sets COMPLETED
    assert job.status == ProcessingStatus.COMPLETED
    assert job.completed_at is not None

@pytest.mark.asyncio
async def test_execute_job_lock_failure(orchestrator, state_store, media_repo, lock_manager):
    job = Job(
        id="test-job",
        media_id="test-media",
        modality=Modality.AUDIO,
        status=ProcessingStatus.PENDING,
        priority=0,
        created_at=datetime.now(timezone.utc),
        max_retries=3
    )
    
    lock_manager.acquire.return_value = False
    
    status = ModalityStatus(media_id="test-media", modality=Modality.AUDIO, data_available=True, embedding_status="pending")
    media_repo.get_modality_status.return_value = status
    await orchestrator.execute_job(job)
    
    # Lock failed, so job should be updated to FAILED
    state_store.update_job.assert_called_once()
    updated_job = state_store.update_job.call_args[0][0]
    assert updated_job.status == ProcessingStatus.FAILED
    assert "pipeline:test-media:audio" in updated_job.error_message
