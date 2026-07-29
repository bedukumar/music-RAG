"""Domain events for the retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from ragpipe.domain.events.events import DomainEvent


@dataclass(frozen=True)
class SearchStarted(DomainEvent):
    """Emitted when a search request begins."""
    EVENT_TYPE: str = field(default="search.started", init=False, repr=False)
    query_text: str = ""
    modalities: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class SearchCompleted(DomainEvent):
    """Emitted when a search request successfully completes."""
    EVENT_TYPE: str = field(default="search.completed", init=False, repr=False)
    result_count: int = 0
    total_latency_ms: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class SearchFailed(DomainEvent):
    """Emitted when a search request fails."""
    EVENT_TYPE: str = field(default="search.failed", init=False, repr=False)
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class RetrievalStageCompleted(DomainEvent):
    """Emitted when a specific retrieval pipeline stage completes."""
    EVENT_TYPE: str = field(default="retrieval.stage_completed", init=False, repr=False)
    stage: str = ""
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class FusionCompleted(DomainEvent):
    """Emitted when result fusion completes."""
    EVENT_TYPE: str = field(default="retrieval.fusion_completed", init=False, repr=False)
    strategy: str = ""
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)


@dataclass(frozen=True)
class ResultsRanked(DomainEvent):
    """Emitted when re-ranking completes."""
    EVENT_TYPE: str = field(default="retrieval.results_ranked", init=False, repr=False)
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", self.EVENT_TYPE)
