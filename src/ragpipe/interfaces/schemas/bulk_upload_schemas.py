"""Pydantic schemas for the bulk upload API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BulkUploadResponse(BaseModel):
    """Response body for a bulk upload resource."""

    bulk_upload_id: str = Field(..., description="Unique bulk upload identifier")
    status: str = Field(..., description="Current processing status")
    original_filename: str
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class BulkUploadCreateResponse(BaseModel):
    """Response body returned immediately after a bulk upload is submitted (HTTP 202)."""

    bulk_upload_id: str = Field(..., description="Unique bulk upload identifier")
    status: str = Field(default="PENDING")


class BulkUploadListResponse(BaseModel):
    """Paginated list of bulk uploads."""

    items: list[BulkUploadResponse]
    total: int
    offset: int
    limit: int


class BulkUploadRowResponse(BaseModel):
    """Response for a single row within a bulk upload."""

    row_number: int
    status: str
    media_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class BulkUploadRowListResponse(BaseModel):
    """Paginated list of bulk upload row results."""

    items: list[BulkUploadRowResponse]
    total: int
    offset: int
    limit: int
