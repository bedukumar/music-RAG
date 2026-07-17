"""
Pipeline Schemas.

Pydantic models for pipeline state and jobs.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from ragpipe.interfaces.schemas.media_schemas import ModalityStatusResponse


class StageResultResponse(BaseModel):
    """Schema for a pipeline stage result."""
    stage: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    metrics: dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)


class PipelineStateResponse(BaseModel):
    """Schema for pipeline state."""
    id: str
    media_id: str
    modality: str
    job_id: str
    stages: list[StageResultResponse]
    current_stage: Optional[str] = None
    overall_status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    """Schema for job details."""
    id: str
    media_id: str
    modality: str
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    pipeline_state_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PipelineStatusResponse(BaseModel):
    """Comprehensive status for a media item's pipelines."""
    media_id: str
    title: str
    media_type: str
    modality_statuses: list[ModalityStatusResponse]
    pipelines: dict[str, dict[str, Any]]
    
    model_config = ConfigDict(from_attributes=True)


class ProcessRequest(BaseModel):
    """Request to process media."""
    modalities: Optional[list[str]] = None


class ReprocessRequest(BaseModel):
    """Request to reprocess a modality."""
    modality: str
