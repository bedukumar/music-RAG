from fastapi import APIRouter, Depends, HTTPException, Request
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.exceptions import VectorStoreError

router = APIRouter(prefix="/collections", tags=["collections"])

def get_vector_repo(request: Request) -> VectorRepository:
    # Assuming vector_repo exists on container
    # Since Qdrant is the default, we use it directly or via a service
    # We will just fetch it from container (it exists as 'audio_embedder' but we need the actual vector repo)
    # Actually, in container.py, we have `self.vector_repository` created in init_resources
    return request.app.state.container.vector_repository

@router.get("")
async def list_collections(
    vector_repo: VectorRepository = Depends(get_vector_repo)
):
    """List all vector collections and their stats."""
    try:
        collections = await vector_repo.list_collections()
        result = []
        for c in collections:
            try:
                info = await vector_repo.get_collection_info(c)
                info["name"] = c
                result.append(info)
            except VectorStoreError:
                result.append({"name": c, "status": "error_fetching_info"})
        return {"collections": result}
    except VectorStoreError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{name}/optimize")
async def optimize_collection(
    name: str,
    vector_repo: VectorRepository = Depends(get_vector_repo)
):
    """Trigger index optimization on a collection."""
    try:
        await vector_repo.optimize_collection(name)
        return {"status": "optimizing"}
    except VectorStoreError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{name}")
async def drop_collection(
    name: str,
    force: bool = False,
    vector_repo: VectorRepository = Depends(get_vector_repo)
):
    """Drop a collection."""
    if not force:
        raise HTTPException(status_code=400, detail="Must provide force=true to drop a collection.")
    try:
        await vector_repo.delete_collection(name)
        return {"status": "deleted"}
    except VectorStoreError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/health")
async def check_collection_health(
    name: str,
    vector_repo: VectorRepository = Depends(get_vector_repo)
):
    """Check collection health."""
    try:
        exists = await vector_repo.collection_exists(name)
        if not exists:
            return {"status": "missing"}
        info = await vector_repo.get_collection_info(name)
        status = info.get("status", "unknown")
        return {"status": status, "info": info}
    except VectorStoreError as e:
        raise HTTPException(status_code=500, detail=str(e))
