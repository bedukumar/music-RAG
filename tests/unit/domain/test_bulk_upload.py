import pytest
from datetime import datetime, timezone
from ragpipe.domain.models.bulk_upload import BulkUpload, BulkUploadStatus, BulkUploadRow, BulkUploadRowStatus

def test_bulk_upload_create():
    upload = BulkUpload.create(
        object_key="test-key.csv",
        bucket="test-bucket",
        original_filename="upload.csv"
    )
    assert upload.id is not None
    assert upload.object_key == "test-key.csv"
    assert upload.bucket == "test-bucket"
    assert upload.original_filename == "upload.csv"
    assert upload.status == BulkUploadStatus.PENDING
    assert upload.total_rows == 0
    assert upload.processed_rows == 0
    assert upload.successful_rows == 0
    assert upload.failed_rows == 0
    assert upload.created_at is not None
    assert upload.started_at is None
    assert upload.completed_at is None
    assert upload.error_message is None

def test_bulk_upload_mark_processing():
    upload = BulkUpload.create("k", "b", "f.csv")
    upload.mark_processing()
    assert upload.status == BulkUploadStatus.PROCESSING
    assert upload.started_at is not None

def test_bulk_upload_mark_completed_success():
    upload = BulkUpload.create("k", "b", "f.csv")
    upload.mark_processing()
    upload.total_rows = 2
    upload.increment_success()
    upload.increment_success()
    upload.mark_completed()
    assert upload.status == BulkUploadStatus.COMPLETED
    assert upload.completed_at is not None
    assert upload.processed_rows == 2
    assert upload.successful_rows == 2
    assert upload.failed_rows == 0

def test_bulk_upload_mark_completed_with_errors():
    upload = BulkUpload.create("k", "b", "f.csv")
    upload.mark_processing()
    upload.total_rows = 2
    upload.increment_success()
    upload.increment_failure()
    upload.mark_completed()
    assert upload.status == BulkUploadStatus.COMPLETED_WITH_ERRORS
    assert upload.completed_at is not None
    assert upload.processed_rows == 2
    assert upload.successful_rows == 1
    assert upload.failed_rows == 1

def test_bulk_upload_mark_failed():
    upload = BulkUpload.create("k", "b", "f.csv")
    upload.mark_failed("Network error")
    assert upload.status == BulkUploadStatus.FAILED
    assert upload.error_message == "Network error"
    assert upload.completed_at is not None

def test_bulk_upload_mark_cancelled():
    upload = BulkUpload.create("k", "b", "f.csv")
    upload.mark_cancelled()
    assert upload.status == BulkUploadStatus.CANCELLED
    assert upload.completed_at is not None

def test_bulk_upload_row_create():
    row = BulkUploadRow.create(
        bulk_upload_id="bu_123",
        row_number=1,
        raw_data={"col1": "val1"}
    )
    assert row.id is not None
    assert row.bulk_upload_id == "bu_123"
    assert row.row_number == 1
    assert row.raw_data == {"col1": "val1"}
    assert row.status == BulkUploadRowStatus.PENDING
    assert row.media_id is None
    assert row.error_type is None
    assert row.error_message is None
    assert row.created_at is not None
