"""Unit tests for async operations in LLMClient and caching decorator."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.caching import ResponseCache, cache_response
from stratifyai.client import LLMClient
from stratifyai.models import ChatRequest, ChatResponse, Message, Usage


def create_mock_response(content: str = "Hello!", model: str = "gpt-4.1-mini") -> dict:
    """Create a mock OpenAI response dictionary."""
    return {
        "id": "test-123",
        "model": model,
        "created": 1234567890,
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def create_chat_response(
    content: str = "Hello!",
    model: str = "gpt-4.1-mini",
    cost: float = 0.001,
) -> ChatResponse:
    """Create a ChatResponse for testing."""
    return ChatResponse(
        id="test-123",
        model=model,
        content=content,
        finish_reason="stop",
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=cost,
        ),
        provider="openai",
        created_at=datetime.now(),
        raw_response={},
    )


class TestAsyncChatCompletion:
    """Tests for LLMClient.chat async method."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_async_completion(self, mock_openai):
        """Verify that LLMClient.chat correctly performs an asynchronous chat completion."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model_dump.return_value = create_mock_response("Async response!")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute async chat
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(model="gpt-4.1-mini", messages=messages)

        # Verify async execution
        assert response.content == "Async response!"
        assert response.model == "gpt-4.1-mini"
        mock_client.chat.completions.create.assert_awaited_once()

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_async_is_non_blocking(self, mock_openai):
        """Verify that multiple async chat calls can run concurrently."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        call_order = []

        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.01)
            call_order.append(len(call_order) + 1)
            mock_resp = MagicMock()
            mock_resp.model_dump.return_value = create_mock_response(f"Response {len(call_order)}")
            return mock_resp

        mock_client.chat.completions.create = AsyncMock(side_effect=delayed_response)

        client = LLMClient(provider="openai", api_key="test-key")
        messages = [Message(role="user", content="Hello")]

        # Run multiple async calls concurrently
        tasks = [
            client.chat(model="gpt-4.1-mini", messages=messages),
            client.chat(model="gpt-4.1-mini", messages=messages),
        ]
        responses = await asyncio.gather(*tasks)

        # Both calls should complete
        assert len(responses) == 2
        assert mock_client.chat.completions.create.await_count == 2


class TestSyncChatWrapper:
    """Tests for LLMClient.chat_sync synchronous wrapper."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_chat_sync_wraps_async(self, mock_openai):
        """Verify that LLMClient.chat_sync correctly performs a synchronous chat completion."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model_dump.return_value = create_mock_response("Sync response!")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute sync chat
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        response = client.chat_sync(model="gpt-4.1-mini", messages=messages)

        # Verify synchronous execution returns expected result
        assert response.content == "Sync response!"
        assert response.model == "gpt-4.1-mini"
        mock_client.chat.completions.create.assert_called_once()

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_chat_completion_sync_wraps_async(self, mock_openai):
        """Verify that LLMClient.chat_completion_sync correctly wraps async call."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model_dump.return_value = create_mock_response("Completion sync!")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute sync chat_completion
        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
        )
        response = client.chat_completion_sync(request)

        # Verify synchronous execution
        assert response.content == "Completion sync!"
        mock_client.chat.completions.create.assert_called_once()


class TestStreamingAsyncIterator:
    """Tests for LLMClient.chat_completion_stream async iterator."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_yields_async_iterator(self, mock_openai):
        """Verify that LLMClient.chat_completion_stream correctly yields an async iterator."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Create mock streaming chunks
        chunks_data = [
            {"id": "test", "model": "gpt-4.1-mini", "created": 1234567890,
             "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
            {"id": "test", "model": "gpt-4.1-mini", "created": 1234567890,
             "choices": [{"delta": {"content": " World"}, "finish_reason": None}]},
            {"id": "test", "model": "gpt-4.1-mini", "created": 1234567890,
             "choices": [{"delta": {"content": "!"}, "finish_reason": "stop"}]},
        ]

        mock_chunks = []
        for data in chunks_data:
            chunk = MagicMock()
            chunk.model_dump.return_value = data
            chunk.choices = [MagicMock(delta=MagicMock(content=data["choices"][0]["delta"].get("content", "")))]
            mock_chunks.append(chunk)

        async def async_chunk_iter():
            for chunk in mock_chunks:
                yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=async_chunk_iter())

        # Execute streaming
        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            stream=True,
        )
        stream = await client.chat_completion_stream(request)

        # Collect streamed chunks
        collected_chunks = []
        async for chunk in stream:
            collected_chunks.append(chunk)

        # Verify async iterator behavior
        assert len(collected_chunks) == 3
        assert collected_chunks[0].content == "Hello"
        assert collected_chunks[1].content == " World"
        assert collected_chunks[2].content == "!"

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_streaming_via_chat_method(self, mock_openai):
        """Verify streaming works via the chat() method with stream=True."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_chunk = MagicMock()
        mock_chunk.model_dump.return_value = {
            "id": "test", "model": "gpt-4.1-mini", "created": 1234567890,
            "choices": [{"delta": {"content": "Streamed"}, "finish_reason": "stop"}],
        }
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="Streamed"))]

        async def async_iter():
            yield mock_chunk

        mock_client.chat.completions.create = AsyncMock(return_value=async_iter())

        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        stream = await client.chat(model="gpt-4.1-mini", messages=messages, stream=True)

        # Verify returns async iterator
        chunks = [chunk async for chunk in stream]
        assert len(chunks) == 1
        assert chunks[0].content == "Streamed"


