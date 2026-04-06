"""Additional coverage for CostTracker retention and summaries."""

from stratifyai.cost_tracker import CostTracker


class TestCostTrackerRetention:
    def test_max_entries_trims_history_but_preserves_totals(self):
        tracker = CostTracker(max_entries=2)

        tracker.add_entry("openai", "gpt-4o-mini", 10, 5, 15, 0.10, "req-1")
        tracker.add_entry("anthropic", "claude", 20, 10, 30, 0.20, "req-2")
        tracker.add_entry("openai", "gpt-4o-mini", 5, 5, 10, 0.30, "req-3")

        entries = tracker.get_entries()
        assert tracker.get_call_count() == 3
        assert len(entries) == 2
        assert [entry.request_id for entry in entries] == ["req-2", "req-3"]
        assert tracker.get_total_cost() == 0.60
        assert tracker.get_total_tokens() == 55

    def test_summary_includes_budget_and_cache_statistics(self):
        tracker = CostTracker(max_entries=5)
        tracker.set_budget(1.00, alert_threshold=0.50)
        tracker.add_entry(
            "openai",
            "gpt-4o-mini",
            100,
            20,
            120,
            0.55,
            "req-budget",
            cached_tokens=30,
            cache_creation_tokens=10,
            cache_read_tokens=30,
            group="demo",
        )

        summary = tracker.get_summary()
        budget = summary["budget_status"]
        cache_stats = summary["cache_stats"]

        assert summary["total_calls"] == 1
        assert summary["cost_by_provider"]["openai"] == 0.55
        assert summary["cost_by_model"]["gpt-4o-mini"] == 0.55
        assert summary["cost_by_group"]["demo"] == 0.55
        assert cache_stats["total_cache_read_tokens"] == 30
        assert budget["percent_used"] == 55.0
        assert budget["over_budget"] is False
