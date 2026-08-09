"""S3 Object Storage adapter for the RAG Data Ingestion Platform.

Implements the ``ObjectStorage`` port using AWS S3 (or LocalStack for local
development).  boto3 is used via ``asyncio.get_event_loop().run_in_executor``
to avoid blocking the async event loop.

Configuration is read from the environment — never hardcoded:

    AWS_REGION              AWS region (default: us-east-1)
    AWS_ACCESS_KEY_ID       Access key (use "test" for LocalStack)
    AWS_SECRET_ACCESS_KEY   Secret key (use "test" for LocalStack)
    S3_BUCKET               Target bucket name
    S3_ENDPOINT_URL         Custom endpoint URL (LocalStack only — leave unset for AWS)

When ``S3_ENDPOINT_URL`` is set the adapter disables SSL verification so it
works with the LocalStack self-signed certificate.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Optional

import structlog

from ragpipe.domain.ports.object_storage import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
)

logger = structlog.get_logger(__name__)

# Thread pool dedicated to boto3 I/O calls
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="s3-io")


class S3ObjectStorage(ObjectStorage):
    """AWS S3 / LocalStack implementation of the ``ObjectStorage`` port.

    Args:
        bucket: Target S3 bucket name.
        region: AWS region.
        endpoint_url: Optional custom endpoint (set for LocalStack).
        aws_access_key_id: AWS access key ID.  ``None`` → use IAM role.
        aws_secret_access_key: AWS secret access key.  ``None`` → use IAM role.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._access_key = aws_access_key_id
        self._secret_key = aws_secret_access_key
        self._client = self._build_client()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to S3 under the given key."""
        log = logger.bind(bucket=self._bucket, key=key, content_type=content_type)
        try:
            await self._run(
                self._client.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            log.info("s3_upload_success", bytes=len(data))
            return key
        except Exception as exc:
            log.error("s3_upload_failed", error=str(exc))
            raise ObjectStorageError(f"S3 upload failed for key '{key}': {exc}") from exc

    async def download(self, key: str) -> bytes:
        """Download raw bytes from S3."""
        log = logger.bind(bucket=self._bucket, key=key)
        try:
            response = await self._run(
                self._client.get_object,
                Bucket=self._bucket,
                Key=key,
            )
            body: bytes = response["Body"].read()
            log.info("s3_download_success", bytes=len(body))
            return body
        except self._client.exceptions.NoSuchKey:
            raise ObjectNotFoundError(f"S3 key not found: '{key}'")
        except Exception as exc:
            # Botocore raises ClientError with code NoSuchKey — catch generically
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(f"S3 key not found: '{key}'") from exc
            log.error("s3_download_failed", error=str(exc))
            raise ObjectStorageError(f"S3 download failed for key '{key}': {exc}") from exc

    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Return head metadata for an S3 object."""
        try:
            resp = await self._run(
                self._client.head_object,
                Bucket=self._bucket,
                Key=key,
            )
            return {
                "content_type": resp.get("ContentType", ""),
                "content_length": resp.get("ContentLength", 0),
                "last_modified": resp.get("LastModified"),
                "etag": resp.get("ETag", "").strip('"'),
            }
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey"):
                raise ObjectNotFoundError(f"S3 key not found: '{key}'") from exc
            raise ObjectStorageError(f"S3 head_object failed for '{key}': {exc}") from exc

    async def delete(self, key: str) -> bool:
        """Delete an S3 object.  Returns False if the key did not exist."""
        try:
            await self._run(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=key,
            )
            logger.info("s3_delete_success", bucket=self._bucket, key=key)
            return True
        except Exception as exc:
            logger.warning("s3_delete_failed", key=key, error=str(exc))
            return False

    async def generate_presigned_url(
        self,
        key: str,
        expiry_seconds: int = 3600,
    ) -> str:
        """Generate a time-limited pre-signed GET URL."""
        try:
            url: str = await self._run(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expiry_seconds,
            )
            return url
        except Exception as exc:
            raise ObjectStorageError(
                f"Presigned URL generation failed for '{key}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_client(self):  # type: ignore[return]
        """Construct and return a boto3 S3 client."""
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for S3 support. "
                "Install it with: pip install 'ragpipe[bulk]'"
            ) from exc

        kwargs: dict[str, Any] = {
            "region_name": self._region,
        }
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
            # LocalStack uses a self-signed cert; disable verification
            from botocore.config import Config
            kwargs["config"] = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
            kwargs["verify"] = False
        if self._access_key and self._secret_key:
            kwargs["aws_access_key_id"] = self._access_key
            kwargs["aws_secret_access_key"] = self._secret_key

        return boto3.client("s3", **kwargs)

    async def _run(self, fn, *args, **kwargs) -> Any:
        """Run a synchronous boto3 call in the dedicated thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, partial(fn, *args, **kwargs))
