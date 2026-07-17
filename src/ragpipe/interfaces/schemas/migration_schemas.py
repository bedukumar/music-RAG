"""
Migration Schemas.

Pydantic models for migrations and embedding versions.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmbeddingVersionCreateRequest(BaseModel):
    """Request to create an embedding version."""
    modality: str
    model_name: str
    model_version: str
    dimension: int
    chunking_strategy: str
    chunking_version: str
    pipeline_version: str
    activate: bool = False


class EmbeddingVersionResponse(BaseModel):
    """Response for an embedding version."""
    id: str
    modality: str
    model_name: str
    model_version: str
    dimension: int
    chunking_strategy: str
    chunking_version: str
    pipeline_version: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MigrationStartRequest(BaseModel):
    """Request to start a migration."""
    modality: str
    to_version_id: str


class MigrationResponse(BaseModel):
    """Response for a migration."""
    id: str
    modality: str
    from_version_id: Optional[str] = None
    to_version_id: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def progress(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.processed_items + self.failed_items) / self.total_items

    model_config = ConfigDict(from_attributes=True)
