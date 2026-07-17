"""
Migration API Routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.exceptions import MigrationError
from ragpipe.interfaces.schemas.migration_schemas import (
    EmbeddingVersionCreateRequest,
    EmbeddingVersionResponse,
    MigrationResponse,
    MigrationStartRequest,
)

router = APIRouter(prefix="", tags=["migrations"])


def get_embedding_manager(request: Request):
    return request.app.state.container.embedding_manager


def get_migration_manager(request: Request):
    return request.app.state.container.migration_manager


@router.post("/embedding-versions", response_model=EmbeddingVersionResponse)
async def create_embedding_version(
    req: EmbeddingVersionCreateRequest,
    manager=Depends(get_embedding_manager)
):
    """Create a new embedding version."""
    try:
        modality = Modality(req.modality)
        version = await manager.create_embedding_version(
            modality=modality,
            model_name=req.model_name,
            model_version=req.model_version,
            dimension=req.dimension,
            chunking_strategy=req.chunking_strategy,
            chunking_version=req.chunking_version,
            pipeline_version=req.pipeline_version,
            activate=req.activate,
        )
        return version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/embedding-versions", response_model=list[EmbeddingVersionResponse])
async def list_embedding_versions(
    modality: Optional[str] = None,
    manager=Depends(get_embedding_manager)
):
    """List embedding versions."""
    try:
        mod = Modality(modality) if modality else None
        return await manager.list_versions(mod)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/embedding-versions/{version_id}", response_model=EmbeddingVersionResponse)
async def get_embedding_version(version_id: str, manager=Depends(get_embedding_manager)):
    """Get a specific embedding version."""
    version = await manager.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/embedding-versions/{version_id}/activate")
async def activate_version(version_id: str, manager=Depends(get_embedding_manager)):
    """Activate an embedding version."""
    try:
        await manager.activate_version(version_id)
        return {"status": "activated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/migrations", response_model=MigrationResponse)
async def start_migration(
    req: MigrationStartRequest,
    manager=Depends(get_migration_manager)
):
    """Start a backfill migration to a new embedding version."""
    try:
        modality = Modality(req.modality)
        migration = await manager.start_backfill(modality, req.to_version_id)
        return migration
    except (ValueError, MigrationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/migrations", response_model=list[MigrationResponse])
async def list_migrations(
    modality: Optional[str] = None,
    manager=Depends(get_migration_manager)
):
    """List all migrations."""
    mod = Modality(modality) if modality else None
    return await manager.list_migrations(mod)


@router.get("/migrations/{migration_id}", response_model=MigrationResponse)
async def get_migration_status(migration_id: str, manager=Depends(get_migration_manager)):
    """Get migration status."""
    migration = await manager.get_migration_status(migration_id)
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")
    return migration


@router.post("/migrations/{migration_id}/switch")
async def switch_index(migration_id: str, manager=Depends(get_migration_manager)):
    """Switch read alias to the new migrated collection."""
    try:
        await manager.switch_index(migration_id)
        return {"status": "switched"}
    except MigrationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/migrations/{migration_id}/rollback")
async def rollback_migration(migration_id: str, manager=Depends(get_migration_manager)):
    """Rollback a migration."""
    try:
        await manager.rollback(migration_id)
        return {"status": "rolled_back"}
    except MigrationError as e:
        raise HTTPException(status_code=400, detail=str(e))
