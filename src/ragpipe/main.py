"""
FastAPI Application Entry Point.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from starlette.requests import HTTPConnection

from ragpipe.container import Container
from ragpipe.interfaces.api.router import main_router

async def db_session_cleanup(conn: HTTPConnection):
    try:
        yield
    finally:
        if hasattr(conn.app.state, "container"):
            try:
                await conn.app.state.container._shared_session.remove()
            except Exception:
                pass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting RagPipe Application...")
    
    # Initialize DI Container
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///ragpipe.db")
    storage_path = os.getenv("STORAGE_PATH", "./data")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    
    container = Container(db_url=db_url, storage_path=storage_path, qdrant_url=qdrant_url)
    await container.init_resources()
    
    # Attach container to app state for use in routes
    app.state.container = container
    app.state.db_engine = container.engine
    
    # Wire up WebSocket broadcast to Domain Events
    from ragpipe.interfaces.api.websocket_routes import manager as ws_manager
    container.event_bus.set_broadcast_callback(ws_manager.handle_domain_event)
    
    # Run recovery asynchronously in background
    import asyncio
    asyncio.create_task(container.recovery_manager.run_recovery())
    
    logger.info("RagPipe Application started successfully.")
    yield
    
    # Shutdown
    logger.info("Shutting down RagPipe Application...")
    await container.close_resources()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RagPipe API",
        description="Audio RAG Data Ingestion Platform",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(db_session_cleanup)],
    )
    
    # Include main API router
    app.include_router(main_router)
    
    # Removed HTTP middleware since session cleanup is now handled by the global dependency
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ragpipe.main:app", host="0.0.0.0", port=8000, reload=True)
