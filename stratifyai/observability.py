"""Observability helpers for tracing and metrics.

Provides:
- Correlation ID context management
- Lightweight in-process metrics aggregation for API export
"""

from __future__ import annotations

from collections import defaultdict
from contextvars import ContextVar, Token
from threading import Lock
from typing import Any
from uuid import uuid4

_correlation_id_var: ContextVar[str | None] = ContextVar(
    "stratifyai_correlation_id", default=None
)


def new_correlation_id() -> str:
    """Generate a new correlation ID."""
    return uuid4().hex


def bind_correlation_id(correlation_id: str | None = None) -> tuple[str, Token]:
    """Bind a correlation ID to the current execution context."""
    value = correlation_id or new_correlation_id()
    token = _correlation_id_var.set(value)
    return value, token


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current context, if any."""
    return _correlation_id_var.get()


def reset_correlation_id(token: Token) -> None:
    """Reset the correlation ID context variable using a prior token."""
    _correlation_id_var.reset(token)


def build_log_extra(**data: Any) -> dict[str, Any]:
    """Build structured logging extras with the active correlation ID."""
    extra: dict[str, Any] = {"extra_data": data}
    correlation_id = get_correlation_id()
    if correlation_id:
        extra["correlation_id"] = correlation_id
    return extra


class MetricsRegistry:
    """In-process metrics registry for structured API export."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.http_requests_total = 0
            self.http_responses_total = 0
            self.http_errors_total = 0
            self.http_status_counts: dict[str, int] = defaultdict(int)
            self.http_path_counts: dict[str, int] = defaultdict(int)
            self.http_total_latency_ms = 0.0

            self.stream_requests_total = 0
            self.stream_errors_total = 0
            self.stream_provider_counts: dict[str, int] = defaultdict(int)
            self.stream_model_counts: dict[str, int] = defaultdict(int)
            self.stream_first_token_latency_total_ms = 0.0
            self.stream_first_token_latency_samples = 0
            self.stream_total_latency_total_ms = 0.0
            self.stream_total_latency_samples = 0

    def record_http_request(self, method: str, path: str) -> None:
        """Record an incoming HTTP request."""
        with self._lock:
            self.http_requests_total += 1
            self.http_path_counts[f"{method} {path}"] += 1

    def record_http_response(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        """Record a completed HTTP response."""
        with self._lock:
            self.http_responses_total += 1
            self.http_status_counts[str(status_code)] += 1
            if status_code >= 400:
                self.http_errors_total += 1
            self.http_total_latency_ms += duration_ms

    def record_stream_request(self, provider: str, model: str) -> None:
        """Record a streaming request start."""
        with self._lock:
            self.stream_requests_total += 1
            self.stream_provider_counts[provider] += 1
            self.stream_model_counts[f"{provider}/{model}"] += 1

    def record_stream_completion(
        self,
        first_token_latency_ms: float | None,
        total_latency_ms: float,
    ) -> None:
        """Record a completed streaming response."""
        with self._lock:
            if first_token_latency_ms is not None:
                self.stream_first_token_latency_total_ms += first_token_latency_ms
                self.stream_first_token_latency_samples += 1
            self.stream_total_latency_total_ms += total_latency_ms
            self.stream_total_latency_samples += 1

    def record_stream_error(self) -> None:
        """Record a streaming error."""
        with self._lock:
            self.stream_errors_total += 1

    def export(
        self,
        *,
        api_version: str,
        cache_stats: dict[str, Any] | None = None,
        cost_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Export metrics as structured JSON-compatible data."""
        with self._lock:
            avg_http_latency = (
                self.http_total_latency_ms / self.http_responses_total
                if self.http_responses_total
                else 0.0
            )
            avg_first_token_latency = (
                self.stream_first_token_latency_total_ms
                / self.stream_first_token_latency_samples
                if self.stream_first_token_latency_samples
                else None
            )
            avg_stream_total_latency = (
                self.stream_total_latency_total_ms / self.stream_total_latency_samples
                if self.stream_total_latency_samples
                else None
            )

            return {
                "version": api_version,
                "http": {
                    "requests_total": self.http_requests_total,
                    "responses_total": self.http_responses_total,
                    "errors_total": self.http_errors_total,
                    "avg_latency_ms": round(avg_http_latency, 2),
                    "status_counts": dict(self.http_status_counts),
                    "path_counts": dict(self.http_path_counts),
                },
                "streaming": {
                    "requests_total": self.stream_requests_total,
                    "errors_total": self.stream_errors_total,
                    "avg_first_token_latency_ms": (
                        round(avg_first_token_latency, 2)
                        if avg_first_token_latency is not None
                        else None
                    ),
                    "avg_total_latency_ms": (
                        round(avg_stream_total_latency, 2)
                        if avg_stream_total_latency is not None
                        else None
                    ),
                    "provider_counts": dict(self.stream_provider_counts),
                    "model_counts": dict(self.stream_model_counts),
                },
                "cache": cache_stats or {},
                "cost": cost_summary or {},
            }


metrics_registry = MetricsRegistry()
