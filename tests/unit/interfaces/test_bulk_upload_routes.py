"""Unit tests for bulk upload API routes."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadStatus
from ragpipe.interfaces.api.bulk_upload_routes import router


# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------


def _make_test_app(bulk_upload_service=None) -> FastAPI:
    """Create a minimal FastAPI app with the bulk upload router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    container_mock = MagicMock()
    container_mock.bulk_upload_service = bulk_upload_service
    app.state.container = container_mock
    return app


def _make_bulk_upload(
    bu_id: str = "bu-test-id",
    status: BulkUploadStatus = BulkUploadStatus.PENDING,
) -> BulkUpload:
    bu = BulkUpload.create("key", "bucket", "songs.csv")
    bu.id = bu_id
    bu.status = status
    return bu


# ---------------------------------------------------------------------------
# POST /api/v1/bulk-uploads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_bulk_upload_returns_202():
    """Successful upload should return HTTP 202 with bulk_upload_id."""
    svc = AsyncMock()
    svc.create_bulk_upload.return_value = _make_bulk_upload()

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("songs.csv", BytesIO(b"title,media_type\nSong1,song"), "text/csv")},
        )

    assert response.status_code == 202
    data = response.json()
    assert "bulk_upload_id" in data
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_post_bulk_upload_empty_file_returns_400():
    """Empty file bytes should return HTTP 400."""
    svc = AsyncMock()
    app = _make_test_app(bulk_upload_service=svc)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_bulk_upload_invalid_type_returns_400():
    """Service ValueError should produce HTTP 400."""
    svc = AsyncMock()
    svc.create_bulk_upload.side_effect = ValueError("Unsupported file type")

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("doc.pdf", BytesIO(b"binary"), "application/pdf")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_bulk_upload_no_service_returns_503():
    """Missing service (not configured) should return HTTP 503."""
    app = _make_test_app(bulk_upload_service=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("songs.csv", BytesIO(b"title\nSong1"), "text/csv")},
        )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/v1/bulk-uploads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bulk_uploads_list():
    """GET list should return paginated results."""
    svc = AsyncMock()
    svc.list_bulk_uploads.return_value = ([_make_bulk_upload()], 1)

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


# ---------------------------------------------------------------------------
# GET /api/v1/bulk-uploads/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bulk_upload_detail():
    """GET detail should return the bulk upload."""
    svc = AsyncMock()
    svc.get_bulk_upload.return_value = _make_bulk_upload("bu-xyz")

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads/bu-xyz")

    assert response.status_code == 200
    assert response.json()["bulk_upload_id"] == "bu-xyz"


@pytest.mark.asyncio
async def test_get_bulk_upload_detail_not_found():
    """GET on a non-existent ID should return 404."""
    svc = AsyncMock()
    svc.get_bulk_upload.return_value = None

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads/does-not-exist")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/bulk-uploads/{id}/cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_returns_cancelled_status():
    """Cancel endpoint should return the updated status."""
    svc = AsyncMock()
    bu = _make_bulk_upload(status=BulkUploadStatus.CANCELLED)
    svc.cancel_bulk_upload.return_value = bu

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/bulk-uploads/bu-test-id/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_terminal_state_returns_409():
    """Cancelling a terminal upload should return 409 Conflict."""
    svc = AsyncMock()
    svc.cancel_bulk_upload.side_effect = ValueError("Cannot cancel bulk upload in terminal state")

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/bulk-uploads/bu-done/cancel")

    assert response.status_code == 409

@pytest.mark.asyncio
async def test_post_bulk_upload_oversized_payload_returns_413(monkeypatch):
    """File exceeding MAX_FILE_SIZE_BYTES should return HTTP 413."""
    import ragpipe.interfaces.api.bulk_upload_routes as routes
    monkeypatch.setattr(routes, "MAX_FILE_SIZE_BYTES", 10)
    
    svc = AsyncMock()
    app = _make_test_app(bulk_upload_service=svc)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("songs.csv", BytesIO(b"this is more than 10 bytes"), "text/csv")},
        )

    assert response.status_code == 413

@pytest.mark.asyncio
async def test_post_bulk_upload_service_error_returns_500():
    """Service generic Exception should produce HTTP 500."""
    svc = AsyncMock()
    svc.create_bulk_upload.side_effect = Exception("Unknown failure")

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/bulk-uploads",
            files={"file": ("doc.csv", BytesIO(b"a,b"), "text/csv")},
        )

    assert response.status_code == 500

@pytest.mark.asyncio
async def test_get_bulk_uploads_pagination():
    """GET list should pass pagination parameters."""
    svc = AsyncMock()
    svc.list_bulk_uploads.return_value = ([], 0)

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads?limit=10&offset=5&status=PENDING")

    assert response.status_code == 200
    svc.list_bulk_uploads.assert_called_once_with(status="PENDING", limit=10, offset=5)

@pytest.mark.asyncio
async def test_get_bulk_upload_rows():
    """GET rows should return the row list."""
    from ragpipe.domain.models.bulk_upload import BulkUploadRow, BulkUploadRowStatus
    
    row = BulkUploadRow.create(bulk_upload_id="bu-xyz", row_number=1, raw_data={})
    row.status = BulkUploadRowStatus.PROCESSED
    row.media_id = "media-1"
    
    svc = AsyncMock()
    svc.get_bulk_upload.return_value = _make_bulk_upload("bu-xyz")
    svc.list_bulk_upload_rows.return_value = ([row], 1)

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads/bu-xyz/rows?limit=20&offset=0&status=processed")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["row_number"] == 1
    assert data["items"][0]["status"] == "processed"
    assert data["items"][0]["media_id"] == "media-1"
    svc.list_bulk_upload_rows.assert_called_once_with(bulk_upload_id="bu-xyz", status="processed", limit=20, offset=0)

@pytest.mark.asyncio
async def test_get_bulk_upload_rows_not_found():
    """GET rows on a non-existent ID should return 404."""
    svc = AsyncMock()
    svc.get_bulk_upload.return_value = None

    app = _make_test_app(bulk_upload_service=svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/bulk-uploads/does-not-exist/rows")

    assert response.status_code == 404
