"""SQLAlchemy implementation of the BulkUploadRepository port.

Provides persistence for ``BulkUpload`` and ``BulkUploadRow`` aggregates using
the existing async SQLAlchemy session pattern established in this codebase.

Domain ↔ ORM mapping is handled by private ``_to_domain`` and ``_to_orm``
methods to maintain the clean architecture boundary.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ragpipe.domain.models.bulk_upload import (
    BulkUpload,
    BulkUploadRow,
    BulkUploadRowStatus,
    BulkUploadStatus,
)
from ragpipe.domain.ports.bulk_upload_repository import BulkUploadRepository
from ragpipe.infrastructure.database.models import BulkUploadORM, BulkUploadRowORM

logger = logging.getLogger(__name__)


class SQLAlchemyBulkUploadRepository(BulkUploadRepository):
    """SQLAlchemy/SQLite implementation of ``BulkUploadRepository``."""

    def __init__(self, session: Any) -> None:
        """Initialise with a scoped async session (same pattern as other repos).

        Args:
            session: ``async_scoped_session`` factory — the repository
                calls ``session()`` to get the current task-scoped session.
        """
        self._session = session

    # ------------------------------------------------------------------
    # BulkUpload CRUD
    # ------------------------------------------------------------------

    async def save(self, bulk_upload: BulkUpload) -> BulkUpload:
        """Persist a new BulkUpload record."""
        orm = self._bulk_upload_to_orm(bulk_upload)
        async with self._get_session() as session:
            session.add(orm)
            await session.flush()
        return bulk_upload

    async def get(self, bulk_upload_id: str) -> Optional[BulkUpload]:
        """Retrieve a BulkUpload by its ID."""
        async with self._get_session() as session:
            result = await session.execute(
                select(BulkUploadORM).where(BulkUploadORM.id == bulk_upload_id)
            )
            orm = result.scalar_one_or_none()
            return self._bulk_upload_to_domain(orm) if orm else None

    async def update(self, bulk_upload: BulkUpload) -> BulkUpload:
        """Persist updates to an existing BulkUpload."""
        async with self._get_session() as session:
            await session.execute(
                update(BulkUploadORM)
                .where(BulkUploadORM.id == bulk_upload.id)
                .values(
                    status=bulk_upload.status.value,
                    total_rows=bulk_upload.total_rows,
                    processed_rows=bulk_upload.processed_rows,
                    successful_rows=bulk_upload.successful_rows,
                    failed_rows=bulk_upload.failed_rows,
                    started_at=bulk_upload.started_at,
                    completed_at=bulk_upload.completed_at,
                    error_message=bulk_upload.error_message,
                )
            )
        return bulk_upload

    async def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BulkUpload], int]:
        """List bulk uploads, optionally filtered by status."""
        async with self._get_session() as session:
            query = select(BulkUploadORM)
            count_query = select(func.count(BulkUploadORM.id))

            if status:
                query = query.where(BulkUploadORM.status == status.upper())
                count_query = count_query.where(BulkUploadORM.status == status.upper())

            query = query.order_by(BulkUploadORM.created_at.desc()).offset(offset).limit(limit)

            result = await session.execute(query)
            items = [self._bulk_upload_to_domain(r) for r in result.scalars().all()]

            count_result = await session.execute(count_query)
            total = count_result.scalar_one()

        return items, total

    # ------------------------------------------------------------------
    # BulkUploadRow CRUD
    # ------------------------------------------------------------------

    async def save_row(self, row: BulkUploadRow) -> BulkUploadRow:
        """Persist a new bulk upload row record."""
        orm = self._row_to_orm(row)
        async with self._get_session() as session:
            session.add(orm)
            await session.flush()
        return row

    async def get_row(
        self,
        bulk_upload_id: str,
        row_number: int,
    ) -> Optional[BulkUploadRow]:
        """Retrieve a row by the idempotency key (bulk_upload_id, row_number)."""
        async with self._get_session() as session:
            result = await session.execute(
                select(BulkUploadRowORM).where(
                    BulkUploadRowORM.bulk_upload_id == bulk_upload_id,
                    BulkUploadRowORM.row_number == row_number,
                )
            )
            orm = result.scalar_one_or_none()
            return self._row_to_domain(orm) if orm else None

    async def update_row(self, row: BulkUploadRow) -> BulkUploadRow:
        """Persist updates to an existing row record."""
        async with self._get_session() as session:
            await session.execute(
                update(BulkUploadRowORM)
                .where(BulkUploadRowORM.id == row.id)
                .values(
                    status=row.status.value,
                    media_id=row.media_id,
                    error_type=row.error_type,
                    error_message=row.error_message,
                )
            )
        return row

    async def list_rows(
        self,
        bulk_upload_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[BulkUploadRow], int]:
        """List rows for a bulk upload."""
        async with self._get_session() as session:
            query = select(BulkUploadRowORM).where(
                BulkUploadRowORM.bulk_upload_id == bulk_upload_id
            )
            count_query = select(func.count(BulkUploadRowORM.id)).where(
                BulkUploadRowORM.bulk_upload_id == bulk_upload_id
            )

            if status:
                query = query.where(BulkUploadRowORM.status == status.lower())
                count_query = count_query.where(BulkUploadRowORM.status == status.lower())

            query = query.order_by(BulkUploadRowORM.row_number).offset(offset).limit(limit)

            result = await session.execute(query)
            rows = [self._row_to_domain(r) for r in result.scalars().all()]

            count_result = await session.execute(count_query)
            total = count_result.scalar_one()

        return rows, total

    async def count_rows_by_status(
        self,
        bulk_upload_id: str,
    ) -> dict[str, int]:
        """Count rows grouped by status."""
        async with self._get_session() as session:
            result = await session.execute(
                select(BulkUploadRowORM.status, func.count(BulkUploadRowORM.id))
                .where(BulkUploadRowORM.bulk_upload_id == bulk_upload_id)
                .group_by(BulkUploadRowORM.status)
            )
            counts: dict[str, int] = defaultdict(int)
            for row_status, cnt in result.all():
                counts[row_status] = cnt
        return dict(counts)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _get_session(self):
        """Context manager that yields a session and commits/rolls back."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _ctx():
            session: AsyncSession = self._session()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        return _ctx()

    def _bulk_upload_to_orm(self, b: BulkUpload) -> BulkUploadORM:
        return BulkUploadORM(
            id=b.id,
            object_key=b.object_key,
            bucket=b.bucket,
            original_filename=b.original_filename,
            status=b.status.value,
            total_rows=b.total_rows,
            processed_rows=b.processed_rows,
            successful_rows=b.successful_rows,
            failed_rows=b.failed_rows,
            created_at=b.created_at,
            started_at=b.started_at,
            completed_at=b.completed_at,
            error_message=b.error_message,
        )

    def _bulk_upload_to_domain(self, orm: BulkUploadORM) -> BulkUpload:
        return BulkUpload(
            id=orm.id,
            object_key=orm.object_key,
            bucket=orm.bucket,
            original_filename=orm.original_filename,
            status=BulkUploadStatus(orm.status),
            total_rows=orm.total_rows,
            processed_rows=orm.processed_rows,
            successful_rows=orm.successful_rows,
            failed_rows=orm.failed_rows,
            created_at=orm.created_at,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            error_message=orm.error_message,
        )

    def _row_to_orm(self, r: BulkUploadRow) -> BulkUploadRowORM:
        return BulkUploadRowORM(
            id=r.id,
            bulk_upload_id=r.bulk_upload_id,
            row_number=r.row_number,
            status=r.status.value,
            media_id=r.media_id,
            error_type=r.error_type,
            error_message=r.error_message,
            raw_data=r.raw_data,
            created_at=r.created_at,
        )

    def _row_to_domain(self, orm: BulkUploadRowORM) -> BulkUploadRow:
        return BulkUploadRow(
            id=orm.id,
            bulk_upload_id=orm.bulk_upload_id,
            row_number=orm.row_number,
            status=BulkUploadRowStatus(orm.status),
            media_id=orm.media_id,
            error_type=orm.error_type,
            error_message=orm.error_message,
            raw_data=orm.raw_data or {},
            created_at=orm.created_at,
        )
