from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ragpipe.application.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/enrich", tags=["enrichment"])

def get_enrichment_service(request: Request) -> EnrichmentService:
    return request.app.state.container.enrichment_service

class EnrichmentConfig(BaseModel):
    prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None

@router.post("/{media_id}")
async def trigger_enrichment(
    media_id: str,
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """Trigger an LLM job to enrich metadata."""
    try:
        job_id = await enrichment_service.start_enrichment(media_id)
        return {"status": "started", "job_id": job_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/status/{job_id}")
async def get_enrichment_status(
    job_id: str,
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """Poll status for the enrichment job."""
    status = enrichment_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@router.get("/jobs")
async def list_enrichment_jobs(
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """List all enrichment jobs."""
    return {"jobs": enrichment_service.get_all_jobs()}

@router.post("/config")
async def update_enrichment_config(
    config: EnrichmentConfig,
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """Set prompts or max tokens for enrichment."""
    updates = config.model_dump(exclude_none=True)
    new_config = enrichment_service.update_config(updates)
    return {"status": "updated", "config": new_config}
