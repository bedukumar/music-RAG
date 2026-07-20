"""
Pipeline Orchestrator Service.

Coordinates the execution of jobs and pipelines.
"""

import structlog
import uuid
from datetime import datetime, timezone
from typing import Callable
from dataclasses import replace

from ragpipe.application.pipelines.base_pipeline import BasePipeline
from ragpipe.domain.events.events import JobCreated
from ragpipe.domain.models.modality import Modality, ProcessingStatus
from ragpipe.domain.models.pipeline import Job
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.lock_manager import LockManager
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.exceptions import LockError

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates pipeline execution."""

    def __init__(
        self,
        media_repository: MediaRepository,
        state_store: StateStore,
        event_bus: EventBus,
        metrics: MetricsCollector,
        lock_manager: LockManager,
        pipeline_factory: Callable[[Modality], BasePipeline],
    ) -> None:
        self.media_repo = media_repository
        self.state_store = state_store
        self.event_bus = event_bus
        self.metrics = metrics
        self.lock_manager = lock_manager
        self.pipeline_factory = pipeline_factory

    async def get_processable_modalities(self, media_id: str) -> list[Modality]:
        """Get list of modalities that can be processed for a media item."""
        statuses = await self.media_repo.list_modality_statuses(media_id)
        return [
            s.modality for s in statuses
            if s.data_available and s.embedding_status in ("pending", "failed")
        ]

    async def process_media(self, media_id: str, modalities: list[Modality] | None = None) -> list[Job]:
        """Create and start jobs for a media item.

        Args:
            media_id: The media ID.
            modalities: Optional specific modalities to process. If None, process all pending.

        Returns:
            List of created jobs.
        """
        if modalities is None:
            modalities = await self.get_processable_modalities(media_id)
        else:
            # Validate that the requested modalities actually have data available
            statuses = await self.media_repo.list_modality_statuses(media_id)
            available = {s.modality for s in statuses if s.data_available}
            
            # Filter out requested modalities that lack data
            original_count = len(modalities)
            modalities = [m for m in modalities if m in available]
            
            if len(modalities) < original_count:
                log = logger.bind(media_id=media_id)
                log.info("Filtered out requested modalities due to missing data")
                
            if not modalities:
                return []
            
        jobs = []
        now = datetime.now(timezone.utc)
        
        for modality in modalities:
            job = Job(
                id=str(uuid.uuid4()),
                media_id=media_id,
                modality=modality,
                status=ProcessingStatus.PENDING,
                priority=0,
                created_at=now,
                started_at=None,
                completed_at=None,
                error_message=None,
                retry_count=0,
                max_retries=3,
                pipeline_state_id=None,
            )
            await self.state_store.save_job(job)
            jobs.append(job)
            
            await self.event_bus.publish(JobCreated(
                job_id=job.id,
                media_id=media_id,
                modality=modality,
            ))
            
            self.metrics.increment("jobs_created_total", tags={"modality": modality.value})
            
        # In a real system, a worker would pick these up.
        # For our unified process, we could trigger execute_job here asynchronously via asyncio.create_task
        # but we'll leave that to the caller/API layer to manage.
        
        return jobs

    async def execute_job(self, job: Job) -> None:
        """Execute a specific job using distributed locking.

        Args:
            job: The job to execute.
        """
        # Bind context
        log = logger.bind(job_id=job.id, media_id=job.media_id, modality=job.modality.value)
        
        lock_id = f"pipeline:{job.media_id}:{job.modality.value}"
        owner_id = f"worker-{job.id}"
        
        try:
            if not await self.lock_manager.acquire(lock_id, owner_id, ttl_seconds=3600):
                log.warning("Could not acquire lock", lock_id=lock_id)
                raise LockError(lock_id)
                
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.pipeline_state_id = f"state-{job.id}"
            await self.state_store.update_job(job)
            
            # Update modality status
            status = await self.media_repo.get_modality_status(job.media_id, job.modality)
            if status:
                status = replace(status, embedding_status="processing")
                await self.media_repo.save_modality_status(status)
                
            pipeline = self.pipeline_factory(job.modality)
            
            with self.metrics.timer("job_duration_seconds", {"modality": job.modality.value}):
                pipeline_state = await pipeline.execute(job.media_id, job)
                
            # Success
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.pipeline_state_id = pipeline_state.id
            await self.state_store.update_job(job)
            
            if status:
                status = replace(
                    status,
                    embedding_status="completed",
                    embedding_version_id=pipeline.embedding_version.id,
                    last_processed=job.completed_at,
                    error_message=None
                )
                await self.media_repo.save_modality_status(status)
                
            self.metrics.increment("jobs_completed_total", tags={"modality": job.modality.value})
            
        except Exception as e:
            log.exception("Job failed", error=str(e))
            job.status = ProcessingStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(e)
            await self.state_store.update_job(job)
            
            status = await self.media_repo.get_modality_status(job.media_id, job.modality)
            if status:
                status = replace(
                    status,
                    embedding_status="failed",
                    last_processed=job.completed_at,
                    error_message=str(e)
                )
                await self.media_repo.save_modality_status(status)
                
            self.metrics.increment("jobs_failed_total", tags={"modality": job.modality.value})
            
        finally:
            await self.lock_manager.release(lock_id, owner_id)

    async def reprocess_modality(self, media_id: str, modality: Modality) -> Job:
        """Force reprocessing of a specific modality.

        Args:
            media_id: The media ID.
            modality: The modality to reprocess.

        Returns:
            The created job.
        """
        # Validate data availability
        status = await self.media_repo.get_modality_status(media_id, modality)
        if not status or not status.data_available:
            raise ValueError(f"Cannot reprocess {modality.value}: data not available")

        # Force release any lingering locks to allow immediate execution
        lock_id = f"pipeline:{media_id}:{modality.value}"
        await self.lock_manager.force_release(lock_id)
        
        # Reset modality status
        status = await self.media_repo.get_modality_status(media_id, modality)
        if status:
            status = replace(status, embedding_status="pending", error_message=None)
            await self.media_repo.save_modality_status(status)
            
        # Delete existing embedding records
        await self.state_store.delete_embedding_records(media_id, modality)
        
        # Create and return new job
        jobs = await self.process_media(media_id, [modality])
        return jobs[0]
