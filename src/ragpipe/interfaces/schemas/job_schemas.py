"""
Job Schemas.

Pydantic models for jobs.
"""

from typing import Any

from pydantic import BaseModel

from ragpipe.interfaces.schemas.pipeline_schemas import JobResponse


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    items: list[dict[str, Any]]  # Using dict here since the StatusService returns dicts
    total: int
    offset: int
    limit: int


class SystemStatsResponse(BaseModel):
    """System statistics."""
    total_media: int
    jobs: dict[str, int]
