"""Pipeline domain models for the RAG Data Ingestion Platform.

This module defines the pipeline processing state machine, including the
pipeline stages, per-stage results, overall pipeline state, and the job
entity that drives work scheduling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ragpipe.domain.exceptions import PipelineError, ValidationError
from ragpipe.domain.models.modality import Modality, ProcessingStatus


class PipelineStage(Enum):
    """Ordered stages in the data ingestion pipeline."""

    VALIDATION = "validation"
    NORMALIZATION = "normalization"
    PREPROCESSING = "preprocessing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    POST_PROCESSING = "post_processing"
    VECTOR_STORAGE = "vector_storage"
    COMPLETED = "completed"


class StageStatus(Enum):
    """Execution status of a single pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of executing a single pipeline stage.

    Attributes:
        stage: The pipeline stage this result corresponds to.
        status: Execution status.
        started_at: When execution started.
        completed_at: When execution ended.
        error_message: Error details if the stage failed.
        metrics: Operational metrics (e.g. ``duration_ms``, ``items_processed``).
    """

    stage: PipelineStage
    status: StageStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: dict[str, object] = field(default_factory=dict)


@dataclass
class PipelineState:
    """Mutable aggregate tracking the full processing state of a pipeline run.

    This is an aggregate root — it owns the list of ``StageResult`` objects
    and governs state transitions.

    Attributes:
        id: Unique pipeline state identifier.
        media_id: The media item being processed.
        modality: The modality being processed.
        job_id: The associated job identifier.
        stages: Ordered list of stage results.
        current_stage: The stage currently being executed.
        overall_status: Aggregate status of the pipeline.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    id: str
    media_id: str
    modality: Modality
    job_id: str
    stages: list[StageResult] = field(default_factory=list)
    current_stage: Optional[PipelineStage] = None
    overall_status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "PipelineState id must not be empty")
        if not self.media_id:
            raise ValidationError("media_id", "media_id must not be empty")

    def advance_stage(self, next_stage: PipelineStage) -> StageResult:
        """Advance the pipeline to the next stage.

        Marks the current stage as completed (if one exists) and starts the
        next stage.

        Args:
            next_stage: The stage to advance to.

        Returns:
            The newly created ``StageResult`` for the next stage.

        Raises:
            PipelineError: If the pipeline is in a terminal state.
        """
        now = datetime.now(timezone.utc)

        if self.overall_status in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ):
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage=next_stage.value,
                details=f"Cannot advance: pipeline is already {self.overall_status.value}",
            )

        # Mark the running stage as completed
        if self.current_stage is not None:
            self._complete_current_stage(now)

        new_result = StageResult(
            stage=next_stage,
            status=StageStatus.RUNNING,
            started_at=now,
        )
        self.stages.append(new_result)
        self.current_stage = next_stage
        self.overall_status = ProcessingStatus.PROCESSING
        self.updated_at = now
        return new_result

    def fail_stage(self, error: str) -> StageResult:
        """Mark the current stage and the overall pipeline as failed.

        Args:
            error: Human-readable error description.

        Returns:
            The updated ``StageResult`` for the failed stage.

        Raises:
            PipelineError: If there is no current stage to fail.
        """
        now = datetime.now(timezone.utc)

        if self.current_stage is None:
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="unknown",
                details="No current stage to fail",
            )

        failed_result = StageResult(
            stage=self.current_stage,
            status=StageStatus.FAILED,
            started_at=self._get_current_stage_start(),
            completed_at=now,
            error_message=error,
        )
        self._replace_current_stage_result(failed_result)
        self.overall_status = ProcessingStatus.FAILED
        self.updated_at = now
        return failed_result

    def complete(self) -> None:
        """Mark the pipeline as successfully completed.

        Raises:
            PipelineError: If the pipeline is already in a terminal state.
        """
        now = datetime.now(timezone.utc)

        if self.overall_status in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ):
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="complete",
                details=f"Cannot complete: pipeline is already {self.overall_status.value}",
            )

        if self.current_stage is not None:
            self._complete_current_stage(now)

        self.overall_status = ProcessingStatus.COMPLETED
        self.current_stage = PipelineStage.COMPLETED
        self.updated_at = now

    def get_failed_stage(self) -> Optional[StageResult]:
        """Return the first failed stage result, if any.

        Returns:
            The ``StageResult`` with ``FAILED`` status, or ``None``.
        """
        for result in self.stages:
            if result.status == StageStatus.FAILED:
                return result
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _complete_current_stage(self, now: datetime) -> None:
        """Mark the current running stage as completed."""
        completed = StageResult(
            stage=self.current_stage,  # type: ignore[arg-type]
            status=StageStatus.COMPLETED,
            started_at=self._get_current_stage_start(),
            completed_at=now,
            metrics=self._get_current_stage_metrics(),
        )
        self._replace_current_stage_result(completed)

    def _get_current_stage_start(self) -> Optional[datetime]:
        """Get the start time of the current running stage."""
        for result in reversed(self.stages):
            if result.stage == self.current_stage:
                return result.started_at
        return None

    def _get_current_stage_metrics(self) -> dict[str, object]:
        """Get the metrics of the current running stage."""
        for result in reversed(self.stages):
            if result.stage == self.current_stage:
                return dict(result.metrics)
        return {}

    def _replace_current_stage_result(self, new_result: StageResult) -> None:
        """Replace the last stage result matching the current stage."""
        for i in range(len(self.stages) - 1, -1, -1):
            if self.stages[i].stage == self.current_stage:
                self.stages[i] = new_result
                return
        self.stages.append(new_result)

    @classmethod
    def create(
        cls,
        media_id: str,
        modality: Modality,
        job_id: str,
    ) -> PipelineState:
        """Factory method to create a new ``PipelineState`` with a generated UUID.

        Args:
            media_id: The media item to process.
            modality: The modality to process.
            job_id: The parent job identifier.

        Returns:
            A new ``PipelineState`` in ``PENDING`` status.
        """
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            media_id=media_id,
            modality=modality,
            job_id=job_id,
            stages=[],
            current_stage=None,
            overall_status=ProcessingStatus.PENDING,
            created_at=now,
            updated_at=now,
        )


