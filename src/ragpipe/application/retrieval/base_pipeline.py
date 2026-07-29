"""Base pipeline for retrieval operations."""

from abc import ABC

from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.retrieval.events import RetrievalStageCompleted
from ragpipe.domain.retrieval.models import RetrievalStage


class BaseRetrievalPipeline(ABC):
    """Abstract base class for retrieval operations."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def _emit_stage_completed(self, stage: RetrievalStage, latency_ms: float) -> None:
        """Helper to emit stage completed events."""
        event = RetrievalStageCompleted(
            stage=stage.value,
            latency_ms=latency_ms,
        )
        await self.event_bus.publish(event)
