import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ragpipe.application.services.job_manager import JobManager
from ragpipe.domain.models.modality import Modality, ProcessingStatus
from ragpipe.domain.models.pipeline import Job

@pytest.fixture
def state_store():
    return AsyncMock()

@pytest.fixture
def event_bus():
    return AsyncMock()

@pytest.fixture
def metrics():
    metrics = MagicMock()
    return metrics

@pytest.fixture
def job_manager(state_store, event_bus, metrics):
    return JobManager(
        state_store=state_store,
        event_bus=event_bus,
        metrics=metrics,
    )

@pytest.mark.asyncio
async def test_retry_job_success(job_manager, state_store, event_bus):
    job = Job(
        id="job-1",
        media_id="media-1",
        modality=Modality.AUDIO,
        status=ProcessingStatus.FAILED,
        priority=0,
        created_at=datetime.now(timezone.utc),
        retry_count=1,
        max_retries=3,
        error_message="some error",
        pipeline_state_id="old-state"
    )
    
    state_store.get_job.return_value = job
    
    updated_job = await job_manager.retry_job("job-1")
    
    assert updated_job.retry_count == 2
    assert updated_job.status == ProcessingStatus.PENDING
    assert updated_job.error_message is None
    assert updated_job.pipeline_state_id is None
    
    state_store.update_job.assert_called_once_with(updated_job)
    event_bus.publish.assert_called_once()

@pytest.mark.asyncio
async def test_retry_job_invalid_state(job_manager, state_store):
    job = Job(
        id="job-1",
        media_id="media-1",
        modality=Modality.AUDIO,
        status=ProcessingStatus.COMPLETED,
        priority=0,
        created_at=datetime.now(timezone.utc),
        retry_count=1,
        max_retries=3
    )
    
    state_store.get_job.return_value = job
    
    with pytest.raises(ValueError, match="Only failed jobs can be retried"):
        await job_manager.retry_job("job-1")

@pytest.mark.asyncio
async def test_get_dead_letter_jobs(job_manager, state_store):
    jobs = [
        # Job below max retries
        Job(
            id="job-1", media_id="media-1", modality=Modality.AUDIO,
            status=ProcessingStatus.FAILED, priority=0, created_at=datetime.now(timezone.utc),
            retry_count=2, max_retries=3
        ),
        # Job at or above max retries
        Job(
            id="job-2", media_id="media-1", modality=Modality.AUDIO,
            status=ProcessingStatus.FAILED, priority=0, created_at=datetime.now(timezone.utc),
            retry_count=3, max_retries=3
        ),
        Job(
            id="job-3", media_id="media-1", modality=Modality.AUDIO,
            status=ProcessingStatus.FAILED, priority=0, created_at=datetime.now(timezone.utc),
            retry_count=4, max_retries=3
        )
    ]
    
    state_store.list_jobs.return_value = (jobs, None)
    
    dlq_jobs = await job_manager.get_dead_letter_jobs(limit=10)
    
    assert len(dlq_jobs) == 2
    assert {j.id for j in dlq_jobs} == {"job-2", "job-3"}
    state_store.list_jobs.assert_called_once_with(status="failed", limit=50)

@pytest.mark.asyncio
async def test_cancel_job(job_manager, state_store):
    job = Job(
        id="job-1",
        media_id="media-1",
        modality=Modality.AUDIO,
        status=ProcessingStatus.PENDING,
        priority=0,
        created_at=datetime.now(timezone.utc),
        retry_count=0,
        max_retries=3
    )
    
    state_store.get_job.return_value = job
    
    await job_manager.cancel_job("job-1")
    
    assert job.status == ProcessingStatus.FAILED
    assert job.error_message == "Cancelled by user"
    assert job.completed_at is not None
    
    state_store.update_job.assert_called_once_with(job)
