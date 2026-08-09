"""Unit tests for S3ObjectStorage adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, create_autospec

import pytest

from ragpipe.domain.ports.object_storage import ObjectNotFoundError, ObjectStorageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_boto3_client():
    """Return a mock boto3 S3 client."""
    client = MagicMock()
    # Simulate the ClientError exception class
    class FakeNoSuchKey(Exception):
        response = {"Error": {"Code": "NoSuchKey"}}
    client.exceptions.NoSuchKey = FakeNoSuchKey
    return client


@pytest.fixture()
def s3_storage(mock_boto3_client):
    """S3ObjectStorage with the boto3 client replaced by a mock directly."""
    from ragpipe.infrastructure.storage.s3_object_storage import S3ObjectStorage

    storage = S3ObjectStorage.__new__(S3ObjectStorage)
    storage._bucket = "test-bucket"
    storage._region = "us-east-1"
    storage._endpoint_url = "http://localhost:4566"
    storage._access_key = "test"
    storage._secret_key = "test"
    storage._client = mock_boto3_client
    return storage


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_calls_put_object(s3_storage, mock_boto3_client):
    """upload() should call put_object with the correct parameters."""
    mock_boto3_client.put_object.return_value = {"ETag": '"abc123"'}

    result = await s3_storage.upload(
        key="bulk-uploads/test-id/file.csv",
        data=b"col1,col2\nval1,val2",
        content_type="text/csv",
    )

    assert result == "bulk-uploads/test-id/file.csv"
    mock_boto3_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="bulk-uploads/test-id/file.csv",
        Body=b"col1,col2\nval1,val2",
        ContentType="text/csv",
    )


@pytest.mark.asyncio
async def test_upload_raises_object_storage_error_on_failure(s3_storage, mock_boto3_client):
    """upload() should wrap boto3 exceptions in ObjectStorageError."""
    mock_boto3_client.put_object.side_effect = Exception("Connection reset")

    with pytest.raises(ObjectStorageError, match="S3 upload failed"):
        await s3_storage.upload(key="test.csv", data=b"data", content_type="text/csv")


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_returns_bytes(s3_storage, mock_boto3_client):
    """download() should return the raw bytes from S3."""
    body_mock = MagicMock()
    body_mock.read.return_value = b"hello world"
    mock_boto3_client.get_object.return_value = {"Body": body_mock}

    result = await s3_storage.download("test-key")

    assert result == b"hello world"


@pytest.mark.asyncio
async def test_download_raises_not_found_on_missing_key(s3_storage, mock_boto3_client):
    """download() should raise ObjectNotFoundError for a NoSuchKey response."""
    # Simulate a botocore ClientError without importing botocore
    class FakeClientError(Exception):
        response = {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}

    mock_boto3_client.get_object.side_effect = FakeClientError()

    with pytest.raises(ObjectNotFoundError):
        await s3_storage.download("missing-key")



# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_returns_true_on_success(s3_storage, mock_boto3_client):
    """delete() should return True when the object is deleted."""
    mock_boto3_client.delete_object.return_value = {}

    result = await s3_storage.delete("some-key")

    assert result is True
    mock_boto3_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="some-key"
    )


@pytest.mark.asyncio
async def test_delete_returns_false_on_error(s3_storage, mock_boto3_client):
    """delete() should return False (not raise) on error."""
    mock_boto3_client.delete_object.side_effect = Exception("Network error")

    result = await s3_storage.delete("some-key")

    assert result is False


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_metadata_returns_dict(s3_storage, mock_boto3_client):
    """get_metadata() should return a normalised dict."""
    from datetime import datetime, timezone

    mock_boto3_client.head_object.return_value = {
        "ContentType": "text/csv",
        "ContentLength": 1024,
        "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "ETag": '"abc123"',
    }

    meta = await s3_storage.get_metadata("bulk-uploads/id/file.csv")

    assert meta["content_type"] == "text/csv"
    assert meta["content_length"] == 1024
    assert meta["etag"] == "abc123"


# ---------------------------------------------------------------------------
# Presigned URL tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_presigned_url(s3_storage, mock_boto3_client):
    """generate_presigned_url() should return the URL from boto3."""
    mock_boto3_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    url = await s3_storage.generate_presigned_url("test-key", expiry_seconds=300)

    assert url == "https://s3.example.com/presigned"
    mock_boto3_client.generate_presigned_url.assert_called_once()
