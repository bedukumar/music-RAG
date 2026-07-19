from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from typing import Optional
from ragpipe.domain.models.modality import Modality
from ragpipe.application.services.embedding_manager import EmbeddingManager

router = APIRouter(tags=["embeddings"])
media_router = APIRouter(prefix="/media", tags=["embeddings"])

def get_embedding_manager(request: Request) -> EmbeddingManager:
    return request.app.state.container.embedding_manager

def get_orchestrator(request: Request):
    return request.app.state.container.pipeline_orchestrator

def get_chunk_manager(request: Request):
    return request.app.state.container.chunk_manager

@media_router.get("/{media_id}/embeddings")
async def get_embeddings(
    media_id: str,
    modality: Optional[str] = None,
    include_vectors: bool = False,
    embedding_manager: EmbeddingManager = Depends(get_embedding_manager)
):
    """Get embeddings info for a media item."""
    mod = Modality(modality) if modality else None
    embeddings = await embedding_manager.get_media_embeddings(media_id, mod, include_vectors)
    return {"embeddings": embeddings, "count": len(embeddings)}

@media_router.post("/{media_id}/embeddings/rebuild")
async def rebuild_embeddings(
    media_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    modality: Optional[str] = None,
    force: bool = False,
    outdated_only: bool = False,
    orchestrator=Depends(get_orchestrator)
):
    """Rebuild embeddings for a media item."""
    if not modality:
        raise HTTPException(status_code=400, detail="Modality is required to rebuild embeddings")
    try:
        mod = Modality(modality)
        job = await orchestrator.reprocess_modality(media_id, mod)
        
        async def run_job(j=job):
            try:
                await orchestrator.execute_job(j)
            finally:
                try:
                    await request.app.state.container._shared_session.remove()
                except Exception:
                    pass
                    
        background_tasks.add_task(run_job)
        return {"status": "rebuilding", "job_id": job.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@media_router.delete("/{media_id}/embeddings")
async def delete_embeddings(
    media_id: str,
    modality: Optional[str] = None,
    chunk_manager=Depends(get_chunk_manager)
):
    """Delete embeddings (and chunks) for a media item."""
    mod = Modality(modality) if modality else None
    await chunk_manager.delete_chunks(media_id, mod)
    return {"status": "deleted"}

@router.get("/embedding-models")
async def list_embedding_models(
    embedding_manager: EmbeddingManager = Depends(get_embedding_manager)
):
    """Return installed embedding models."""
    models = await embedding_manager.list_installed_models()
    return {"models": models}

# Combine them in a master router
master_router = APIRouter()
master_router.include_router(media_router)
master_router.include_router(router)
