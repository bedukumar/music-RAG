"""
Pipeline API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ragpipe.interfaces.schemas.pipeline_schemas import PipelineStatusResponse

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def get_status_service(request: Request):
    return request.app.state.container.status_service


@router.get("/status/{media_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(media_id: str, status_service=Depends(get_status_service)):
    """Get complete pipeline status for a media item."""
    status = await status_service.get_pipeline_status(media_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return status


@router.get("/stats")
async def get_system_stats(status_service=Depends(get_status_service)):
    """Get system-wide pipeline statistics."""
    return await status_service.get_system_stats()