class TestLatencyTracking:
    """Tests for ChatResponse.latency_ms tracking."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_latency_ms_populated_after_chat_completion(self, mock_openai):
        """Verify that ChatResponse.latency_ms is accurately populated after async completion."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            mock_resp = MagicMock()
            mock_resp.model_dump.return_value = create_mock_response()
            return mock_resp

        mock_client.chat.completions.create = AsyncMock(side_effect=delayed_response)

        # Execute
        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
        )
        response = await client.chat_completion(request)

        # Verify latency_ms is populated and reasonable
        assert response.latency_ms is not None
        assert response.latency_ms >= 50  # At least 50ms (our simulated delay)
        assert response.latency_ms < 500  # Sanity check - should not be too long

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_latency_ms_reflects_actual_execution_time(self, mock_openai):
        """Verify latency_ms accurately reflects the actual execution time."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        delay_ms = 100

        async def timed_response(*args, **kwargs):
            await asyncio.sleep(delay_ms / 1000)
            mock_resp = MagicMock()
            mock_resp.model_dump.return_value = create_mock_response()
            return mock_resp

        mock_client.chat.completions.create = AsyncMock(side_effect=timed_response)

        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
        )
        response = await client.chat_completion(request)

        # Latency should be close to our delay (with some tolerance)
        assert response.latency_ms >= delay_ms
        assert response.latency_ms < delay_ms + 50  # Allow 50ms tolerance

    def test_latency_ms_field_exists_in_chat_response(self):
        """Verify ChatResponse model has latency_ms field."""
        response = ChatResponse(
            id="test",
            model="gpt-4.1-mini",
            content="Hello",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            latency_ms=123.45,
        )
        assert response.latency_ms == 123.45


class TestAsyncCacheDecorator:
    """Tests for @cache_response decorator with async functions."""

    @pytest.mark.asyncio
    async def test_cache_response_caches_async_function(self):
        """Verify @cache_response correctly caches responses for async functions."""
        cache = ResponseCache()
        call_count = 0

        @cache_response(cache_instance=cache)
        async def mock_llm_call(**kwargs):
            nonlocal call_count
            call_count += 1
            return create_chat_response(content=f"Response {call_count}")

        # First call - should execute function
        response1 = await mock_llm_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )
        assert call_count == 1
        assert response1.content == "Response 1"

        # Second call with same params - should return cached
        response2 = await mock_llm_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )
        assert call_count == 1  # Function not called again
        assert response2.content == "Response 1"  # Same cached response

    @pytest.mark.asyncio
    async def test_cache_response_retrieves_cached_value(self):
        """Verify @cache_response retrieves cached responses without re-execution."""
        cache = ResponseCache()
        execution_times = []

        @cache_response(cache_instance=cache)
        async def slow_llm_call(**kwargs):
            await asyncio.sleep(0.05)  # Simulate slow API call
            execution_times.append(asyncio.get_event_loop().time())
            return create_chat_response()

        # First call - slow
        await slow_llm_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Test")],
            temperature=0.5,
        )

        # Subsequent calls - should be instant from cache
        for _ in range(5):
            await slow_llm_call(
                model="gpt-4.1-mini",
                messages=[Message(role="user", content="Test")],
                temperature=0.5,
            )

        # Only one actual execution
        assert len(execution_times) == 1

    @pytest.mark.asyncio
    async def test_cache_miss_on_different_parameters(self):
        """Verify cache miss when parameters differ."""
        cache = ResponseCache()
        call_count = 0

        @cache_response(cache_instance=cache)
        async def mock_call(**kwargs):
            nonlocal call_count
            call_count += 1
            return create_chat_response(content=f"Response for temp={kwargs['temperature']}")

        # Different temperatures should result in cache misses
        await mock_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.5,
        )
        await mock_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )
        await mock_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.9,
        )

        # Each unique temperature should trigger a new call
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_cache_decorator_preserves_async_behavior(self):
        """Verify decorated function remains properly async."""
        cache = ResponseCache()

        @cache_response(cache_instance=cache)
        async def async_fn(**kwargs):
            await asyncio.sleep(0.01)
            return create_chat_response()

        # Should be awaitable
        import inspect
        assert inspect.iscoroutinefunction(async_fn)

        # Should work with asyncio.gather
        results = await asyncio.gather(
            async_fn(model="gpt-4.1-mini", messages=[Message(role="user", content="A")], temperature=0.1),
            async_fn(model="gpt-4.1-mini", messages=[Message(role="user", content="B")], temperature=0.2),
        )
        assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
