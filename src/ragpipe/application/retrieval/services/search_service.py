"""Search Service."""

import time
from typing import Dict, Any, List

from ragpipe.application.retrieval.orchestrator import RetrievalOrchestrator
from ragpipe.domain.retrieval.models import SearchQuery, SearchSession


class SearchService:
    """Service layer for search operations."""

    def __init__(self, orchestrator: RetrievalOrchestrator):
        self.orchestrator = orchestrator
        self.search_history = []

    async def search(self, query: SearchQuery) -> SearchSession:
        """Execute a search."""
        session = await self.orchestrator.execute_search(query)
        
        entry = {
            "id": session.session_id,
            "timestamp": time.time(),
            "query": query.text,
            "modalities": [m.value for m in query.active_modalities],
            "latency_ms": session.latency_ms.get("total", 0.0),
            "retrieved_count": len(session.results)
        }
        self.search_history.append(entry)
        
        return session

    async def get_history(self) -> List[Dict[str, Any]]:
        return self.search_history

    async def get_analytics(self) -> Dict[str, Any]:
        total = len(self.search_history)
        avg_latency = sum(e["latency_ms"] for e in self.search_history) / total if total else 0.0
        
        mod_counts = {}
        query_counts = {}
        for e in self.search_history:
            for m in e["modalities"]:
                mod_counts[m] = mod_counts.get(m, 0) + 1
                
            q = e["query"]
            if q:
                query_counts[q] = query_counts.get(q, 0) + 1
            
        top_queries = sorted([{"query": q, "count": c} for q, c in query_counts.items()], key=lambda x: x["count"], reverse=True)[:10]
        
        return {
            "totalSearches": total,
            "averageLatencyMs": avg_latency,
            "topModalities": mod_counts,
            "topQueries": top_queries
        }
