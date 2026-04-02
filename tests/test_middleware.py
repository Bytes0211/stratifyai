"""Tests for TrackedLLMClient middleware."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.cost_tracker import CostTracker
from stratifyai.exceptions import BudgetExceededError
from stratifyai.middleware import TrackedLLMClient
from stratifyai.models import ChatResponse, Message, Usage


def _make_response(**overrides) -> ChatResponse:
    defaults = {
        "id": "test-resp-1",
        "model": "gpt-4.1-mini",
        "content": "Hello!",
        "finish_reason": "stop",
        "usage": Usage(
            prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.001
        ),
        "provider": "openai",
        "created_at": datetime.now(),
        "raw_response": {},
    }
    defaults.update(overrides)
    return ChatResponse(**defaults)


class TestTrackedLLMClient:
    """Tests for the TrackedLLMClient wrapper."""

    @pytest.mark.asyncio
    async def test_chat_completion_stream_tracks_first_and_total_latency(self):
        """Streaming telemetry should capture first-token and total latency."""
        mock_client = MagicMock()
        mock_client.provider_name = "openai"

        async def stream():
            yield _make_response(content="Hello")
            yield _make_response(content=" world")

        mock_client.chat_completion_stream.return_value = stream()

        tracker = CostTracker()
        tracked = TrackedLLMClient(client=mock_client, cost_tracker=tracker)

        from stratifyai.models import ChatRequest

        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
        )

        with patch("stratifyai.middleware.time.perf_counter") as mock_perf:
            mock_perf.side_effect = [10.0, 10.05, 10.2]
            chunks = [chunk async for chunk in tracked.chat_completion_stream(request)]

        assert len(chunks) == 2
        metrics = tracked.get_last_stream_metrics()
        assert metrics["chunk_count"] == 2
        assert metrics["first_token_latency_ms"] == pytest.approx(50.0)
        assert metrics["total_latency_ms"] == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_chat_completion_tracks_cost(self):
        """Middleware should automatically add a cost entry."""
        mock_client = MagicMock()
        mock_client.provider_name = "openai"
        mock_client.chat_completion = AsyncMock(return_value=_make_response())

        tracker = CostTracker()
        tracked = TrackedLLMClient(client=mock_client, cost_tracker=tracker)

        from stratifyai.models import ChatRequest

        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
        )
        response = await tracked.chat_completion(request)

        assert response.content == "Hello!"
        assert response.latency_ms is not None and response.latency_ms > 0
        assert tracker.get_call_count() == 1
        assert tracker.get_total_cost() == pytest.approx(0.001)

    @pytest.mark.asyncio
    async def test_chat_tracks_cost(self):
        """The chat() convenience method should also track."""
        mock_client = MagicMock()
        mock_client.provider_name = "openai"
        mock_client.chat = AsyncMock(return_value=_make_response())

        tracker = CostTracker()
        tracked = TrackedLLMClient(client=mock_client, cost_tracker=tracker)

        messages = [Message(role="user", content="Hi")]
        response = await tracked.chat(model="gpt-4.1-mini", messages=messages)

        assert tracker.get_call_count() == 1
        assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_budget_exceeded_raises(self):
        """Should raise BudgetExceededError before making the call."""
        mock_client = MagicMock()
        mock_client.provider_name = "openai"
        mock_client.chat_completion = AsyncMock(return_value=_make_response())

        tracker = CostTracker()
        tracker.set_budget(limit=0.001)
        # Simulate prior spend that exceeds budget
        tracker.add_entry(
            provider="openai",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.01,
            request_id="prior",
        )

        tracked = TrackedLLMClient(client=mock_client, cost_tracker=tracker)

        from stratifyai.models import ChatRequest

        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
        )

        with pytest.raises(BudgetExceededError):
            await tracked.chat_completion(request)

        # The underlying client should NOT have been called
        mock_client.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_calls_accumulate(self):
        """Multiple calls should accumulate in the tracker."""
        mock_client = MagicMock()
        mock_client.provider_name = "openai"
        mock_client.chat = AsyncMock(return_value=_make_response())

        tracker = CostTracker()
        tracked = TrackedLLMClient(client=mock_client, cost_tracker=tracker)

        messages = [Message(role="user", content="Hi")]
        await tracked.chat(model="gpt-4.1-mini", messages=messages)
        await tracked.chat(model="gpt-4.1-mini", messages=messages)
        await tracked.chat(model="gpt-4.1-mini", messages=messages)

        assert tracker.get_call_count() == 3
        assert tracker.get_total_cost() == pytest.approx(0.003)
