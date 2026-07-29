from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from ragpipe.domain.models.modality import Modality

# Existing old search service for validation/tuning
from ragpipe.application.services.search_service import SearchService as OldSearchService
# New Retrieval Pipeline search service
from ragpipe.application.retrieval.services.search_service import SearchService as RetrievalSearchService
from ragpipe.domain.retrieval.models import SearchFilters, SearchQuery


router = APIRouter(prefix="/search", tags=["search"])


def get_old_search_service(request: Request) -> OldSearchService:
    return request.app.state.container.search_service

def get_retrieval_search_service(request: Request) -> RetrievalSearchService:
    if not hasattr(request.app.state.container, "retrieval_search_service") or request.app.state.container.retrieval_search_service is None:
        raise HTTPException(status_code=500, detail="Retrieval search service not initialized")
    return request.app.state.container.retrieval_search_service


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
    search_service: OldSearchService = Depends(get_old_search_service)
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
    search_service: RetrievalSearchService = Depends(get_retrieval_search_service)
):
    """Get search validation history logs."""
    history = await search_service.get_history()
    return {"history": history, "count": len(history)}

@router.get("/analytics")
async def get_search_analytics(
    search_service: RetrievalSearchService = Depends(get_retrieval_search_service)
):
    """Get search analytics."""
    analytics = await search_service.get_analytics()
    return analytics

@router.post("/tuning")
async def tune_search(
    req: SearchTuningRequest,
    search_service: OldSearchService = Depends(get_old_search_service)
):
    """Adjust search hyperparameters on the fly."""
    params = req.model_dump(exclude_none=True)
    new_params = await search_service.tune_hyperparameters(params)
    return {"status": "tuned", "hyperparameters": new_params}


class SearchRequest(BaseModel):
    query: str
    modalities: List[str] = Field(default=["audio", "transcript", "metadata"])
    filters: Dict[str, Any] = Field(default_factory=dict) # exact matches
    tag_matches: List[str] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=100)
    rerank: bool = False
    fusion_strategy: str = "rrf"


@router.post("")
async def search(
    request: SearchRequest,
    service: RetrievalSearchService = Depends(get_retrieval_search_service)
):
    """Execute a multi-modal search via the Retrieval Pipeline."""
    active_modalities = []
    for m in request.modalities:
        try:
            active_modalities.append(Modality(m))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid modality: {m}")

    query = SearchQuery(
        text=request.query,
        active_modalities=active_modalities,
        filters=SearchFilters(
            exact_matches=request.filters,
            tag_matches=request.tag_matches
        ),
        top_k=request.top_k,
        rerank=request.rerank,
        fusion_strategy=request.fusion_strategy
    )

    try:
        session = await service.search(query)
        
        results = []
        for r in session.results:
            results.append({
                "media_id": r.media.media_id,
                "title": r.media.title,
                "media_type": r.media.media_type,
                "metadata": r.media.metadata,
                "overall_score": r.overall_score,
                "matched_chunks": [
                    {
                        "chunk_id": c.chunk_id,
                        "modality": c.modality.value,
                        "score": c.score,
                        "content": c.content,
                        "timestamps": c.timestamps
                    } for c in r.matched_chunks
                ]
            })
            
        return {
            "session_id": session.session_id,
            "latency_ms": session.latency_ms,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