@dataclass
class Job:
    """A scheduled unit of work in the ingestion pipeline.

    Jobs are created, queued, picked up by workers, and driven through the
    pipeline stages.  They support retry semantics with a configurable max
    retry count.

    Attributes:
        id: Unique job identifier (UUID-4 string).
        media_id: The media item this job processes.
        modality: The modality this job targets.
        status: Current processing status.
        priority: Scheduling priority (higher = more urgent).
        created_at: Timestamp of creation.
        started_at: When execution started.
        completed_at: When execution ended.
        error_message: Error details on failure.
        retry_count: Number of times this job has been retried.
        max_retries: Maximum allowed retries before permanent failure.
        pipeline_state_id: The associated ``PipelineState.id``.
    """

    id: str
    media_id: str
    modality: Modality
    status: ProcessingStatus = ProcessingStatus.PENDING
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    pipeline_state_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.id:
            raise ValidationError("id", "Job id must not be empty")
        if not self.media_id:
            raise ValidationError("media_id", "media_id must not be empty")
        if self.priority < 0:
            raise ValidationError(
                "priority", f"Priority must be non-negative, got {self.priority}"
            )
        if self.max_retries < 0:
            raise ValidationError(
                "max_retries",
                f"max_retries must be non-negative, got {self.max_retries}",
            )

    def start(self) -> None:
        """Mark the job as started / processing.

        Raises:
            PipelineError: If the job is not in a startable state.
        """
        if self.status not in (ProcessingStatus.PENDING, ProcessingStatus.FAILED):
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="job_start",
                details=f"Cannot start job in status {self.status.value}",
            )
        self.status = ProcessingStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self.error_message = None

    def complete(self) -> None:
        """Mark the job as successfully completed.

        Raises:
            PipelineError: If the job is not currently processing.
        """
        if self.status != ProcessingStatus.PROCESSING:
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="job_complete",
                details=f"Cannot complete job in status {self.status.value}",
            )
        self.status = ProcessingStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str) -> None:
        """Mark the job as failed.

        Args:
            error: Human-readable error description.

        Raises:
            PipelineError: If the job is not currently processing.
        """
        if self.status != ProcessingStatus.PROCESSING:
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="job_fail",
                details=f"Cannot fail job in status {self.status.value}",
            )
        self.status = ProcessingStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error

    def can_retry(self) -> bool:
        """Check whether the job is eligible for another retry.

        Returns:
            ``True`` if the retry count is below the maximum.
        """
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment the retry counter and reset status for re-processing.

        Raises:
            PipelineError: If the job has exhausted its retry budget.
        """
        if not self.can_retry():
            raise PipelineError(
                media_id=self.media_id,
                modality=self.modality.value,
                stage="job_retry",
                details=f"Max retries ({self.max_retries}) exhausted",
            )
        self.retry_count += 1
        self.status = ProcessingStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error_message = None

    @classmethod
    def create(
        cls,
        media_id: str,
        modality: Modality,
        priority: int = 0,
        max_retries: int = 3,
    ) -> Job:
        """Factory method to create a new ``Job`` with a generated UUID.

        Args:
            media_id: The media item to process.
            modality: The target modality.
            priority: Scheduling priority.
            max_retries: Maximum retry attempts.

        Returns:
            A new ``Job`` in ``PENDING`` status.
        """
        return cls(
            id=str(uuid.uuid4()),
            media_id=media_id,
            modality=modality,
            status=ProcessingStatus.PENDING,
            priority=priority,
            created_at=datetime.now(timezone.utc),
            max_retries=max_retries,
        )
