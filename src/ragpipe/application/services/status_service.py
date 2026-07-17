"""
Status Service.

Provides consolidated views of system status, jobs, and pipeline states.
"""

from typing import Any, Optional

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore


class StatusService:
    """Service for querying system status."""

    def __init__(
        self,
        state_store: StateStore,
        media_repository: MediaRepository,
        metrics: MetricsCollector,
    ) -> None:
        self.state_store = state_store
        self.media_repo = media_repository
        self.metrics = metrics

    async def get_pipeline_status(self, media_id: str) -> dict[str, Any]:
        """Get comprehensive pipeline status for a media item.

        Args:
            media_id: The media ID.

        Returns:
            Dictionary containing media info, modality statuses, and pipelines.
        """
        media = await self.media_repo.get(media_id)
        if not media:
            return {}
            
        statuses = await self.media_repo.list_modality_statuses(media_id)
        
        result = {
            "media_id": media_id,
            "title": media.title,
            "media_type": media.media_type.value,
            "modality_statuses": [
                {
                    "modality": s.modality.value,
                    "data_available": s.data_available,
                    "embedding_status": s.embedding_status,
                    "last_processed": s.last_processed.isoformat() if s.last_processed else None,
                    "error_message": s.error_message,
                }
                for s in statuses
            ],
            "pipelines": {},
        }
        
        # Get latest pipeline state for each modality
        for modality in Modality:
            state = await self.state_store.get_pipeline_state(media_id, modality)
            if state:
                result["pipelines"][modality.value] = {
                    "state_id": state.id,
                    "job_id": state.job_id,
                    "overall_status": state.overall_status.value,
                    "current_stage": state.current_stage.value if state.current_stage else None,
                    "created_at": state.created_at.isoformat(),
                    "updated_at": state.updated_at.isoformat(),
                    "stages": [
                        {
                            "stage": sr.stage.value,
                            "status": sr.status.value,
                            "started_at": sr.started_at.isoformat() if sr.started_at else None,
                            "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
                            "duration_ms": (sr.completed_at - sr.started_at).total_seconds() * 1000 if sr.completed_at and sr.started_at else None,
                            "error_message": sr.error_message,
                        }
                        for sr in state.stages
                    ]
                }
                
        return result

    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get detailed job status including its pipeline state."""
        job = await self.state_store.get_job(job_id)
        if not job:
            return None
            
        result = {
            "id": job.id,
            "media_id": job.media_id,
            "modality": job.modality.value,
            "status": job.status.value,
            "priority": job.priority,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "pipeline_state": None,
        }
        
        if job.pipeline_state_id:
            state = await self.state_store.get_pipeline_state(job.media_id, job.modality, job.id)
            if state:
                result["pipeline_state"] = {
                    "id": state.id,
                    "overall_status": state.overall_status.value,
                    "current_stage": state.current_stage.value if state.current_stage else None,
                    "stages": [
                        {
                            "stage": sr.stage.value,
                            "status": sr.status.value,
                            "duration_ms": (sr.completed_at - sr.started_at).total_seconds() * 1000 if sr.completed_at and sr.started_at else None,
                        }
                        for sr in state.stages
                    ]
                }
                
        return result

    async def list_jobs(
        self,
        status: Optional[str] = None,
        modality: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List jobs with optional filtering."""
        jobs, total = await self.state_store.list_jobs(status, modality, limit, offset)
        
        job_dicts = []
        for job in jobs:
            job_dicts.append({
                "id": job.id,
                "media_id": job.media_id,
                "modality": job.modality.value,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
            })
            
        return job_dicts, total

    async def get_system_stats(self) -> dict[str, Any]:
        """Get high-level system statistics."""
        # This would typically use the metrics_collector if it exposes a readable API,
        # or do some aggregate queries via state_store and media_repository.
        # For this simplified implementation, we'll do some basic queries.
        
        # Get total media count
        _, total_media = await self.media_repo.list_all(limit=1)
        
        # We can use the state_store list_jobs to get counts per status by doing limit=1
        _, pending_jobs = await self.state_store.list_jobs(status="pending", limit=1)
        _, processing_jobs = await self.state_store.list_jobs(status="processing", limit=1)
        _, completed_jobs = await self.state_store.list_jobs(status="completed", limit=1)
        _, failed_jobs = await self.state_store.list_jobs(status="failed", limit=1)
        
        return {
            "total_media": total_media,
            "jobs": {
                "pending": pending_jobs,
                "processing": processing_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
            }
        }
