"""State store port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for persisting pipeline states,
jobs, embedding versions, embedding records, and migrations.  It serves as the
central state persistence contract for the entire ingestion pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ragpipe.domain.models.embedding import EmbeddingRecord, EmbeddingVersion
from ragpipe.domain.models.migration import Migration
from ragpipe.domain.models.modality import Modality, ProcessingStatus
from ragpipe.domain.models.pipeline import Job, PipelineState, StageResult


class StateStore(ABC):
    """Abstract interface for pipeline and job state persistence.

    Implementations may use any storage backend (PostgreSQL, Redis, etc.).
    This port aggregates all non-vector persistence operations needed by
    the ingestion pipeline.
    """

    # ------------------------------------------------------------------
    # Pipeline state
    # ------------------------------------------------------------------

    @abstractmethod
    def save_pipeline_state(self, state: PipelineState) -> None:
        """Persist a new pipeline state.

        Args:
            state: The pipeline state to save.
        """

    @abstractmethod
    def get_pipeline_state(
        self,
        media_id: str,
        modality: Modality,
        job_id: str,
    ) -> Optional[PipelineState]:
        """Retrieve a pipeline state by its composite key.

        Args:
            media_id: The media item identifier.
            modality: The processing modality.
            job_id: The parent job identifier.

        Returns:
            The ``PipelineState`` if found, otherwise ``None``.
        """

    @abstractmethod
    def update_stage(
        self,
        state_id: str,
        stage_result: StageResult,
    ) -> None:
        """Update or append a stage result on an existing pipeline state.

        Args:
            state_id: The pipeline state identifier.
            stage_result: The stage result to persist.
        """

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    @abstractmethod
    def save_job(self, job: Job) -> None:
        """Persist a new job.

        Args:
            job: The job to save.
        """

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by its identifier.

        Args:
            job_id: The job identifier.

        Returns:
            The ``Job`` if found, otherwise ``None``.
        """

    @abstractmethod
    def list_jobs(
        self,
        status: Optional[ProcessingStatus] = None,
        modality: Optional[Modality] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """List jobs with optional filtering and pagination.

        Args:
            status: Optional filter by processing status.
            modality: Optional filter by modality.
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            A tuple of ``(jobs, total_count)``.
        """

    @abstractmethod
    def update_job(self, job: Job) -> None:
        """Update an existing job.

        Args:
            job: The updated job instance.
        """

    @abstractmethod
    def get_pending_jobs(
        self,
        modality: Optional[Modality] = None,
        limit: int = 50,
    ) -> list[Job]:
        """Retrieve pending jobs, optionally filtered by modality.

        Results are ordered by priority (descending) then creation time
        (ascending).

        Args:
            modality: Optional modality filter.
            limit: Maximum number of jobs to return.

        Returns:
            List of pending ``Job`` instances.
        """

    @abstractmethod
    def get_failed_jobs(
        self,
        modality: Optional[Modality] = None,
        limit: int = 50,
    ) -> list[Job]:
        """Retrieve failed jobs, optionally filtered by modality.

        Args:
            modality: Optional modality filter.
            limit: Maximum number of jobs to return.

        Returns:
            List of failed ``Job`` instances.
        """

    # ------------------------------------------------------------------
    # Embedding versions
    # ------------------------------------------------------------------

    @abstractmethod
    def save_embedding_version(self, version: EmbeddingVersion) -> None:
        """Persist a new embedding version.

        Args:
            version: The embedding version to save.
        """

    @abstractmethod
    def get_active_embedding_version(
        self, modality: Modality
    ) -> Optional[EmbeddingVersion]:
        """Retrieve the currently active embedding version for a modality.

        Args:
            modality: The target modality.

        Returns:
            The active ``EmbeddingVersion`` if one exists, otherwise ``None``.
        """

    @abstractmethod
    def list_embedding_versions(
        self, modality: Optional[Modality] = None
    ) -> list[EmbeddingVersion]:
        """List embedding versions, optionally filtered by modality.

        Args:
            modality: Optional modality filter.

        Returns:
            List of ``EmbeddingVersion`` instances.
        """

    @abstractmethod
    def get_embedding_version(
        self, version_id: str
    ) -> Optional[EmbeddingVersion]:
        """Retrieve an embedding version by its identifier.

        Args:
            version_id: The version identifier.

        Returns:
            The ``EmbeddingVersion`` if found, otherwise ``None``.
        """

    # ------------------------------------------------------------------
    # Embedding records
    # ------------------------------------------------------------------

    @abstractmethod
    def save_embedding_record(self, record: EmbeddingRecord) -> None:
        """Persist a new embedding record.

        Args:
            record: The embedding record to save.
        """

    @abstractmethod
    def get_embedding_records(
        self,
        media_id: str,
        modality: Optional[Modality] = None,
    ) -> list[EmbeddingRecord]:
        """Retrieve embedding records for a media item.

        Args:
            media_id: The media item identifier.
            modality: Optional modality filter.

        Returns:
            List of ``EmbeddingRecord`` instances.
        """

    @abstractmethod
    def delete_embedding_records(
        self,
        media_id: str,
        modality: Optional[Modality] = None,
    ) -> None:
        """Delete all embedding records for a media item.

        Args:
            media_id: The media item identifier.
            modality: Optional modality filter.  If ``None``, deletes
                records for all modalities.
        """

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    @abstractmethod
    def save_migration(self, migration: Migration) -> None:
        """Persist a new migration.

        Args:
            migration: The migration to save.
        """

    @abstractmethod
    def get_migration(self, migration_id: str) -> Optional[Migration]:
        """Retrieve a migration by its identifier.

        Args:
            migration_id: The migration identifier.

        Returns:
            The ``Migration`` if found, otherwise ``None``.
        """

    @abstractmethod
    def list_migrations(
        self, modality: Optional[Modality] = None
    ) -> list[Migration]:
        """List migrations, optionally filtered by modality.

        Args:
            modality: Optional modality filter.

        Returns:
            List of ``Migration`` instances.
        """

    @abstractmethod
    def update_migration(self, migration: Migration) -> None:
        """Update an existing migration.

        Args:
            migration: The updated migration instance.
        """
