from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
from ragpipe.domain.models.modality import Modality
from ragpipe.application.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

def get_search_service(request: Request) -> SearchService:
    return request.app.state.container.search_service

class SearchValidateRequest(BaseModel):
    query: str
    modality: str
    ground_truth_ids: List[str] = []

class SearchTuningRequest(BaseModel):
    top_k: Optional[int] = None
    distance_metric: Optional[str] = None
    threshold: Optional[float] = None

@router.post("/validate")
async def validate_search(
    req: SearchValidateRequest,
    search_service: SearchService = Depends(get_search_service)
):
    """Validate search query against ground truth IDs."""
    try:
        mod = Modality(req.modality)
        result = await search_service.validate_search(req.query, mod, req.ground_truth_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history")
async def get_search_history(
    search_service: SearchService = Depends(get_search_service)
):
    """Get search validation history logs."""
    history = await search_service.get_history()
    return {"history": history, "count": len(history)}

@router.post("/tuning")
async def tune_search(
    req: SearchTuningRequest,
    search_service: SearchService = Depends(get_search_service)
):
    """Adjust search hyperparameters on the fly."""
    params = req.model_dump(exclude_none=True)
    new_params = await search_service.tune_hyperparameters(params)
    return {"status": "tuned", "hyperparameters": new_params}
