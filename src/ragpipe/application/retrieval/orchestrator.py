"""Retrieval Orchestrator."""

import time
import uuid

from ragpipe.application.retrieval.planner import RetrievalPlanner
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.retrieval.events import SearchCompleted, SearchStarted
from ragpipe.domain.retrieval.models import SearchQuery, SearchSession


class RetrievalOrchestrator:
    """High-level orchestration of search operations."""

    def __init__(self, event_bus: EventBus, planner: RetrievalPlanner):
        self.event_bus = event_bus
        self.planner = planner

    async def execute_search(self, query: SearchQuery) -> SearchSession:
        """Execute a full search session."""
        start_time = time.time()
        session_id = str(uuid.uuid4())

        await self.event_bus.publish(
            SearchStarted(
                query_text=query.text,
                modalities=[m.value for m in query.active_modalities],
            )
        )

        results = await self.planner.plan_and_execute(query)

        latency_ms = (time.time() - start_time) * 1000
        
        await self.event_bus.publish(
            SearchCompleted(
                result_count=len(results),
                total_latency_ms=latency_ms,
            )
        )

        return SearchSession(
            session_id=session_id,
            query=query,
            results=results,
            latency_ms={"total": latency_ms},
        )
