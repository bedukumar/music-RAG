"""
Job API Routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks

from ragpipe.interfaces.schemas.job_schemas import JobListResponse
from ragpipe.interfaces.schemas.pipeline_schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_status_service(request: Request):
    return request.app.state.container.status_service


def get_job_manager(request: Request):
    return request.app.state.container.job_manager


def get_orchestrator(request: Request):
    return request.app.state.container.pipeline_orchestrator


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    modality: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_service=Depends(get_status_service)
):
    """List jobs with filtering and pagination."""
    items, total = await status_service.list_jobs(status, modality, limit, offset)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/dead-letter")
async def get_dead_letter_jobs(
    limit: int = Query(50, ge=1, le=100),
    job_manager=Depends(get_job_manager)
):
    """Get jobs that have exhausted all retries."""
    jobs = await job_manager.get_dead_letter_jobs(limit)
    return jobs


@router.get("/{job_id}")
async def get_job(job_id: str, status_service=Depends(get_status_service)):
    """Get detailed job status."""
    job = await status_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str, 
    request: Request,
    background_tasks: BackgroundTasks,
    job_manager=Depends(get_job_manager),
    orchestrator=Depends(get_orchestrator)
):
    """Retry a failed job."""
    try:
        job = await job_manager.retry_job(job_id)
        
        async def run_job(j=job):
            try:
                await orchestrator.execute_job(j)
            finally:
                try:
                    await request.app.state.container._shared_session.remove()
                except Exception:
                    pass
                    
        background_tasks.add_task(run_job)
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, job_manager=Depends(get_job_manager)):
    """Cancel a pending or processing job."""
    try:
        await job_manager.cancel_job(job_id)
        return {"status": "cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
