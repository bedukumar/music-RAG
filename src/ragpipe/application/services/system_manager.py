import time
import os
import psutil
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
        self.start_time = time.time()

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
        uptime = int(time.time() - self.start_time)
        try:
            mem = psutil.virtual_memory()
            mem_usage_mb = (mem.total - mem.available) // (1024 * 1024)
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            mem_usage_mb = 0
            cpu_percent = 0.0

        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "memory_usage_mb": mem_usage_mb,
            "cpu_usage_percent": cpu_percent,
        }
