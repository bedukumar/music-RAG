"""
SQLAlchemy State Store.

Implements the StateStore port for tracking pipeline state, jobs,
embedding versions, embedding records, and migrations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ragpipe.domain.models.embedding import EmbeddingRecord, EmbeddingVersion
from ragpipe.domain.models.migration import Migration, MigrationStatus
from ragpipe.domain.models.modality import Modality, ProcessingStatus
from ragpipe.domain.models.pipeline import Job, PipelineStage, PipelineState, StageResult, StageStatus
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.infrastructure.database.models import (
    EmbeddingRecordORM,
    EmbeddingVersionORM,
    JobORM,
    MigrationORM,
    PipelineStateORM,
)

logger = logging.getLogger(__name__)


class SQLAlchemyStateStore(StateStore):
    """SQLAlchemy implementation of the StateStore port.

    Manages persistence of pipeline state, jobs, embedding versions,
    embedding records, and index migrations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    # ── Pipeline State ──────────────────────────────────────────────────

    def _pipeline_state_to_dict(self, state: PipelineState) -> dict:
        """Serialize pipeline state stages to JSON-compatible dict."""
        return [
            {
                "stage": sr.stage.value if isinstance(sr.stage, PipelineStage) else sr.stage,
                "status": sr.status.value if isinstance(sr.status, StageStatus) else sr.status,
                "started_at": sr.started_at.isoformat() if sr.started_at else None,
                "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
                "error_message": sr.error_message,
                "metrics": sr.metrics,
            }
            for sr in state.stages
        ]

    def _dict_to_stages(self, data: list[dict]) -> list[StageResult]:
        """Deserialize JSON stages to StageResult objects."""
        results = []
        for d in data:
            results.append(StageResult(
                stage=PipelineStage(d["stage"]) if d.get("stage") else PipelineStage.VALIDATION,
                status=StageStatus(d["status"]) if d.get("status") else StageStatus.PENDING,
                started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
                completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
                error_message=d.get("error_message"),
                metrics=d.get("metrics", {}),
            ))
        return results

    async def save_pipeline_state(self, state: PipelineState) -> None:
        """Save a pipeline state.

        Args:
            state: The pipeline state to save.
        """
        orm = PipelineStateORM(
            id=state.id,
            media_id=state.media_id,
            modality=state.modality.value if isinstance(state.modality, Modality) else state.modality,
            job_id=state.job_id,
            stages=self._pipeline_state_to_dict(state),
            current_stage=state.current_stage.value if state.current_stage else None,
            overall_status=state.overall_status.value if isinstance(state.overall_status, ProcessingStatus) else state.overall_status,
        )
        await self._session.merge(orm)
        await self._session.commit()
        logger.debug("Saved pipeline state", extra={"state_id": state.id})

    async def get_pipeline_state(
        self, media_id: str, modality: Modality, job_id: Optional[str] = None
    ) -> Optional[PipelineState]:
        """Get pipeline state for a media item and modality.

        Args:
            media_id: The media item ID.
            modality: The modality.
            job_id: Optional specific job ID.

        Returns:
            The pipeline state if found, None otherwise.
        """
        stmt = select(PipelineStateORM).where(
            PipelineStateORM.media_id == media_id,
            PipelineStateORM.modality == modality.value,
        )
        if job_id:
            stmt = stmt.where(PipelineStateORM.job_id == job_id)
        stmt = stmt.order_by(PipelineStateORM.created_at.desc())

        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        return PipelineState(
            id=orm.id,
            media_id=orm.media_id,
            modality=Modality(orm.modality),
            job_id=orm.job_id,
            stages=self._dict_to_stages(orm.stages or []),
            current_stage=PipelineStage(orm.current_stage) if orm.current_stage else None,
            overall_status=ProcessingStatus(orm.overall_status),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def update_stage(self, state_id: str, stage_result: StageResult) -> None:
        """Update a specific stage in a pipeline state.

        Args:
            state_id: The pipeline state ID.
            stage_result: The updated stage result.
        """
        stmt = select(PipelineStateORM).where(PipelineStateORM.id == state_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return

        stages = orm.stages or []
        stage_name = stage_result.stage.value if isinstance(stage_result.stage, PipelineStage) else stage_result.stage

        # Update or add stage
        found = False
        for i, s in enumerate(stages):
            if s.get("stage") == stage_name:
                stages[i] = {
                    "stage": stage_name,
                    "status": stage_result.status.value if isinstance(stage_result.status, StageStatus) else stage_result.status,
                    "started_at": stage_result.started_at.isoformat() if stage_result.started_at else None,
                    "completed_at": stage_result.completed_at.isoformat() if stage_result.completed_at else None,
                    "error_message": stage_result.error_message,
                    "metrics": stage_result.metrics,
                }
                found = True
                break

        if not found:
            stages.append({
                "stage": stage_name,
                "status": stage_result.status.value if isinstance(stage_result.status, StageStatus) else stage_result.status,
                "started_at": stage_result.started_at.isoformat() if stage_result.started_at else None,
                "completed_at": stage_result.completed_at.isoformat() if stage_result.completed_at else None,
                "error_message": stage_result.error_message,
                "metrics": stage_result.metrics,
            })

        orm.stages = stages
        orm.current_stage = stage_name
        orm.updated_at = datetime.now(timezone.utc)

        # Force SQLAlchemy to detect JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(orm, "stages")

        await self._session.commit()

    # ── Jobs ────────────────────────────────────────────────────────────

    async def save_job(self, job: Job) -> None:
        """Save a new job.

        Args:
            job: The job to save.
        """
        orm = JobORM(
            id=job.id,
            media_id=job.media_id,
            modality=job.modality.value if isinstance(job.modality, Modality) else job.modality,
            status=job.status.value if isinstance(job.status, ProcessingStatus) else job.status,
            priority=job.priority,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            pipeline_state_id=job.pipeline_state_id,
        )
        self._session.add(orm)
        await self._session.commit()
        logger.debug("Saved job", extra={"job_id": job.id, "media_id": job.media_id})

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.

        Args:
            job_id: The job ID.

        Returns:
            The job if found, None otherwise.
        """
        stmt = select(JobORM).where(JobORM.id == job_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        return Job(
            id=orm.id,
            media_id=orm.media_id,
            modality=Modality(orm.modality),
            status=ProcessingStatus(orm.status),
            priority=orm.priority,
            created_at=orm.created_at,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            error_message=orm.error_message,
            retry_count=orm.retry_count,
            max_retries=orm.max_retries,
            pipeline_state_id=orm.pipeline_state_id,
        )

    async def list_jobs(
        self,
        status: Optional[str] = None,
        modality: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """List jobs with optional filtering.

        Args:
            status: Optional status filter.
            modality: Optional modality filter.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            Tuple of (jobs list, total count).
        """
        stmt = select(JobORM)
        count_stmt = select(func.count(JobORM.id))

        if status:
            stmt = stmt.where(JobORM.status == status)
            count_stmt = count_stmt.where(JobORM.status == status)
        if modality:
            stmt = stmt.where(JobORM.modality == modality)
            count_stmt = count_stmt.where(JobORM.modality == modality)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(JobORM.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)

        jobs = []
        for orm in result.scalars().all():
            jobs.append(Job(
                id=orm.id,
                media_id=orm.media_id,
                modality=Modality(orm.modality),
                status=ProcessingStatus(orm.status),
                priority=orm.priority,
                created_at=orm.created_at,
                started_at=orm.started_at,
                completed_at=orm.completed_at,
                error_message=orm.error_message,
                retry_count=orm.retry_count,
                max_retries=orm.max_retries,
                pipeline_state_id=orm.pipeline_state_id,
            ))

        return jobs, total

    async def update_job(self, job: Job) -> None:
        """Update an existing job.

        Args:
            job: The job with updated values.
        """
        stmt = select(JobORM).where(JobORM.id == job.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return

        orm.status = job.status.value if isinstance(job.status, ProcessingStatus) else job.status
        orm.started_at = job.started_at
        orm.completed_at = job.completed_at
        orm.error_message = job.error_message
        orm.retry_count = job.retry_count
        orm.pipeline_state_id = job.pipeline_state_id

        await self._session.commit()
        logger.debug("Updated job", extra={"job_id": job.id, "status": orm.status})

    async def get_pending_jobs(self, modality: Optional[Modality] = None, limit: int = 10) -> list[Job]:
        """Get pending jobs ordered by priority.

        Args:
            modality: Optional modality filter.
            limit: Maximum number of jobs.

        Returns:
            List of pending jobs.
        """
        stmt = select(JobORM).where(JobORM.status == "pending")
        if modality:
            stmt = stmt.where(JobORM.modality == modality.value)
        stmt = stmt.order_by(JobORM.priority.desc(), JobORM.created_at.asc()).limit(limit)

        result = await self._session.execute(stmt)
        return [
            Job(
                id=orm.id,
                media_id=orm.media_id,
                modality=Modality(orm.modality),
                status=ProcessingStatus(orm.status),
                priority=orm.priority,
                created_at=orm.created_at,
                started_at=orm.started_at,
                completed_at=orm.completed_at,
                error_message=orm.error_message,
                retry_count=orm.retry_count,
                max_retries=orm.max_retries,
                pipeline_state_id=orm.pipeline_state_id,
            )
            for orm in result.scalars().all()
        ]

    async def get_failed_jobs(self, modality: Optional[Modality] = None, limit: int = 50) -> list[Job]:
        """Get failed jobs.

        Args:
            modality: Optional modality filter.
            limit: Maximum number of jobs.

        Returns:
            List of failed jobs.
        """
        stmt = select(JobORM).where(JobORM.status == "failed")
        if modality:
            stmt = stmt.where(JobORM.modality == modality.value)
        stmt = stmt.order_by(JobORM.created_at.desc()).limit(limit)

        result = await self._session.execute(stmt)
        return [
            Job(
                id=orm.id,
                media_id=orm.media_id,
                modality=Modality(orm.modality),
                status=ProcessingStatus(orm.status),
                priority=orm.priority,
                created_at=orm.created_at,
                started_at=orm.started_at,
                completed_at=orm.completed_at,
                error_message=orm.error_message,
                retry_count=orm.retry_count,
                max_retries=orm.max_retries,
                pipeline_state_id=orm.pipeline_state_id,
            )
            for orm in result.scalars().all()
        ]

    # ── Embedding Versions ──────────────────────────────────────────────

    async def save_embedding_version(self, version: EmbeddingVersion) -> None:
        """Save an embedding version.

        Args:
            version: The embedding version to save.
        """
        orm = EmbeddingVersionORM(
            id=version.id,
            modality=version.modality.value if isinstance(version.modality, Modality) else version.modality,
            model_name=version.model_name,
            model_version=version.model_version,
            dimension=version.dimension,
            chunking_strategy=version.chunking_strategy,
            chunking_version=version.chunking_version,
            pipeline_version=version.pipeline_version,
            is_active=version.is_active,
            created_at=version.created_at,
        )
        self._session.add(orm)
        await self._session.commit()

    async def get_active_embedding_version(self, modality: Modality) -> Optional[EmbeddingVersion]:
        """Get the active embedding version for a modality.

        Args:
            modality: The modality.

        Returns:
            Active embedding version if found.
        """
        stmt = select(EmbeddingVersionORM).where(
            EmbeddingVersionORM.modality == modality.value,
            EmbeddingVersionORM.is_active == True,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        return EmbeddingVersion(
            id=orm.id,
            modality=Modality(orm.modality),
            model_name=orm.model_name,
            model_version=orm.model_version,
            dimension=orm.dimension,
            chunking_strategy=orm.chunking_strategy,
            chunking_version=orm.chunking_version,
            pipeline_version=orm.pipeline_version,
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    async def list_embedding_versions(self, modality: Optional[Modality] = None) -> list[EmbeddingVersion]:
        """List embedding versions.

        Args:
            modality: Optional modality filter.

        Returns:
            List of embedding versions.
        """
        stmt = select(EmbeddingVersionORM)
        if modality:
            stmt = stmt.where(EmbeddingVersionORM.modality == modality.value)
        stmt = stmt.order_by(EmbeddingVersionORM.created_at.desc())

        result = await self._session.execute(stmt)
        return [
            EmbeddingVersion(
                id=orm.id,
                modality=Modality(orm.modality),
                model_name=orm.model_name,
                model_version=orm.model_version,
                dimension=orm.dimension,
                chunking_strategy=orm.chunking_strategy,
                chunking_version=orm.chunking_version,
                pipeline_version=orm.pipeline_version,
                is_active=orm.is_active,
                created_at=orm.created_at,
            )
            for orm in result.scalars().all()
        ]

    async def get_embedding_version(self, version_id: str) -> Optional[EmbeddingVersion]:
        """Get an embedding version by ID.

        Args:
            version_id: The version ID.

        Returns:
            The embedding version if found.
        """
        stmt = select(EmbeddingVersionORM).where(EmbeddingVersionORM.id == version_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        return EmbeddingVersion(
            id=orm.id,
            modality=Modality(orm.modality),
            model_name=orm.model_name,
            model_version=orm.model_version,
            dimension=orm.dimension,
            chunking_strategy=orm.chunking_strategy,
            chunking_version=orm.chunking_version,
            pipeline_version=orm.pipeline_version,
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    # ── Embedding Records ───────────────────────────────────────────────

    async def save_embedding_record(self, record: EmbeddingRecord) -> None:
        """Save an embedding record (idempotent via unique constraint).

        Args:
            record: The embedding record to save.
        """
        # Check if record already exists (idempotency)
        stmt = select(EmbeddingRecordORM).where(
            EmbeddingRecordORM.media_id == record.media_id,
            EmbeddingRecordORM.modality == record.modality.value if isinstance(record.modality, Modality) else record.modality,
            EmbeddingRecordORM.version_id == record.version_id,
            EmbeddingRecordORM.chunk_index == record.chunk_index,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.vector_id = record.vector_id
            existing.chunk_metadata = record.chunk_metadata
        else:
            orm = EmbeddingRecordORM(
                id=record.id,
                media_id=record.media_id,
                modality=record.modality.value if isinstance(record.modality, Modality) else record.modality,
                version_id=record.version_id,
                chunk_index=record.chunk_index,
                vector_id=record.vector_id,
                chunk_metadata=record.chunk_metadata,
                created_at=record.created_at,
            )
            self._session.add(orm)

        await self._session.commit()

    async def get_embedding_records(
        self, media_id: str, modality: Modality
    ) -> list[EmbeddingRecord]:
        """Get all embedding records for a media item and modality.

        Args:
            media_id: The media item ID.
            modality: The modality.

        Returns:
            List of embedding records.
        """
        stmt = select(EmbeddingRecordORM).where(
            EmbeddingRecordORM.media_id == media_id,
            EmbeddingRecordORM.modality == modality.value,
        ).order_by(EmbeddingRecordORM.chunk_index)

        result = await self._session.execute(stmt)
        return [
            EmbeddingRecord(
                id=orm.id,
                media_id=orm.media_id,
                modality=Modality(orm.modality),
                version_id=orm.version_id,
                chunk_index=orm.chunk_index,
                vector_id=orm.vector_id,
                chunk_metadata=orm.chunk_metadata or {},
                created_at=orm.created_at,
            )
            for orm in result.scalars().all()
        ]

    async def delete_embedding_records(self, media_id: str, modality: Modality) -> None:
        """Delete all embedding records for a media item and modality.

        Args:
            media_id: The media item ID.
            modality: The modality.
        """
        stmt = delete(EmbeddingRecordORM).where(
            EmbeddingRecordORM.media_id == media_id,
            EmbeddingRecordORM.modality == modality.value,
        )
        await self._session.execute(stmt)
        await self._session.commit()

    # ── Migrations ──────────────────────────────────────────────────────

    async def save_migration(self, migration: Migration) -> None:
        """Save a migration record.

        Args:
            migration: The migration to save.
        """
        orm = MigrationORM(
            id=migration.id,
            modality=migration.modality.value if isinstance(migration.modality, Modality) else migration.modality,
            from_version_id=migration.from_version_id,
            to_version_id=migration.to_version_id,
            status=migration.status.value if isinstance(migration.status, MigrationStatus) else migration.status,
            total_items=migration.total_items,
            processed_items=migration.processed_items,
            failed_items=migration.failed_items,
            started_at=migration.started_at,
            completed_at=migration.completed_at,
            error_message=migration.error_message,
        )
        self._session.add(orm)
        await self._session.commit()

    async def get_migration(self, migration_id: str) -> Optional[Migration]:
        """Get a migration by ID.

        Args:
            migration_id: The migration ID.

        Returns:
            The migration if found.
        """
        stmt = select(MigrationORM).where(MigrationORM.id == migration_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        return Migration(
            id=orm.id,
            modality=Modality(orm.modality),
            from_version_id=orm.from_version_id,
            to_version_id=orm.to_version_id,
            status=MigrationStatus(orm.status),
            total_items=orm.total_items,
            processed_items=orm.processed_items,
            failed_items=orm.failed_items,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            error_message=orm.error_message,
        )

    async def list_migrations(self, modality: Optional[Modality] = None) -> list[Migration]:
        """List all migrations.

        Args:
            modality: Optional modality filter.

        Returns:
            List of migrations.
        """
        stmt = select(MigrationORM)
        if modality:
            stmt = stmt.where(MigrationORM.modality == modality.value)
        stmt = stmt.order_by(MigrationORM.started_at.desc().nulls_last())

        result = await self._session.execute(stmt)
        return [
            Migration(
                id=orm.id,
                modality=Modality(orm.modality),
                from_version_id=orm.from_version_id,
                to_version_id=orm.to_version_id,
                status=MigrationStatus(orm.status),
                total_items=orm.total_items,
                processed_items=orm.processed_items,
                failed_items=orm.failed_items,
                started_at=orm.started_at,
                completed_at=orm.completed_at,
                error_message=orm.error_message,
            )
            for orm in result.scalars().all()
        ]

    async def update_migration(self, migration: Migration) -> None:
        """Update a migration record.

        Args:
            migration: The migration with updated values.
        """
        stmt = select(MigrationORM).where(MigrationORM.id == migration.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return

        orm.status = migration.status.value if isinstance(migration.status, MigrationStatus) else migration.status
        orm.total_items = migration.total_items
        orm.processed_items = migration.processed_items
        orm.failed_items = migration.failed_items
        orm.started_at = migration.started_at
        orm.completed_at = migration.completed_at
        orm.error_message = migration.error_message

        await self._session.commit()
