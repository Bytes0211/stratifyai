"""Cost tracking module for LLM API calls."""

import logging
import os
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _get_default_max_entries() -> int:
    """Return the default retained history size for cost tracking."""
    raw_value = os.getenv("STRATIFYAI_COST_TRACKER_MAX_ENTRIES", "10000")
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return 10_000
    return value if value > 0 else 10_000


@dataclass
class CostEntry:
    """Individual cost entry for an LLM API call."""

    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    request_id: str
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    group: str | None = None


class CostTracker:
    """
    Track and analyze costs across LLM API calls.

    Features:
    - Call history with detailed metrics
    - Grouping by provider, model, or custom tags
    - Cost analytics and reporting
    - Budget tracking and alerts
    - Bounded in-memory history for long-running servers
    """

    def __init__(self, max_entries: int | None = None):
        """Initialize cost tracker.

        Args:
            max_entries: Maximum number of detailed history entries to retain in
                memory. Aggregate totals remain cumulative even when older
                entries are trimmed. If ``None``, the value is read from
                ``STRATIFYAI_COST_TRACKER_MAX_ENTRIES`` and falls back to 10_000.
        """
        if max_entries is None:
            max_entries = _get_default_max_entries()

        self._max_entries = max_entries if max_entries and max_entries > 0 else None
        self._entries: deque[CostEntry] = deque(maxlen=self._max_entries)
        self._total_cost: float = 0.0
        self._total_tokens: int = 0
        self._total_calls: int = 0
        self._cost_by_provider: dict[str, float] = defaultdict(float)
        self._cost_by_model: dict[str, float] = defaultdict(float)
        self._cost_by_group: dict[str, float] = defaultdict(float)
        self._tokens_by_provider: dict[str, int] = defaultdict(int)
        self._budget_limit: float | None = None
        self._alert_threshold: float | None = None

    def add_entry(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: float,
        request_id: str,
        cached_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        group: str | None = None,
    ) -> None:
        """
        Add a cost entry to the tracker.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens used
            cost_usd: Cost in USD
            request_id: Unique request identifier
            cached_tokens: Number of cached tokens
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
            group: Optional group tag for categorization
        """
        entry = CostEntry(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            request_id=request_id,
            cached_tokens=cached_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            group=group,
        )
        self._entries.append(entry)
        self._total_calls += 1
        self._total_cost += cost_usd
        self._total_tokens += total_tokens
        self._cost_by_provider[provider] += cost_usd
        self._cost_by_model[model] += cost_usd
        self._tokens_by_provider[provider] += total_tokens
        if group:
            self._cost_by_group[group] += cost_usd

        # Check budget alerts
        if self._alert_threshold and self._total_cost >= self._alert_threshold:
            self._trigger_alert(self._total_cost, self._alert_threshold)

    def get_total_cost(self) -> float:
        """Get total cost across all tracked calls."""
        return round(self._total_cost, 10)

    def get_total_tokens(self) -> int:
        """Get total tokens across all tracked calls."""
        return self._total_tokens

    def get_call_count(self) -> int:
        """Get total number of tracked calls."""
        return self._total_calls

    def get_entries(
        self,
        provider: str | None = None,
        model: str | None = None,
        group: str | None = None,
    ) -> list[CostEntry]:
        """
        Get filtered cost entries.

        Args:
            provider: Filter by provider name
            model: Filter by model name
            group: Filter by group tag

        Returns:
            List of matching cost entries
        """
        entries = list(self._entries)

        if provider:
            entries = [e for e in entries if e.provider == provider]
        if model:
            entries = [e for e in entries if e.model == model]
        if group:
            entries = [e for e in entries if e.group == group]

        return entries

    def get_cost_by_provider(self) -> dict[str, float]:
        """Get total cost grouped by provider."""
        return {key: round(value, 10) for key, value in self._cost_by_provider.items()}

    def get_cost_by_model(self) -> dict[str, float]:
        """Get total cost grouped by model."""
        return {key: round(value, 10) for key, value in self._cost_by_model.items()}

    def get_cost_by_group(self) -> dict[str, float]:
        """Get total cost grouped by custom group tag."""
        return {key: round(value, 10) for key, value in self._cost_by_group.items()}

    def get_tokens_by_provider(self) -> dict[str, int]:
        """Get total tokens grouped by provider."""
        return dict(self._tokens_by_provider)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache usage statistics."""
        total_cache_reads = sum(e.cache_read_tokens for e in self._entries)
        total_cache_creates = sum(e.cache_creation_tokens for e in self._entries)
        total_prompt_tokens = sum(e.prompt_tokens for e in self._entries)

        cache_hit_rate = 0.0
        if total_prompt_tokens > 0:
            cache_hit_rate = (total_cache_reads / total_prompt_tokens) * 100

        return {
            "total_cache_read_tokens": total_cache_reads,
            "total_cache_creation_tokens": total_cache_creates,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
        }

    def set_budget(self, limit: float, alert_threshold: float | None = None) -> None:
        """
        Set budget limit and optional alert threshold.

        Args:
            limit: Maximum budget in USD
            alert_threshold: Alert when cost reaches this threshold (default: 80% of limit)
        """
        self._budget_limit = limit
        self._alert_threshold = alert_threshold or (limit * 0.8)

    def get_budget_status(self) -> dict[str, Any]:
        """
        Get current budget status.

        Returns:
            Dictionary with budget information
        """
        total_cost = self.get_total_cost()

        if self._budget_limit is None:
            return {
                "budget_set": False,
                "total_cost": total_cost,
            }

        remaining = self._budget_limit - total_cost
        percent_used = (total_cost / self._budget_limit) * 100

        return {
            "budget_set": True,
            "budget_limit": self._budget_limit,
            "total_cost": total_cost,
            "remaining": max(0, round(remaining, 10)),
            "percent_used": round(percent_used, 2),
            "over_budget": total_cost > self._budget_limit,
            "alert_threshold": self._alert_threshold,
        }

    def is_over_budget(self) -> bool:
        """Check if current spending exceeds budget limit."""
        if self._budget_limit is None:
            return False
        return self._total_cost > self._budget_limit

    def reset(self) -> None:
        """Reset all tracked data."""
        self._entries.clear()
        self._total_cost = 0.0
        self._total_tokens = 0
        self._total_calls = 0
        self._cost_by_provider.clear()
        self._cost_by_model.clear()
        self._cost_by_group.clear()
        self._tokens_by_provider.clear()

    def _trigger_alert(self, current_cost: float, threshold: float) -> None:
        """
        Trigger budget alert (can be overridden for custom behavior).

        Args:
            current_cost: Current total cost
            threshold: Alert threshold that was exceeded
        """
        # Override this method for custom alert behavior (email, webhook, etc.)
        logger.warning(
            "Budget alert: current cost $%.4f exceeds threshold $%.4f",
            current_cost,
            threshold,
        )

    def get_summary(self) -> dict[str, Any]:
        """
        Get comprehensive summary of tracked costs.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_cost": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "total_calls": self.get_call_count(),
            "retained_entries": len(self._entries),
            "max_entries": self._max_entries,
            "cost_by_provider": self.get_cost_by_provider(),
            "cost_by_model": self.get_cost_by_model(),
            "cost_by_group": self.get_cost_by_group(),
            "tokens_by_provider": self.get_tokens_by_provider(),
            "cache_stats": self.get_cache_stats(),
            "budget_status": self.get_budget_status(),
        }
