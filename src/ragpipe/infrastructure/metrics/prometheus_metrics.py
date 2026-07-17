"""
Prometheus Metrics Collector.

Implementation of MetricsCollector using prometheus_client.
"""

from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Gauge, Histogram

from ragpipe.domain.ports.metrics_collector import MetricsCollector


class PrometheusMetricsCollector(MetricsCollector):
    """Prometheus metrics collector."""

    def __init__(self, prefix: str = "ragpipe_") -> None:
        """Initialize the metrics collector."""
        self._prefix = prefix
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def _get_counter(self, name: str, tags: dict[str, str] | None) -> Counter:
        full_name = f"{self._prefix}{name}"
        if full_name not in self._counters:
            labelnames = list(tags.keys()) if tags else []
            self._counters[full_name] = Counter(full_name, f"{name} count", labelnames)
        return self._counters[full_name]

    def _get_gauge(self, name: str, tags: dict[str, str] | None) -> Gauge:
        full_name = f"{self._prefix}{name}"
        if full_name not in self._gauges:
            labelnames = list(tags.keys()) if tags else []
            self._gauges[full_name] = Gauge(full_name, f"{name} gauge", labelnames)
        return self._gauges[full_name]

    def _get_histogram(self, name: str, tags: dict[str, str] | None) -> Histogram:
        full_name = f"{self._prefix}{name}"
        if full_name not in self._histograms:
            labelnames = list(tags.keys()) if tags else []
            self._histograms[full_name] = Histogram(full_name, f"{name} histogram", labelnames)
        return self._histograms[full_name]

    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        counter = self._get_counter(name, tags)
        if tags:
            counter.labels(**tags).inc(value)
        else:
            counter.inc(value)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        gauge = self._get_gauge(name, tags)
        if tags:
            gauge.labels(**tags).set(value)
        else:
            gauge.set(value)

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a value in a histogram."""
        histogram = self._get_histogram(name, tags)
        if tags:
            histogram.labels(**tags).observe(value)
        else:
            histogram.observe(value)

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None) -> Iterator[None]:
        """Context manager to time a block of code."""
        histogram = self._get_histogram(name, tags)
        if tags:
            with histogram.labels(**tags).time():
                yield
        else:
            with histogram.time():
                yield
