import time
from typing import Dict, Any, List
from collections import deque
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.events.events import DomainEvent

class SystemManager:
    """Service for handling system metrics and events audit log."""
    def __init__(self, metrics: MetricsCollector, event_bus: EventBus):
        self.metrics = metrics
        self.event_bus = event_bus
        self.recent_events = deque(maxlen=1000)

    def log_event(self, event: DomainEvent):
        self.recent_events.append({
            "timestamp": time.time(),
            "type": event.event_type,
            "data": str(event.__dict__)  # stringify to avoid serialization issues
        })

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        events = list(self.recent_events)
        events.reverse()
        return events[:limit]

    def get_metrics(self) -> Dict[str, Any]:
        # Return dummy system metrics since the collector may only push out (like statsd/prometheus)
        return {
            "status": "healthy",
            "uptime_seconds": 3600,
            "active_pipelines": 2,
            "total_media_processed": 1500,
            "memory_usage_mb": 256
        }
