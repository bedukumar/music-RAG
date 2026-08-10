"""Bulk Upload API Routes.

Endpoints:

    POST   /api/v1/bulk-uploads                       — Submit a file for bulk processing
    GET    /api/v1/bulk-uploads                       — List bulk uploads
    GET    /api/v1/bulk-uploads/{bulk_upload_id}      — Get a specific bulk upload
    GET    /api/v1/bulk-uploads/{bulk_upload_id}/rows — List row-level results
    POST   /api/v1/bulk-uploads/{bulk_upload_id}/cancel — Cancel a bulk upload

All endpoints return 503 if S3/SQS is not configured in the environment so that
the API does not break when running without bulk upload infrastructure.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from ragpipe.interfaces.schemas.bulk_upload_schemas import (
    BulkUploadCreateResponse,
    BulkUploadListResponse,
    BulkUploadResponse,
    BulkUploadRowListResponse,
    BulkUploadRowResponse,
)

router = APIRouter(prefix="/bulk-uploads", tags=["bulk-uploads"])

# Maximum file size: 100 MB (raw bytes limit before streaming)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


def _get_service(request: Request):
    """Resolve BulkUploadService from the DI container."""
    return request.app.state.container.bulk_upload_service


def _bulk_upload_to_response(bu) -> BulkUploadResponse:
    """Map a BulkUpload domain object to the API response schema."""
    return BulkUploadResponse(
        bulk_upload_id=bu.id,
        status=bu.status.value,
        original_filename=bu.original_filename,
        total_rows=bu.total_rows,
        processed_rows=bu.processed_rows,
        successful_rows=bu.successful_rows,
        failed_rows=bu.failed_rows,
        created_at=bu.created_at,
        started_at=bu.started_at,
        completed_at=bu.completed_at,
        error_message=bu.error_message,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/bulk-uploads
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=202,
    response_model=BulkUploadCreateResponse,
    summary="Submit a CSV/XLSX file for bulk media ingestion",
    description=(
        "Uploads the file to S3, creates a BulkUpload record in PENDING status, "
        "publishes an SQS message, and returns 202 Accepted immediately. "
        "The actual CSV/XLSX parsing and media registration happen asynchronously "
        "in the bulk upload worker process."
    ),
)
async def create_bulk_upload(
    file: UploadFile = File(
        ...,
        description="CSV or XLSX file. Required columns: title, media_type. "
        "Optional: artist, album, genre, language, tags (comma-separated), duration, "
        "source_url, audio_path, transcript_text, lyrics, bpm, musical_key (song); "
        "show_name, episode_number, host, guests (podcast); "
        "resolution, fps, video_path (video). "
        "Additional columns become metadata_fields.",
    ),
    service=Depends(_get_service),
):
    """Submit a file for bulk asynchronous media ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content_type = file.content_type or "application/octet-stream"

    # Read with size guard
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {len(file_bytes)} bytes. "
                f"Maximum is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            ),
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        bulk_upload = await service.create_bulk_upload(
            file_bytes=file_bytes,
            original_filename=file.filename,
            content_type=content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create bulk upload: {exc}")

    return BulkUploadCreateResponse(
        bulk_upload_id=bulk_upload.id,
        status=bulk_upload.status.value,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bulk-uploads
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=BulkUploadListResponse,
    summary="List bulk uploads",
)
async def list_bulk_uploads(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: PENDING, PROCESSING, COMPLETED, "
        "COMPLETED_WITH_ERRORS, FAILED, CANCELLED",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service=Depends(_get_service),
):
    """List all bulk uploads with optional status filter and pagination."""
    items, total = await service.list_bulk_uploads(
        status=status, limit=limit, offset=offset
    )
    return BulkUploadListResponse(
        items=[_bulk_upload_to_response(bu) for bu in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bulk-uploads/{bulk_upload_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{bulk_upload_id}",
    response_model=BulkUploadResponse,
    summary="Get a specific bulk upload",
)
async def get_bulk_upload(
    bulk_upload_id: str,
    service=Depends(_get_service),
):
    """Retrieve a bulk upload by its ID including row-level counters."""
    bulk_upload = await service.get_bulk_upload(bulk_upload_id)
    if not bulk_upload:
        raise HTTPException(status_code=404, detail="Bulk upload not found")
    return _bulk_upload_to_response(bulk_upload)


# ---------------------------------------------------------------------------
# GET /api/v1/bulk-uploads/{bulk_upload_id}/rows
# ---------------------------------------------------------------------------


@router.get(
    "/{bulk_upload_id}/rows",
    response_model=BulkUploadRowListResponse,
    summary="List row-level results for a bulk upload",
)
async def list_bulk_upload_rows(
    bulk_upload_id: str,
    status: Optional[str] = Query(
        default=None,
        description="Filter rows by status: pending, processed, failed, skipped",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service=Depends(_get_service),
):
    """Return per-row processing outcomes for a specific bulk upload."""
    # Verify the parent exists
    bulk_upload = await service.get_bulk_upload(bulk_upload_id)
    if not bulk_upload:
        raise HTTPException(status_code=404, detail="Bulk upload not found")

    rows, total = await service.list_bulk_upload_rows(
        bulk_upload_id=bulk_upload_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return BulkUploadRowListResponse(
        items=[
            BulkUploadRowResponse(
                row_number=r.row_number,
                status=r.status.value,
                media_id=r.media_id,
                error_type=r.error_type,
                error_message=r.error_message,
            )
            for r in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/bulk-uploads/{bulk_upload_id}/cancel
# ---------------------------------------------------------------------------


@router.post(
    "/{bulk_upload_id}/cancel",
    response_model=BulkUploadResponse,
    summary="Cancel a bulk upload",
)
async def cancel_bulk_upload(
    bulk_upload_id: str,
    service=Depends(_get_service),
):
    """Cancel a PENDING or PROCESSING bulk upload.

    Note: Cancellation marks the record as CANCELLED but does not guarantee
    that the worker will stop immediately — it will finish the current row
    and check the status before continuing.
    """
    try:
        bulk_upload = await service.cancel_bulk_upload(bulk_upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _bulk_upload_to_response(bulk_upload)
