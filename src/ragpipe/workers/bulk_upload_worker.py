"""Bulk Upload Worker — dedicated SQS consumer process.

Run as a separate process:

    python -m ragpipe.workers.bulk_upload_worker

Architecture:
- Polls SQS (long-polling, 20-second wait).
- Downloads the file from S3.
- Parses CSV (stdlib csv) or XLSX (openpyxl, lazy iteration).
- For each row:
    - Checks the idempotency table (bulk_upload_id + row_number) — skips if already done.
    - Validates the row against the expected schema.
    - Calls MediaRegistrar.register_media() and PipelineOrchestrator.process_media().
    - Records the row outcome (processed / failed) in BulkUploadRowORM.
    - Emits BulkUploadRowProcessed or BulkUploadRowFailed events.
- Deletes the SQS message ONLY after the batch is durably recorded.
- Infrastructure errors extend the visibility timeout instead of deleting.

Idempotency guarantee:
    If the same SQS message is delivered twice, row records with status=processed
    are skipped.  This is safe even if the worker crashes mid-batch.

Graceful shutdown:
    SIGTERM/SIGINT sets the shutdown flag; the worker finishes the current
    message before exiting.
"""

from __future__ import annotations

import asyncio
import csv
import html
import io
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Supported media types for bulk rows
VALID_MEDIA_TYPES = {"song", "podcast", "video"}

# How often to flush counter updates back to DB (every N rows)
_COUNTER_FLUSH_INTERVAL = 50


