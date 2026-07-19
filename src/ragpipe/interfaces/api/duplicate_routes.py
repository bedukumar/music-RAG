from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List
from ragpipe.application.services.duplicate_detector import DuplicateDetector

router = APIRouter(prefix="/duplicates", tags=["duplicates"])

def get_duplicate_detector(request: Request) -> DuplicateDetector:
    return request.app.state.container.duplicate_detector

class MergeDuplicatesRequest(BaseModel):
    target_id: str
    duplicate_ids: List[str]

@router.post("/scan")
async def scan_duplicates(
    detector: DuplicateDetector = Depends(get_duplicate_detector)
):
    """Run hashing & vector similarity scan across the catalog."""
    return await detector.scan_duplicates()

@router.get("")
async def get_duplicates(
    detector: DuplicateDetector = Depends(get_duplicate_detector)
):
    """Return grouped list of duplicates."""
    return {"groups": await detector.get_duplicates()}

@router.delete("/merge")
async def merge_duplicates(
    req: MergeDuplicatesRequest,
    detector: DuplicateDetector = Depends(get_duplicate_detector)
):
    """Consolidate metadata & embeddings into a single media item."""
    try:
        result = await detector.merge_duplicates(req.target_id, req.duplicate_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
