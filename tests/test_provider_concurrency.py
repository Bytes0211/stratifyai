"""Tests for provider concurrency limiting."""

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from stratifyai.client import LLMClient
from stratifyai.exceptions import InvalidProviderError
from stratifyai.models import ChatRequest, ChatResponse, Message, Usage
from stratifyai.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing concurrency."""

    def __init__(self):
        """Initialize mock provider without parent init."""
        self._concurrency_semaphore = None
        self._concurrency_limit = None
        self.call_count = 0
        self.concurrent_calls = 0
        self.max_concurrent_observed = 0
        self._client = MagicMock()
        # Lock protects concurrency tracking counters so the
        # increment-then-max sequence is atomic within the event loop.
        self._tracking_lock = asyncio.Lock()

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mock"

    def get_supported_models(self) -> list[str]:
        """Return supported models."""
        return ["mock-model"]

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute chat completion with concurrency tracking."""
        sem = await self._acquire_concurrency_slot()
        try:
            async with self._tracking_lock:
                self.call_count += 1
                self.concurrent_calls += 1
                self.max_concurrent_observed = max(
                    self.max_concurrent_observed, self.concurrent_calls
                )

            # Simulate some work
            await asyncio.sleep(0.05)

            async with self._tracking_lock:
                self.concurrent_calls -= 1

            return ChatResponse(
                id="test-id",
                model="mock-model",
                content="Mock response",
                finish_reason="stop",
                usage=Usage(
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    cost_usd=0.001,
                ),
                provider="mock",
                created_at=None,
                raw_response={},
            )
        finally:
            self._release_concurrency_slot(sem)

    async def chat_completion_stream(self, request: ChatRequest):
        """Not implemented for tests."""
        pass

    def _initialize_client(self) -> None:
        """Initialize client."""
        pass

    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """Normalize response."""
        pass

    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """Calculate cost."""
        return 0.001


class TestProviderConcurrencyLimit:
    """Test suite for provider concurrency limiting."""

    def test_set_concurrency_limit_stores_limit(self):
        """Test that setting a limit stores the value for lazy semaphore creation."""
        provider = MockProvider()
        provider.set_concurrency_limit(5)

        assert provider.get_concurrency_limit() == 5
        # Semaphore is created lazily on first async acquire, not eagerly
        assert provider._concurrency_semaphore is None

    def test_set_concurrency_limit_none_clears_semaphore(self):
        """Test that setting None removes the limit."""
        provider = MockProvider()
        provider.set_concurrency_limit(5)
        provider.set_concurrency_limit(None)

        assert provider.get_concurrency_limit() is None
        assert provider._concurrency_semaphore is None

    def test_get_concurrency_limit_default_none(self):
        """Test that default limit is None."""
        provider = MockProvider()
        assert provider.get_concurrency_limit() is None

    @pytest.mark.asyncio
    async def test_concurrent_calls_respected_limit(self):
        """Test that concurrent calls respect the limit."""
        provider = MockProvider()
        provider.set_concurrency_limit(2)

        messages = [Message(role="user", content="Test")]

        # Create 5 concurrent tasks
        tasks = [
            provider.chat_completion(ChatRequest(model="mock-model", messages=messages))
            for _ in range(5)
        ]

        # Run them concurrently
        await asyncio.gather(*tasks)

        # Check that max concurrent was never more than limit
        assert provider.max_concurrent_observed <= 2
        # Check that all calls completed
        assert provider.call_count == 5

    @pytest.mark.asyncio
    async def test_semaphore_slot_release_on_exception(self):
        """Test that slots are released even if exception occurs."""
        provider = MockProvider()
        provider.set_concurrency_limit(1)

        async def failing_call():
            """Call that raises exception."""
            sem = await provider._acquire_concurrency_slot()
            try:
                raise ValueError("Test error")
            finally:
                provider._release_concurrency_slot(sem)

        # First call raises
        with pytest.raises(ValueError):
            await failing_call()

        # Check that semaphore still has a slot available
        # We can acquire it without waiting
        start = time.time()
        sem = await provider._acquire_concurrency_slot()
        elapsed = time.time() - start

        # Should be fast (not blocked waiting for timeout)
        assert elapsed < 1.0
        provider._release_concurrency_slot(sem)

    @pytest.mark.asyncio
    async def test_no_limit_allows_unlimited_concurrent(self):
        """Test that no limit allows unlimited concurrent requests."""
        provider = MockProvider()
        # Don't set any limit

        messages = [Message(role="user", content="Test")]

        # Create many concurrent tasks
        tasks = [
            provider.chat_completion(ChatRequest(model="mock-model", messages=messages))
            for _ in range(20)
        ]

        # Run them concurrently
        start = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Without a limit all 20 tasks should run concurrently (~50ms total).
        # Use a generous threshold to avoid CI flakiness.
        assert elapsed < 5.0
        assert provider.call_count == 20
        # Without a limit, we should see some concurrency (at least 2)
        assert provider.max_concurrent_observed >= 2


class TestLLMClientConcurrencyMethods:
    """Test LLMClient concurrency limit API."""

    def test_set_provider_concurrency_limit_invalid_provider(self):
        """Test that invalid provider raises error."""
        client = LLMClient()

        with pytest.raises(InvalidProviderError):
            client.set_provider_concurrency_limit("invalid-provider", 5)

    def test_get_provider_concurrency_limit_invalid_provider(self):
        """Test getting limit for invalid provider."""
        client = LLMClient()

        with pytest.raises(InvalidProviderError):
            client.get_provider_concurrency_limit("invalid-provider")


class TestConcurrencyWithQueueing:
    """Test that concurrency limiting provides fair queueing."""

    @pytest.mark.asyncio
    async def test_sequential_queueing_behavior(self):
        """Test that with limit=1, tasks run sequentially and all complete."""
        provider = MockProvider()
        provider.set_concurrency_limit(1)

        completion_order = []

        async def track_completion(task_id: int):
            """Call and track when it completes."""
            messages = [Message(role="user", content=f"Task {task_id}")]
            await provider.chat_completion(
                ChatRequest(model="mock-model", messages=messages)
            )
            completion_order.append(task_id)

        # Create 5 tasks
        tasks = [track_completion(i) for i in range(5)]

        # Run concurrently
        await asyncio.gather(*tasks)

        # All tasks must complete
        assert len(completion_order) == 5
        assert set(completion_order) == {0, 1, 2, 3, 4}
        assert provider.call_count == 5
        # With limit=1, max concurrent must be exactly 1
        assert provider.max_concurrent_observed == 1

    @pytest.mark.asyncio
    async def test_progressive_increase_parallelism(self):
        """Test that parallelism increases as limit increases."""
        messages = [Message(role="user", content="Test")]

        results = {}

        for limit in [1, 2, 4]:
            provider = MockProvider()
            provider.set_concurrency_limit(limit)

            tasks = [
                provider.chat_completion(
                    ChatRequest(model="mock-model", messages=messages)
                )
                for _ in range(8)
            ]

            start = time.time()
            await asyncio.gather(*tasks)
            elapsed = time.time() - start

            results[limit] = elapsed

        # Higher limits should generally complete faster.
        # Use a generous margin — limit=4 should be noticeably faster than limit=1
        assert results[4] < results[1] * 0.95, (
            f"limit=4 ({results[4]:.3f}s) should be faster than limit=1 ({results[1]:.3f}s)"
        )
