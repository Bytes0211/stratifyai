"""Cost tracking module for LLM API calls."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


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
    group: Optional[str] = None


class CostTracker:
    """
    Track and analyze costs across LLM API calls.
    
    Features:
    - Call history with detailed metrics
    - Grouping by provider, model, or custom tags
    - Cost analytics and reporting
    - Budget tracking and alerts
    """
    
    def __init__(self):
        """Initialize cost tracker."""
        self._entries: List[CostEntry] = []
        self._total_cost: float = 0.0
        self._budget_limit: Optional[float] = None
        self._alert_threshold: Optional[float] = None
    
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
        group: Optional[str] = None,
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
        self._total_cost += cost_usd
        
        # Check budget alerts
        if self._alert_threshold and self._total_cost >= self._alert_threshold:
            self._trigger_alert(self._total_cost, self._alert_threshold)
    
    def get_total_cost(self) -> float:
        """Get total cost across all tracked calls."""
        return self._total_cost
    
    def get_total_tokens(self) -> int:
        """Get total tokens across all tracked calls."""
        return sum(entry.total_tokens for entry in self._entries)
    
    def get_call_count(self) -> int:
        """Get total number of tracked calls."""
        return len(self._entries)
    
    def get_entries(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        group: Optional[str] = None,
    ) -> List[CostEntry]:
        """
        Get filtered cost entries.
        
        Args:
            provider: Filter by provider name
            model: Filter by model name
            group: Filter by group tag
            
        Returns:
            List of matching cost entries
        """
        entries = self._entries
        
        if provider:
            entries = [e for e in entries if e.provider == provider]
        if model:
            entries = [e for e in entries if e.model == model]
        if group:
            entries = [e for e in entries if e.group == group]
        
        return entries
    
    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get total cost grouped by provider."""
        costs: Dict[str, float] = defaultdict(float)
        for entry in self._entries:
            costs[entry.provider] += entry.cost_usd
        return dict(costs)
    
    def get_cost_by_model(self) -> Dict[str, float]:
        """Get total cost grouped by model."""
        costs: Dict[str, float] = defaultdict(float)
        for entry in self._entries:
            costs[entry.model] += entry.cost_usd
        return dict(costs)
    
    def get_cost_by_group(self) -> Dict[str, float]:
        """Get total cost grouped by custom group tag."""
        costs: Dict[str, float] = defaultdict(float)
        for entry in self._entries:
            if entry.group:
                costs[entry.group] += entry.cost_usd
        return dict(costs)
    
    def get_tokens_by_provider(self) -> Dict[str, int]:
        """Get total tokens grouped by provider."""
        tokens: Dict[str, int] = defaultdict(int)
        for entry in self._entries:
            tokens[entry.provider] += entry.total_tokens
        return dict(tokens)
    
    def get_cache_stats(self) -> Dict[str, any]:
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
    
    def set_budget(self, limit: float, alert_threshold: Optional[float] = None) -> None:
        """
        Set budget limit and optional alert threshold.
        
        Args:
            limit: Maximum budget in USD
            alert_threshold: Alert when cost reaches this threshold (default: 80% of limit)
        """
        self._budget_limit = limit
        self._alert_threshold = alert_threshold or (limit * 0.8)
    
    def get_budget_status(self) -> Dict[str, any]:
        """
        Get current budget status.
        
        Returns:
            Dictionary with budget information
        """
        if self._budget_limit is None:
            return {
                "budget_set": False,
                "total_cost": self._total_cost,
            }
        
        remaining = self._budget_limit - self._total_cost
        percent_used = (self._total_cost / self._budget_limit) * 100
        
        return {
            "budget_set": True,
            "budget_limit": self._budget_limit,
            "total_cost": self._total_cost,
            "remaining": max(0, remaining),
            "percent_used": round(percent_used, 2),
            "over_budget": self._total_cost > self._budget_limit,
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
    
    def _trigger_alert(self, current_cost: float, threshold: float) -> None:
        """
        Trigger budget alert (can be overridden for custom behavior).
        
        Args:
            current_cost: Current total cost
            threshold: Alert threshold that was exceeded
        """
        # Default implementation: print warning
        # Override this method for custom alert behavior (email, webhook, etc.)
        print(f"⚠️  Budget Alert: Current cost ${current_cost:.4f} exceeds threshold ${threshold:.4f}")
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get comprehensive summary of tracked costs.
        
        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_cost": self._total_cost,
            "total_tokens": self.get_total_tokens(),
            "total_calls": self.get_call_count(),
            "cost_by_provider": self.get_cost_by_provider(),
            "cost_by_model": self.get_cost_by_model(),
            "tokens_by_provider": self.get_tokens_by_provider(),
            "cache_stats": self.get_cache_stats(),
            "budget_status": self.get_budget_status(),
        }
