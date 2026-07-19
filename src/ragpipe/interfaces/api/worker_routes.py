from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from ragpipe.application.services.worker_manager import WorkerManager
from ragpipe.application.services.job_manager import JobManager
from ragpipe.domain.models.modality import Modality

router = APIRouter(tags=["workers_queues"])
queue_router = APIRouter(prefix="/queues", tags=["queues"])
worker_router = APIRouter(prefix="/workers", tags=["workers"])

def get_worker_manager(request: Request) -> WorkerManager:
    return request.app.state.container.worker_manager

def get_job_manager(request: Request) -> JobManager:
    return request.app.state.container.job_manager

@worker_router.get("")
async def list_workers(worker_manager: WorkerManager = Depends(get_worker_manager)):
    """List active workers (status, current job, uptime)."""
    return {"workers": worker_manager.list_workers()}

@worker_router.post("/{worker_id}/pause")
async def pause_worker(worker_id: str, worker_manager: WorkerManager = Depends(get_worker_manager)):
    """Suspend job processing for a worker."""
    success = worker_manager.pause_worker(worker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worker not found")
    return {"status": "paused", "worker_id": worker_id}

@worker_router.post("/{worker_id}/resume")
async def resume_worker(worker_id: str, worker_manager: WorkerManager = Depends(get_worker_manager)):
    """Resume job processing for a worker."""
    success = worker_manager.resume_worker(worker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worker not found")
    return {"status": "active", "worker_id": worker_id}

@queue_router.get("/{modality}/stats")
async def get_queue_stats(
    modality: str,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Queue depths."""
    try:
        mod = Modality(modality)
        pending, _ = await job_manager.state_store.list_jobs(status="pending", modality=mod.value, limit=10000)
        failed, _ = await job_manager.state_store.list_jobs(status="failed", modality=mod.value, limit=10000)
        return {
            "modality": mod.value,
            "pending_count": len(pending),
            "dead_letter_count": len(failed)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@queue_router.post("/flush")
async def flush_queue(
    queue_type: str,
    modality: Optional[str] = None,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Clear DLQ or pending queue."""
    if queue_type not in ["pending", "dlq"]:
        raise HTTPException(status_code=400, detail="queue_type must be 'pending' or 'dlq'")
        
    try:
        count = await job_manager.flush_queue(queue_type, modality)
        return {"status": "flushed", "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

router.include_router(worker_router)
router.include_router(queue_router)
