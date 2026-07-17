"""
Main API Router.
"""

from fastapi import APIRouter

from ragpipe.interfaces.api.health_routes import router as health_router
from ragpipe.interfaces.api.job_routes import router as job_router
from ragpipe.interfaces.api.media_routes import router as media_router
from ragpipe.interfaces.api.migration_routes import router as migration_router
from ragpipe.interfaces.api.pipeline_routes import router as pipeline_router
from ragpipe.interfaces.api.websocket_routes import router as websocket_router

# API v1 Router
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(media_router)
api_router.include_router(pipeline_router)
api_router.include_router(job_router)
api_router.include_router(migration_router)
api_router.include_router(health_router)

# Main router for app inclusion (includes websocket at root level)
main_router = APIRouter()
main_router.include_router(api_router)
main_router.include_router(websocket_router)
