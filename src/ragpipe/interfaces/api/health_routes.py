"""
Health API Routes.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    """Liveness probe. Always returns 200 if the app is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request):
    """Readiness probe. Checks if the database is accessible."""
    try:
        # Check DB connection
        engine = request.app.state.db_engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")


@router.get("/startup")
async def startup_probe():
    """Startup probe. Used by k8s to know when to start checking readiness."""
    return {"status": "started"}
