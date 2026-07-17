"""
Job Manager Service.

Handles manual interventions for jobs (retry, cancel, dead letter queue).
"""

from datetime import datetime, timezone

from ragpipe.domain.events.events import JobRetried
from ragpipe.domain.models.modality import ProcessingStatus
from ragpipe.domain.models.pipeline import Job
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore


class JobManager:
    """Service for managing jobs (retries, cancellations)."""

    def __init__(
        self,
        state_store: StateStore,
        event_bus: EventBus,
        metrics: MetricsCollector,
    ) -> None:
        self.state_store = state_store
        self.event_bus = event_bus
        self.metrics = metrics

    async def cancel_job(self, job_id: str) -> None:
        """Cancel a pending or processing job.

        Args:
            job_id: The job ID.
        """
        job = await self.state_store.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
            
        if job.status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            raise ValueError(f"Cannot cancel job in state {job.status.value}")
            
        job.status = ProcessingStatus.FAILED
        job.error_message = "Cancelled by user"
        job.completed_at = datetime.now(timezone.utc)
        
        await self.state_store.update_job(job)
        self.metrics.increment("jobs_cancelled_total")

    async def retry_job(self, job_id: str) -> Job:
        """Retry a failed job.

        Args:
            job_id: The job ID.

        Returns:
            The updated job ready for processing.
        """
        job = await self.state_store.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
            
        if job.status != ProcessingStatus.FAILED:
            raise ValueError(f"Only failed jobs can be retried (current: {job.status.value})")
            
        job.retry_count += 1
        job.status = ProcessingStatus.PENDING
        job.error_message = None
        job.completed_at = None
        job.started_at = None
        
        # Unlink previous pipeline state so it runs fresh
        job.pipeline_state_id = None
        
        await self.state_store.update_job(job)
        
        await self.event_bus.publish(JobRetried(
            job_id=job.id,
            retry_count=job.retry_count,
        ))
        
        self.metrics.increment("jobs_retried_total")
        
        return job

    async def get_dead_letter_jobs(self, limit: int = 50) -> list[Job]:
        """Get jobs that have exhausted all retries (Dead Letter Queue).

        Args:
            limit: Maximum number to return.

        Returns:
            List of dead letter jobs.
        """
        # A simple implementation just fetching failed jobs where retry_count >= max_retries
        jobs, _ = await self.state_store.list_jobs(status="failed", limit=limit * 5)
        
        dead_letter = [j for j in jobs if j.retry_count >= j.max_retries]
        return dead_letter[:limit]
