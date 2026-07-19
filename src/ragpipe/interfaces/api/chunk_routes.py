from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from ragpipe.domain.models.modality import Modality

router = APIRouter(prefix="/media", tags=["chunks"])

def get_chunk_manager(request: Request):
    return request.app.state.container.chunk_manager

@router.get("/{media_id}/chunks")
async def list_chunks(
    media_id: str,
    modality: Optional[str] = None,
    chunk_manager=Depends(get_chunk_manager)
):
    """Get all chunks for a media item."""
    mod = Modality(modality) if modality else None
    chunks = await chunk_manager.get_chunks(media_id, mod)
    return {"chunks": chunks, "count": len(chunks)}

@router.delete("/{media_id}/chunks")
async def delete_chunks(
    media_id: str,
    modality: Optional[str] = None,
    chunk_manager=Depends(get_chunk_manager)
):
    """Delete chunks for a media item."""
    mod = Modality(modality) if modality else None
    await chunk_manager.delete_chunks(media_id, mod)
    return {"status": "deleted"}

@router.post("/{media_id}/chunks/rebuild")
async def rebuild_chunks(
    media_id: str,
    modality: str,
    regenerate_embeddings: bool = False,
    chunk_manager=Depends(get_chunk_manager)
):
    """Rebuild chunks without regenerating embeddings unless requested."""
    try:
        mod = Modality(modality)
        await chunk_manager.rebuild_chunks(media_id, mod, regenerate_embeddings)
        return {"status": "rebuilt"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{media_id}/chunks/{chunk_id}")
async def get_chunk(
    media_id: str,
    chunk_id: str,
    chunk_manager=Depends(get_chunk_manager)
):
    """Get a specific chunk."""
    try:
        mod_val, idx_str = chunk_id.split("-", 1)
        mod = Modality(mod_val)
        idx = int(idx_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chunk_id format")
        
    chunks = await chunk_manager.get_chunks(media_id, mod)
    for c in chunks:
        if c["chunk_index"] == idx:
            return c
    raise HTTPException(status_code=404, detail="Chunk not found")
