from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from ragpipe.application.services.system_manager import SystemManager

router = APIRouter(prefix="/system", tags=["system"])

def get_system_manager(request: Request) -> SystemManager:
    return request.app.state.container.system_manager

@router.get("/metrics")
async def get_system_metrics(
    system_manager: SystemManager = Depends(get_system_manager)
):
    """Expose internal system metrics."""
    return system_manager.get_metrics()

@router.get("/events")
async def get_system_events(
    limit: Optional[int] = 100,
    system_manager: SystemManager = Depends(get_system_manager)
):
    """Webhook log of recent important events."""
    events = system_manager.get_events(limit)
    return {"events": events, "count": len(events)}
