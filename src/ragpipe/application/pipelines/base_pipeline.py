"""
Base Pipeline implementation.

Abstract base class for all modality pipelines.
"""

from __future__ import annotations

import hashlib
import structlog
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from dataclasses import replace

from ragpipe.domain.events.events import PipelineFailed, PipelineStageCompleted
from ragpipe.domain.models.chunk import Chunk
from ragpipe.domain.models.embedding import EmbeddingRecord, EmbeddingVersion
from ragpipe.domain.models.modality import Modality, ProcessingStatus
from ragpipe.domain.models.pipeline import Job, PipelineStage, PipelineState, StageResult, StageStatus
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.lock_manager import LockManager
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.vector_repository import VectorRepository

logger = structlog.get_logger(__name__)


class BasePipeline(ABC):
    """Base class for modality processing pipelines."""

    def __init__(
        self,
        media_repository: MediaRepository,
        state_store: StateStore,
        vector_repository: VectorRepository,
        event_bus: EventBus,
        metrics: MetricsCollector,
        lock_manager: LockManager,
        embedding_version: EmbeddingVersion,
    ) -> None:
        self.media_repo = media_repository
        self.state_store = state_store
        self.vector_repo = vector_repository
        self.event_bus = event_bus
        self.metrics = metrics
        self.lock_manager = lock_manager
        self.embedding_version = embedding_version
        
        # Define pipeline stages in order
        self.stages = [
            PipelineStage.VALIDATION,
            PipelineStage.NORMALIZATION,
            PipelineStage.PREPROCESSING,
            PipelineStage.CHUNKING,
            PipelineStage.EMBEDDING,
            PipelineStage.POST_PROCESSING,
            PipelineStage.VECTOR_STORAGE,
        ]

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """The modality this pipeline processes."""
        pass

    def _generate_vector_id(self, media_id: str, chunk_index: int) -> str:
        """Generate deterministic vector ID."""
        import uuid
        key = f"{media_id}:{self.modality.value}:{chunk_index}:{self.embedding_version.id}"
        return str(uuid.uuid5(uuid.NAMESPACE_OID, key))

    async def execute(self, media_id: str, job: Job) -> PipelineState:
        """Execute the pipeline.

        Args:
            media_id: The media item ID.
            job: The job triggering this pipeline.

        Returns:
            The final PipelineState.
        """
        # Determine starting point (resume if possible)
        state_id = f"state-{job.id}"
        existing_state = await self.state_store.get_pipeline_state(media_id, self.modality, job.id)
        
        if existing_state:
            state = existing_state
            # Find first pending or failed stage
            start_idx = 0
            for i, stage in enumerate(self.stages):
                stage_result = next((sr for sr in state.stages if sr.stage == stage), None)
                if not stage_result or stage_result.status in (StageStatus.PENDING, StageStatus.FAILED):
                    start_idx = i
                    break
        else:
            now = datetime.now(timezone.utc)
            stages = [
                StageResult(stage=s, status=StageStatus.PENDING, started_at=None, completed_at=None, error_message=None, metrics={})
                for s in self.stages
            ]
            state = PipelineState(
                id=state_id,
                media_id=media_id,
                modality=self.modality,
                job_id=job.id,
                stages=stages,
                current_stage=self.stages[0],
                overall_status=ProcessingStatus.PROCESSING,
                created_at=now,
                updated_at=now,
            )
            await self.state_store.save_pipeline_state(state)
            start_idx = 0

        # Execute stages
        context: dict[str, Any] = {"media_id": media_id}
        
        log = logger.bind(media_id=media_id, modality=self.modality.value, job_id=job.id)
        
        def update_memory_stage(sr: StageResult):
            for i, s in enumerate(state.stages):
                if s.stage == sr.stage:
                    state.stages[i] = sr
                    return
            state.stages.append(sr)

        for stage in self.stages[start_idx:]:
            state.current_stage = stage
            
            stage_result = StageResult(
                stage=stage,
                status=StageStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                error_message=None,
                metrics={},
            )
            update_memory_stage(stage_result)
            await self.state_store.update_stage(state.id, stage_result)

            try:
                with self.metrics.timer("pipeline_stage_duration_seconds", {"modality": self.modality.value, "stage": stage.value}):
                    stage_metrics = await self._execute_stage(stage, context)
                
                now = datetime.now(timezone.utc)
                stage_result = replace(stage_result, status=StageStatus.COMPLETED, completed_at=now, metrics=stage_metrics or {})
                update_memory_stage(stage_result)
                await self.state_store.update_stage(state.id, stage_result)
                
                duration_ms = (now - stage_result.started_at).total_seconds() * 1000
                await self.event_bus.publish(PipelineStageCompleted(
                    media_id=media_id,
                    modality=self.modality,
                    stage=stage.value,
                    duration_ms=duration_ms,
                ))

            except Exception as e:
                log.exception("Pipeline stage failed", stage=stage.value, error=str(e))
                now = datetime.now(timezone.utc)
                stage_result = replace(stage_result, status=StageStatus.FAILED, completed_at=now, error_message=str(e))
                update_memory_stage(stage_result)
                await self.state_store.update_stage(state.id, stage_result)
                
                state.overall_status = ProcessingStatus.FAILED
                await self.state_store.save_pipeline_state(state)
                
                await self.event_bus.publish(PipelineFailed(
                    media_id=media_id,
                    modality=self.modality,
                    stage=stage.value,
                    error=str(e),
                ))
                self.metrics.increment("pipeline_failures_total", tags={"modality": self.modality.value, "stage": stage.value})
                raise

        # Pipeline complete
        state.current_stage = PipelineStage.COMPLETED
        state.overall_status = ProcessingStatus.COMPLETED
        await self.state_store.save_pipeline_state(state)
        
        return state

    async def _execute_stage(self, stage: PipelineStage, context: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to the specific stage method."""
        if stage == PipelineStage.VALIDATION:
            return await self._validate(context)
        elif stage == PipelineStage.NORMALIZATION:
            return await self._normalize(context)
        elif stage == PipelineStage.PREPROCESSING:
            return await self._preprocess(context)
        elif stage == PipelineStage.CHUNKING:
            return await self._chunk(context)
        elif stage == PipelineStage.EMBEDDING:
            return await self._embed(context)
        elif stage == PipelineStage.POST_PROCESSING:
            return await self._post_process(context)
        elif stage == PipelineStage.VECTOR_STORAGE:
            return await self._store_vectors(context)
        return {}

    @abstractmethod
    async def _validate(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _normalize(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _preprocess(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _chunk(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _embed(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _post_process(self, context: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    async def _store_vectors(self, context: dict[str, Any]) -> dict[str, Any]: ...
