import pytest
from ragpipe.workers.bulk_upload_worker import BulkUploadWorker
from unittest.mock import AsyncMock

@pytest.fixture
def worker():
    return BulkUploadWorker(
        queue=AsyncMock(),
        object_storage=AsyncMock(),
        bulk_upload_repository=AsyncMock(),
        media_registrar=AsyncMock(),
        pipeline_orchestrator=AsyncMock(),
        event_bus=AsyncMock(),
        metrics=AsyncMock(),
    )

def test_missing_title(worker):
    row = {"media_type": "song"}
    with pytest.raises(ValueError, match="Missing required field: 'title'"):
        worker._build_media_item(row)

def test_invalid_media_type(worker):
    row = {"title": "A", "media_type": "unknown", "source_url": "http://example.com"}
    with pytest.raises(ValueError, match="Invalid media_type"):
        worker._build_media_item(row)

def test_empty_values(worker):
    row = {"title": " ", "media_type": "song", "source_url": ""}
    with pytest.raises(ValueError, match="Missing required field: 'title'"):
        worker._build_media_item(row)

def test_missing_source_url_and_audio_path(worker):
    row = {"title": "A", "media_type": "song"}
    with pytest.raises(ValueError, match="Missing required field: 'source_url' or 'audio_path'"):
        worker._build_media_item(row)

def test_malformed_metadata(worker):
    # Tests that unknown columns are merged into metadata_fields
    row = {"title": "A", "media_type": "song", "source_url": "http://a", "unknown_col": "val"}
    item = worker._build_media_item(row)
    assert item.metadata_fields["unknown_col"] == "val"

def test_unicode_csv(worker):
    csv_bytes = "title,media_type,source_url\nCéline,song,http://a\n".encode("utf-8")
    rows = list(worker._parse_csv(csv_bytes))
    assert rows[0]["title"] == "Céline"

def test_commas_in_csv(worker):
    csv_bytes = 'title,media_type,source_url\n"Title, with comma",song,http://a\n'.encode("utf-8")
    rows = list(worker._parse_csv(csv_bytes))
    assert rows[0]["title"] == "Title, with comma"

def test_header_only(worker):
    csv_bytes = b"title,media_type,source_url\n"
    rows = list(worker._parse_csv(csv_bytes))
    assert len(rows) == 0

def test_malformed_csv(worker):
    # Standard csv reader is quite permissive, but let's test a simple case
    csv_bytes = b"title,media_type\nA\nB,song,extra\n"
    rows = list(worker._parse_csv(csv_bytes))
    assert len(rows) == 2
    assert rows[0]["title"] == "A"
    assert rows[0]["media_type"] is None
    assert rows[1]["title"] == "B"

def test_duplicate_rows(worker):
    csv_bytes = b"title,media_type,source_url\nA,song,http://a\nA,song,http://a\n"
    rows = list(worker._parse_csv(csv_bytes))
    assert len(rows) == 2

