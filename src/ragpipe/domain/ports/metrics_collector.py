"""Metrics collector port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for operational metrics
collection.  Implementations may use Prometheus, StatsD, Datadog, or
any other metrics system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterator, Optional


class MetricsCollector(ABC):
    """Abstract interface for collecting operational metrics.

    Supports counters, gauges, histograms, and timers.  All methods accept
    optional tags for dimensional aggregation.
    """

    @abstractmethod
    def increment(
        self,
        name: str,
        value: float = 1,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name (e.g. ``pipeline.items_processed``).
            value: Amount to increment by (default 1).
            tags: Optional dimensional tags.
        """

    @abstractmethod
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric to an absolute value.

        Args:
            name: Metric name.
            value: The gauge value.
            tags: Optional dimensional tags.
        """

    @abstractmethod
    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Record a value in a histogram metric.

        Args:
            name: Metric name.
            value: The observed value.
            tags: Optional dimensional tags.
        """

    @abstractmethod
    def timer(
        self,
        name: str,
        tags: Optional[dict[str, str]] = None,
    ) -> Iterator[None]:
        """Context manager that records the elapsed time as a histogram.

        Usage::

            with metrics.timer("pipeline.stage_duration", tags={"stage": "chunking"}):
                do_chunking()

        Args:
            name: Metric name.
            tags: Optional dimensional tags.

        Yields:
            Nothing — the timing is recorded on context exit.
        """