class BulkUploadWorker:
    """SQS-driven worker that processes bulk upload batches.

    Args:
        queue: ``MessageQueue`` port (SQS adapter in production).
        object_storage: ``ObjectStorage`` port (S3 adapter in production).
        bulk_upload_repository: Persistence for BulkUpload and BulkUploadRow.
        media_registrar: Existing service for registering media items.
        pipeline_orchestrator: Existing service for creating/dispatching Jobs.
        event_bus: Existing in-process event bus.
        metrics: Metrics collector.
        visibility_heartbeat_seconds: How long to extend visibility when processing.
    """

    def __init__(
        self,
        queue,
        object_storage,
        bulk_upload_repository,
        media_registrar,
        pipeline_orchestrator,
        event_bus,
        metrics,
        visibility_heartbeat_seconds: int = 270,
    ) -> None:
        self._queue = queue
        self._storage = object_storage
        self._repo = bulk_upload_repository
        self._registrar = media_registrar
        self._orchestrator = pipeline_orchestrator
        self._event_bus = event_bus
        self._metrics = metrics
        self._heartbeat_secs = visibility_heartbeat_seconds
        self._shutdown = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Poll SQS in a loop until a shutdown signal is received."""
        logger.info("bulk_worker_started")
        self._install_signal_handlers()

        while not self._shutdown:
            try:
                messages = await self._queue.receive_messages(max_messages=1, wait_seconds=20)
            except Exception as exc:
                logger.error("sqs_receive_error", error=str(exc))
                await asyncio.sleep(5)
                continue

            for msg in messages:
                if self._shutdown:
                    break
                await self._process_message_safe(msg)

        logger.info("bulk_worker_stopped")

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def _process_message_safe(self, msg) -> None:
        """Process one SQS message with full error isolation."""
        log = logger.bind(
            message_id=msg.message_id,
            receive_count=msg.receive_count,
        )

        try:
            bulk_upload_id = msg.body.get("bulk_upload_id")
            if not bulk_upload_id:
                log.warning("sqs_message_missing_bulk_upload_id")
                # Malformed message — delete it so it doesn't loop forever
                await self._queue.delete_message(msg.receipt_handle)
                return

            log = log.bind(bulk_upload_id=bulk_upload_id)
            log.info("bulk_worker_message_received")

            await self._handle_bulk_upload(msg, bulk_upload_id)

            # ACK the message only after durable work is complete
            await self._queue.delete_message(msg.receipt_handle)
            log.info("sqs_message_deleted")

        except _InfrastructureError as exc:
            # Let the message become visible again for SQS retry
            log.error("bulk_worker_infra_error", error=str(exc))
            try:
                await self._queue.change_visibility(msg.receipt_handle, 30)
            except Exception:
                pass  # visibility change is best-effort
        except Exception as exc:
            log.exception("bulk_worker_unexpected_error", error=str(exc))
            try:
                await self._queue.change_visibility(msg.receipt_handle, 30)
            except Exception:
                pass

    async def _handle_bulk_upload(self, msg, bulk_upload_id: str) -> None:
        """Core processing logic for a single bulk upload SQS message."""
        log = logger.bind(bulk_upload_id=bulk_upload_id)

        # Load the BulkUpload record
        bulk_upload = await self._repo.get(bulk_upload_id)
        if not bulk_upload:
            log.warning("bulk_upload_not_found_in_db")
            # Delete message — no record to process
            await self._queue.delete_message(msg.receipt_handle)
            return

        from ragpipe.domain.models.bulk_upload import BulkUploadStatus

        # Idempotency: skip if already terminal
        terminal_statuses = {
            BulkUploadStatus.COMPLETED,
            BulkUploadStatus.COMPLETED_WITH_ERRORS,
            BulkUploadStatus.FAILED,
            BulkUploadStatus.CANCELLED,
        }
        if bulk_upload.status in terminal_statuses:
            log.info(
                "bulk_upload_already_terminal",
                status=bulk_upload.status.value,
            )
            return  # ACK happens in caller

        # Mark as PROCESSING
        bulk_upload.mark_processing()
        await self._repo.update(bulk_upload)

        # Emit started event
        from ragpipe.domain.events.events import BulkUploadStarted
        await self._event_bus.publish(
            BulkUploadStarted(bulk_upload_id=bulk_upload_id, total_rows=0)
        )

        try:
            # Download file from S3
            log.info("bulk_worker_downloading", object_key=bulk_upload.object_key)
            file_bytes = await self._storage.download(bulk_upload.object_key)
            log.info("bulk_worker_downloaded", bytes=len(file_bytes))

            # Parse and process rows
            await self._process_rows(msg, bulk_upload, file_bytes)

        except Exception as exc:
            log.exception("bulk_worker_processing_failed", error=str(exc))
            bulk_upload.mark_failed(str(exc))
            await self._repo.update(bulk_upload)
            self._metrics.increment("bulk_uploads_failed_total")
            raise _InfrastructureError(str(exc)) from exc

        # Fix: Recompute counters from DB to ensure accuracy after recovery
        counts = await self._repo.count_rows_by_status(bulk_upload.id)
        successful = counts.get("processed", 0)
        failed = counts.get("failed", 0)
        
        bulk_upload.successful_rows = successful
        bulk_upload.failed_rows = failed
        bulk_upload.processed_rows = successful + failed

        bulk_upload.mark_completed()
        await self._repo.update(bulk_upload)

        # Notify completion
        from ragpipe.domain.events.events import BulkUploadCompleted
        await self._event_bus.publish(
            BulkUploadCompleted(
                bulk_upload_id=bulk_upload_id,
                status=bulk_upload.status.value,
                total_rows=bulk_upload.total_rows,
                successful_rows=bulk_upload.successful_rows,
                failed_rows=bulk_upload.failed_rows,
            )
        )
        self._metrics.increment(
            "bulk_uploads_completed_total",
            tags={"status": bulk_upload.status.value},
        )

    async def _process_rows(self, msg, bulk_upload, file_bytes: bytes) -> None:
        """Parse the file and process each row."""
        log = logger.bind(bulk_upload_id=bulk_upload.id)

        filename = bulk_upload.original_filename.lower()
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            rows = list(self._parse_xlsx(file_bytes))
        else:
            rows = list(self._parse_csv(file_bytes))

        bulk_upload.total_rows = len(rows)
        await self._repo.update(bulk_upload)

        log.info("bulk_worker_parsed", total_rows=bulk_upload.total_rows)

        # Update the BulkUploadStarted event with actual count
        from ragpipe.domain.events.events import BulkUploadStarted
        await self._event_bus.publish(
            BulkUploadStarted(
                bulk_upload_id=bulk_upload.id,
                total_rows=bulk_upload.total_rows,
            )
        )

        flush_counter = 0
        last_heartbeat_row = 0
        heartbeat_interval = max(1, bulk_upload.total_rows // 20)  # every 5%

        for row_number, row_data in enumerate(rows, start=1):
            # Extend SQS visibility timeout periodically
            if row_number - last_heartbeat_row >= heartbeat_interval:
                try:
                    await self._queue.change_visibility(
                        msg.receipt_handle, self._heartbeat_secs
                    )
                    last_heartbeat_row = row_number
                except Exception as exc:
                    log.warning("heartbeat_failed", error=str(exc))

            # Idempotency check — skip already-processed rows
            existing_row = await self._repo.get_row(bulk_upload.id, row_number)
            if existing_row and existing_row.status.value == "processed":
                log.debug("bulk_row_already_processed", row_number=row_number)
                continue

            await self._process_single_row(
                bulk_upload=bulk_upload,
                row_number=row_number,
                row_data=row_data,
                existing_row=existing_row,
            )

            flush_counter += 1
            if flush_counter >= _COUNTER_FLUSH_INTERVAL:
                await self._repo.update(bulk_upload)
                flush_counter = 0

        # Final counter flush
        bulk_upload.mark_completed()
        await self._repo.update(bulk_upload)

    async def _process_single_row(
        self,
        bulk_upload,
        row_number: int,
        row_data: dict[str, Any],
        existing_row,
    ) -> None:
        """Process one row: validate → register → create jobs → record."""
        from ragpipe.domain.events.events import BulkUploadRowFailed, BulkUploadRowProcessed
        from ragpipe.domain.models.bulk_upload import BulkUploadRow, BulkUploadRowStatus

        log = logger.bind(bulk_upload_id=bulk_upload.id, row_number=row_number)

        # Create or reuse row record
        if existing_row:
            row = existing_row
        else:
            row = BulkUploadRow.create(
                bulk_upload_id=bulk_upload.id,
                row_number=row_number,
                raw_data={k: str(v) for k, v in row_data.items()},
            )
            await self._repo.save_row(row)

        # Validate
        try:
            media = self._build_media_item(row_data)
        except Exception as exc:
            log.warning("bulk_row_validation_failed", error=str(exc))
            row.status = BulkUploadRowStatus.FAILED
            row.error_type = "validation_error"
            row.error_message = str(exc)
            await self._repo.update_row(row)
            bulk_upload.increment_failure()

            await self._event_bus.publish(
                BulkUploadRowFailed(
                    bulk_upload_id=bulk_upload.id,
                    row_number=row_number,
                    error_type="validation_error",
                    error_message=str(exc)[:500],
                )
            )
            return

        # Register media using existing MediaRegistrar
        try:
            saved_media = await self._registrar.register_media(media)
        except Exception as exc:
            log.warning("bulk_row_registration_failed", error=str(exc))
            row.status = BulkUploadRowStatus.FAILED
            row.error_type = "registration_error"
            row.error_message = str(exc)
            await self._repo.update_row(row)
            bulk_upload.increment_failure()

            await self._event_bus.publish(
                BulkUploadRowFailed(
                    bulk_upload_id=bulk_upload.id,
                    row_number=row_number,
                    error_type="registration_error",
                    error_message=str(exc)[:500],
                )
            )
            return

        # Dispatch through existing PipelineOrchestrator
        try:
            import asyncio
            jobs = await self._orchestrator.process_media(saved_media.id)
            for job in jobs:
                # Fire and forget the execution task since we have a unified architecture
                asyncio.create_task(self._orchestrator.execute_job(job))
        except Exception as exc:
            # Pipeline dispatch failure is non-fatal for the row — the Job is
            # recorded in PENDING state and can be recovered by RecoveryManager.
            log.warning("bulk_row_pipeline_dispatch_failed", error=str(exc))

        # Mark row as successfully processed
        row.status = BulkUploadRowStatus.PROCESSED
        row.media_id = saved_media.id
        await self._repo.update_row(row)
        bulk_upload.increment_success()

        await self._event_bus.publish(
            BulkUploadRowProcessed(
                bulk_upload_id=bulk_upload.id,
                row_number=row_number,
                media_id=saved_media.id,
            )
        )
        self._metrics.increment("bulk_upload_rows_processed_total")

    # ------------------------------------------------------------------
    # File parsing
    # ------------------------------------------------------------------

    def _parse_csv(self, file_bytes: bytes):
        """Parse CSV bytes into an iterator of row dicts."""
        # Try UTF-8 first, fall back to latin-1
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

        reader = csv.DictReader(io.StringIO(text))
        yield from reader

    def _parse_xlsx(self, file_bytes: bytes):
        """Parse XLSX bytes into an iterator of row dicts (lazy, row by row)."""
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for XLSX support. "
                "Install it with: pip install 'ragpipe[bulk]'"
            ) from exc

        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True
        )
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)

        try:
            headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(next(rows_iter))]
        except StopIteration:
            return  # empty sheet

        for row_values in rows_iter:
            yield {headers[i]: (v if v is not None else "") for i, v in enumerate(row_values)}

        wb.close()

    # ------------------------------------------------------------------
    # Media item construction
    # ------------------------------------------------------------------

    def _build_media_item(self, row: dict[str, Any]):
        """Convert a raw row dict to a domain MediaItem.

        Required columns:  title, media_type
        Optional columns:  artist, album, genre, language, source_url, audio_path,
                           transcript_text, tags, duration, lyrics, bpm, musical_key,
                           show_name, episode_number, host, guests,
                           resolution, fps, video_path
        Unknown columns → merged into metadata_fields.
        """
        from ragpipe.domain.models.media import MediaType, Song, Podcast, Video

        def _s(key: str, default: str = "") -> Optional[str]:
            v = row.get(key, default)
            if v is None or str(v).strip() == "":
                return None
            return html.escape(str(v).strip())

        def _f(key: str) -> Optional[float]:
            v = row.get(key)
            if v is None or str(v).strip() == "":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        def _i(key: str) -> Optional[int]:
            v = row.get(key)
            if v is None or str(v).strip() == "":
                return None
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return None

        title = _s("title")
        if not title:
            raise ValueError("Missing required field: 'title'")

        source_url = _s("source_url")
        audio_path = _s("audio_path")
        if not source_url and not audio_path:
            raise ValueError("Missing required field: 'source_url' or 'audio_path' must be provided")

        raw_type = str(row.get("media_type", "song")).strip().lower()
        if raw_type not in VALID_MEDIA_TYPES:
            raise ValueError(
                f"Invalid media_type '{raw_type}'. Must be one of {sorted(VALID_MEDIA_TYPES)}"
            )
        media_type = MediaType(raw_type)

        tags_raw = str(row.get("tags", "")).strip()
        tags = [html.escape(t.strip()) for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        guests_raw = str(row.get("guests", "")).strip()
        guests = [html.escape(g.strip()) for g in guests_raw.split(",") if g.strip()] if guests_raw else []

        # Collect known keys so we can detect extra columns → metadata_fields
        known_keys = {
            "title", "media_type", "artist", "album", "genre", "language",
            "source_url", "audio_path", "transcript_text", "tags", "duration",
            "lyrics", "bpm", "musical_key", "show_name", "episode_number",
            "host", "guests", "resolution", "fps", "video_path",
        }
        metadata_fields = {
            html.escape(k): html.escape(str(v))[:5000]
            for k, v in row.items()
            if k not in known_keys and v is not None and str(v).strip()
        }

        common = dict(
            title=title,
            artist=_s("artist"),
            album=_s("album"),
            genre=_s("genre"),
            tags=tags,
            duration=_f("duration"),
            language=_s("language") or "en",
            source_url=_s("source_url"),
            audio_path=_s("audio_path"),
            transcript_text=_s("transcript_text"),
            metadata_fields=metadata_fields,
        )

        if media_type == MediaType.SONG:
            return Song.create(
                **common,
                lyrics=_s("lyrics"),
                bpm=_f("bpm"),
                key=_s("musical_key"),
            )
        elif media_type == MediaType.PODCAST:
            return Podcast.create(
                **common,
                show_name=_s("show_name"),
                episode_number=_i("episode_number"),
                host=_s("host"),
                guests=guests,
            )
        else:  # video
            return Video.create(
                **common,
                resolution=_s("resolution"),
                fps=_f("fps"),
                video_path=_s("video_path"),
            )

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _install_signal_handlers(self) -> None:
        """Install SIGTERM and SIGINT handlers for graceful shutdown."""

        def _handle(signum, frame):
            logger.info("bulk_worker_shutdown_signal", signal=signum)
            self._shutdown = True

        signal.signal(signal.SIGTERM, _handle)
        signal.signal(signal.SIGINT, _handle)


class _InfrastructureError(Exception):
    """Sentinel for infrastructure-level errors that should trigger SQS retry."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _main() -> None:
    """Bootstrap and run the bulk upload worker."""
    import os
    from ragpipe.container import Container

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    logger.info("bulk_worker_bootstrap_starting")

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///ragpipe.db")
    storage_path = os.getenv("STORAGE_PATH", "./data")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    container = Container(db_url=db_url, storage_path=storage_path, qdrant_url=qdrant_url)
    await container.init_resources()

    if not container.object_storage or not container.message_queue:
        logger.error(
            "bulk_worker_missing_s3_sqs: S3_ENDPOINT_URL / SQS_QUEUE_URL env vars not configured"
        )
        sys.exit(1)

    worker = BulkUploadWorker(
        queue=container.message_queue,
        object_storage=container.object_storage,
        bulk_upload_repository=container.bulk_upload_repository,
        media_registrar=container.media_registrar,
        pipeline_orchestrator=container.pipeline_orchestrator,
        event_bus=container.event_bus,
        metrics=container.metrics,
    )

    try:
        await worker.run()
    finally:
        await container.close_resources()


if __name__ == "__main__":
    asyncio.run(_main())
