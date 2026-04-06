"""Targeted tests to boost code coverage across low-coverage modules.

Covers:
- stratifyai/providers/openai_compatible.py
- stratifyai/embeddings.py
- stratifyai/logging_config.py
- stratifyai/vectordb.py
- stratifyai/catalog_manager.py
- stratifyai/utils/reasoning_detector.py
- stratifyai/utils/token_counter.py
"""

import io
import json
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.exceptions import (
    AuthenticationError,
    InsufficientBalanceError,
    InvalidModelError,
    LLMAbstractionError,
    ProviderAPIError,
)
from stratifyai.models import ChatRequest, ChatResponse, Message

# ---------------------------------------------------------------------------
# Helpers: concrete OpenAICompatibleProvider subclass for testing
# ---------------------------------------------------------------------------

FAKE_CATALOG = {
    "test-model": {
        "cost_input": 1.0,
        "cost_output": 2.0,
        "supports_caching": True,
        "cost_cache_write": 1.5,
        "cost_cache_read": 0.5,
    },
    "basic-model": {
        "cost_input": 0.5,
        "cost_output": 1.0,
    },
}


def _make_provider(catalog=None):
    """Create an OpenAICompatibleProvider subclass instance with mocked client."""
    from stratifyai.providers.openai_compatible import OpenAICompatibleProvider

    class _TestProvider(OpenAICompatibleProvider):
        @property
        def provider_name(self) -> str:
            return "test_provider"

    with patch("stratifyai.providers.openai_compatible.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        provider = _TestProvider(
            api_key="test-key",
            base_url="https://api.test.com",
            model_catalog=catalog or FAKE_CATALOG,
        )
    return provider


def _raw_response(model="test-model", content="Hello", **overrides):
    """Build a raw OpenAI-compatible response dict."""
    resp = {
        "id": "chatcmpl-test",
        "model": model,
        "created": int(datetime.now().timestamp()),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "prompt_tokens_details": {
                "cached_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    resp.update(overrides)
    return resp


# ===================================================================
# OpenAICompatibleProvider tests
# ===================================================================


class TestOpenAICompatibleProviderInit:
    """Initialization and client setup tests."""

    def test_init_success(self):
        provider = _make_provider()
        assert provider.provider_name == "test_provider"
        assert provider.base_url == "https://api.test.com"

    def test_init_client_failure(self):
        """Lines 57-58: client init exception wraps in ProviderAPIError."""
        from stratifyai.providers.openai_compatible import OpenAICompatibleProvider

        class _TestProvider(OpenAICompatibleProvider):
            @property
            def provider_name(self) -> str:
                return "test_provider"

        with patch(
            "stratifyai.providers.openai_compatible.AsyncOpenAI",
            side_effect=RuntimeError("bad config"),
        ):
            with pytest.raises(ProviderAPIError, match="Failed to initialize"):
                _TestProvider(
                    api_key="key",
                    base_url="https://x.com",
                    model_catalog={},
                )

    def test_supports_caching_true(self):
        """Line 69-70: supports_caching returns True when catalog says so."""
        provider = _make_provider()
        assert provider.supports_caching("test-model") is True

    def test_supports_caching_false(self):
        provider = _make_provider()
        assert provider.supports_caching("basic-model") is False

    def test_supports_caching_unknown_model(self):
        provider = _make_provider()
        assert provider.supports_caching("nonexistent") is False


class TestOpenAICompatibleChatCompletion:
    """chat_completion() tests covering lines 89-218."""

    async def test_invalid_model(self):
        """Line 89: InvalidModelError for unsupported model."""
        provider = _make_provider()
        request = ChatRequest(
            model="unknown-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(InvalidModelError):
            await provider.chat_completion(request)

    async def test_successful_completion(self):
        """Happy path covering lines 99-175."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = _raw_response()
        provider._client.chat.completions.create = AsyncMock(return_value=mock_resp)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")],
            temperature=0.5,
        )
        result = await provider.chat_completion(request)
        assert isinstance(result, ChatResponse)
        assert result.content == "Hello"
        assert result.provider == "test_provider"

    async def test_vision_message(self):
        """Lines 105-124: vision message with [IMAGE:...] marker."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = _raw_response()
        provider._client.chat.completions.create = AsyncMock(return_value=mock_resp)

        vision_content = "Describe this [IMAGE:image/png]\nYWJj"
        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content=vision_content)],
        )
        result = await provider.chat_completion(request)
        assert isinstance(result, ChatResponse)

        # Verify the call included image_url content parts
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        msgs = call_kwargs["messages"]
        assert isinstance(msgs[0]["content"], list)
        assert any(p["type"] == "image_url" for p in msgs[0]["content"])

    async def test_cache_control_on_message(self):
        """Line 133: cache_control added when present and model supports caching."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = _raw_response()
        provider._client.chat.completions.create = AsyncMock(return_value=mock_resp)

        request = ChatRequest(
            model="test-model",
            messages=[
                Message(
                    role="user",
                    content="hello",
                    cache_control={"type": "ephemeral"},
                )
            ],
        )
        await provider.chat_completion(request)
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"][0]["cache_control"] == {"type": "ephemeral"}

    async def test_optional_params(self):
        """Lines 155-167: frequency_penalty, presence_penalty, stop, max_tokens, extra_params."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = _raw_response()
        provider._client.chat.completions.create = AsyncMock(return_value=mock_resp)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            frequency_penalty=0.5,
            presence_penalty=0.3,
            max_tokens=100,
            stop=["END"],
            extra_params={"seed": 42},
        )
        await provider.chat_completion(request)
        call_kwargs = provider._client.chat.completions.create.call_args[1]
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["stop"] == ["END"]
        assert call_kwargs["seed"] == 42

    async def test_insufficient_balance_error(self):
        """Line 180: InsufficientBalanceError on balance-related API error."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_resp.headers = {}
        err = APIStatusError(
            message="Insufficient balance in your account",
            response=mock_resp,
            body=None,
        )
        provider._client.chat.completions.create = AsyncMock(side_effect=err)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(InsufficientBalanceError):
            await provider.chat_completion(request)

    async def test_auth_error(self):
        """Line 186: AuthenticationError on invalid_api_key."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        err = APIStatusError(
            message="invalid_api_key",
            response=mock_resp,
            body=None,
        )
        provider._client.chat.completions.create = AsyncMock(side_effect=err)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(AuthenticationError):
            await provider.chat_completion(request)

    async def test_vision_error_from_api(self):
        """Line 193: Vision-related ProviderAPIError from APIError."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {}
        err = APIStatusError(
            message="image_url is not supported by this model",
            response=mock_resp,
            body=None,
        )
        provider._client.chat.completions.create = AsyncMock(side_effect=err)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            await provider.chat_completion(request)

    async def test_generic_api_error(self):
        """Lines 199-202: generic APIStatusError wraps in ProviderAPIError."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}
        err = APIStatusError(
            message="Internal server error",
            response=mock_resp,
            body=None,
        )
        provider._client.chat.completions.create = AsyncMock(side_effect=err)

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(ProviderAPIError, match="Chat completion failed"):
            await provider.chat_completion(request)

    async def test_generic_exception(self):
        """Lines 203-218: generic Exception wraps in ProviderAPIError."""
        provider = _make_provider()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("Something broke")
        )

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(ProviderAPIError, match="Chat completion failed"):
            await provider.chat_completion(request)

    async def test_generic_exception_with_image_error(self):
        """Lines 203-215: generic Exception with image-related text."""
        provider = _make_provider()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("image is not supported for this model")
        )

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            await provider.chat_completion(request)


class TestOpenAICompatibleStreaming:
    """chat_completion_stream() tests covering lines 238-352."""

    async def test_stream_invalid_model(self):
        """Line 240-241: InvalidModelError in stream."""
        provider = _make_provider()
        request = ChatRequest(
            model="unknown-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(InvalidModelError):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_success(self):
        """Lines 302-307: successful streaming."""
        provider = _make_provider()

        chunk_obj = MagicMock()
        chunk_obj.choices = [MagicMock()]
        chunk_obj.choices[0].delta.content = "Hello"
        chunk_obj.model_dump.return_value = {
            "id": "chunk-1",
            "model": "test-model",
            "created": int(datetime.now().timestamp()),
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None,
                }
            ],
        }

        async def fake_stream():
            yield chunk_obj

        mock_create = AsyncMock(return_value=fake_stream())
        provider._client.chat.completions.create = mock_create

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(request):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].content == "Hello"

    async def test_stream_insufficient_balance(self):
        """Line 311-312: InsufficientBalanceError in stream."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_resp.headers = {}

        async def raise_err():
            raise APIStatusError(
                message="insufficient balance",
                response=mock_resp,
                body=None,
            )
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(InsufficientBalanceError):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_auth_error(self):
        """Lines 313-318: AuthenticationError in stream."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}

        async def raise_err():
            raise APIStatusError(
                message="unauthorized",
                response=mock_resp,
                body=None,
            )
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(AuthenticationError):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_vision_error(self):
        """Lines 320-329: Vision error in stream."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {}

        async def raise_err():
            raise APIStatusError(
                message="image_url is not supported",
                response=mock_resp,
                body=None,
            )
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_generic_api_error(self):
        """Lines 330-334: generic APIStatusError in stream."""
        from openai import APIStatusError

        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}

        async def raise_err():
            raise APIStatusError(
                message="server error",
                response=mock_resp,
                body=None,
            )
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(ProviderAPIError, match="Streaming chat completion failed"):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_generic_exception(self):
        """Lines 335-350: generic Exception in stream."""
        provider = _make_provider()

        async def raise_err():
            raise RuntimeError("boom")
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(ProviderAPIError, match="Streaming chat completion failed"):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_generic_exception_vision(self):
        """Lines 338-347: generic Exception with image error text in stream."""
        provider = _make_provider()

        async def raise_err():
            raise RuntimeError("image is not supported")
            yield  # noqa: F841

        provider._client.chat.completions.create = AsyncMock(return_value=raise_err())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="hi")],
            stream=True,
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            async for _ in provider.chat_completion_stream(request):
                pass

    async def test_stream_with_vision_message(self):
        """Lines 255-277: vision content in streaming request."""
        provider = _make_provider()

        chunk_obj = MagicMock()
        chunk_obj.choices = [MagicMock()]
        chunk_obj.choices[0].delta.content = "I see"
        chunk_obj.model_dump.return_value = {
            "id": "chunk-v",
            "model": "test-model",
            "created": int(datetime.now().timestamp()),
            "choices": [
                {"index": 0, "delta": {"content": "I see"}, "finish_reason": None}
            ],
        }

        async def fake_stream():
            yield chunk_obj

        provider._client.chat.completions.create = AsyncMock(return_value=fake_stream())

        request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="[IMAGE:image/jpeg]\nYWJj")],
            stream=True,
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(request):
            chunks.append(chunk)
        assert len(chunks) == 1


class TestOpenAICompatibleNormalization:
    """_normalize_response and _normalize_stream_chunk tests covering lines 391, 414-417."""

    def test_normalize_response_with_cache_breakdown(self):
        """Line 391: cost_breakdown populated when cache tokens present."""
        provider = _make_provider()
        raw = _raw_response()
        raw["usage"]["prompt_tokens_details"] = {
            "cached_tokens": 5,
            "cache_creation_input_tokens": 3,
        }
        result = provider._normalize_response(raw)
        assert result.usage.cost_breakdown is not None
        assert "cache_cost" in result.usage.cost_breakdown

    def test_normalize_stream_chunk(self):
        """Lines 414-417: stream chunk normalization."""
        provider = _make_provider()
        chunk = {
            "id": "chunk-1",
            "model": "test-model",
            "created": int(datetime.now().timestamp()),
            "choices": [
                {"index": 0, "delta": {"content": "hi"}, "finish_reason": None}
            ],
        }
        result = provider._normalize_stream_chunk(chunk)
        assert result.content == "hi"
        assert result.provider == "test_provider"

    def test_normalize_stream_chunk_no_created(self):
        """Line 417: fallback to datetime.now() when created is 0/missing."""
        provider = _make_provider()
        chunk = {
            "id": "chunk-2",
            "model": "test-model",
            "created": 0,
            "choices": [
                {"index": 0, "delta": {"content": ""}, "finish_reason": "stop"}
            ],
        }
        result = provider._normalize_stream_chunk(chunk)
        assert result.created_at is not None

    def test_calculate_cache_cost_no_caching_support(self):
        """Line 474: model without caching returns 0.0."""
        provider = _make_provider()
        assert provider._calculate_cache_cost(100, 200, "basic-model") == 0.0

    def test_calculate_cache_cost_with_caching(self):
        """Cache cost calculation for caching-enabled model."""
        provider = _make_provider()
        cost = provider._calculate_cache_cost(1_000_000, 1_000_000, "test-model")
        assert cost == pytest.approx(2.0)  # 1.5 write + 0.5 read


# ===================================================================
# Embeddings tests
# ===================================================================


class TestEmbeddingProvider:
    """Tests for embeddings.py covering lines 60-85, 123-181, 200-201, 215-241."""

    def test_openai_embedding_provider_no_key(self):
        """Lines 123-130: AuthenticationError when no API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                from stratifyai.embeddings import OpenAIEmbeddingProvider

                OpenAIEmbeddingProvider()

    def test_openai_embedding_provider_with_key(self):
        """Line 130: successful init with API key."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            assert provider.api_key == "test-key"

    async def test_generate_embeddings_unknown_model(self):
        """Lines 150-154: ValueError for unknown model."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            with pytest.raises(ValueError, match="Unknown OpenAI embedding model"):
                await provider.generate_embeddings(["hello"], model="bad-model")

    async def test_generate_embeddings_empty_texts(self):
        """Lines 156-157: empty texts returns empty result."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            result = await provider.generate_embeddings([])
            assert result.embeddings == []
            assert result.total_tokens == 0

    async def test_generate_embeddings_success(self):
        """Lines 159-172: successful embedding generation."""
        from stratifyai.embeddings import OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_data = MagicMock()
            mock_data.embedding = [0.1, 0.2, 0.3]
            mock_usage = MagicMock()
            mock_usage.total_tokens = 10
            mock_response = MagicMock()
            mock_response.data = [mock_data]
            mock_response.usage = mock_usage

            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            result = await provider.generate_embeddings(["hello world"])

            assert len(result.embeddings) == 1
            assert result.total_tokens == 10
            assert result.cost > 0

    async def test_generate_embeddings_auth_failure(self):
        """Lines 174-179: authentication error during API call."""
        from stratifyai.embeddings import OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.embeddings.create = AsyncMock(
                side_effect=Exception("authentication failed: invalid api key")
            )

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            with pytest.raises(AuthenticationError):
                await provider.generate_embeddings(["hello"])

    async def test_generate_embeddings_generic_failure(self):
        """Lines 180-184: generic error during API call."""
        from stratifyai.embeddings import OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.embeddings.create = AsyncMock(
                side_effect=Exception("connection timeout")
            )

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            with pytest.raises(ProviderAPIError, match="embedding request failed"):
                await provider.generate_embeddings(["hello"])

    async def test_generate_single_embedding(self):
        """Lines 200-201: single embedding convenience method."""
        from stratifyai.embeddings import OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_data = MagicMock()
            mock_data.embedding = [0.5, 0.6]
            mock_usage = MagicMock()
            mock_usage.total_tokens = 5
            mock_response = MagicMock()
            mock_response.data = [mock_data]
            mock_response.usage = mock_usage

            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            vec = await provider.generate_embedding("test")
            assert vec == [0.5, 0.6]

    def test_get_embedding_dimension_valid(self):
        """Lines 215-220: valid model dimension."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            assert provider.get_embedding_dimension("text-embedding-3-small") == 1536
            assert provider.get_embedding_dimension("text-embedding-3-large") == 3072

    def test_get_embedding_dimension_invalid(self):
        """Lines 215-219: ValueError for unknown model."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import OpenAIEmbeddingProvider

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            with pytest.raises(ValueError, match="Unknown OpenAI embedding model"):
                provider.get_embedding_dimension("bad-model")

    def test_create_embedding_provider_openai(self):
        """Lines 238-239: factory creates OpenAI provider."""
        with patch("stratifyai.embeddings.AsyncOpenAI"):
            from stratifyai.embeddings import create_embedding_provider

            provider = create_embedding_provider("openai", api_key="key")
            assert provider is not None

    def test_create_embedding_provider_unknown(self):
        """Lines 240-241: factory raises ValueError for unknown provider."""
        from stratifyai.embeddings import create_embedding_provider

        with pytest.raises(ValueError, match="Unknown embedding provider"):
            create_embedding_provider("cohere", api_key="key")

    def test_generate_embeddings_sync(self):
        """Line 78: synchronous wrapper."""
        from stratifyai.embeddings import EmbeddingResult, OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_data = MagicMock()
            mock_data.embedding = [0.1]
            mock_usage = MagicMock()
            mock_usage.total_tokens = 1
            mock_resp = MagicMock()
            mock_resp.data = [mock_data]
            mock_resp.usage = mock_usage
            mock_client.embeddings.create = AsyncMock(return_value=mock_resp)

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            result = provider.generate_embeddings_sync(["hi"])
            assert isinstance(result, EmbeddingResult)

    async def test_base_generate_embedding(self):
        """Lines 84-85: base class generate_embedding delegates to generate_embeddings."""
        from stratifyai.embeddings import OpenAIEmbeddingProvider

        with patch("stratifyai.embeddings.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            mock_data = MagicMock()
            mock_data.embedding = [0.9, 0.8]
            mock_usage = MagicMock()
            mock_usage.total_tokens = 3
            mock_resp = MagicMock()
            mock_resp.data = [mock_data]
            mock_resp.usage = mock_usage
            mock_client.embeddings.create = AsyncMock(return_value=mock_resp)

            provider = OpenAIEmbeddingProvider(api_key="test-key")
            # Call the base class method (not the overridden one)
            vec = await super(OpenAIEmbeddingProvider, provider).generate_embedding(
                "text"
            )
            assert vec == [0.9, 0.8]


# ===================================================================
# Logging config tests
# ===================================================================


class TestLoggingConfig:
    """Tests for logging_config.py covering lines 27-39, 49, 65-77."""

    def test_configure_logging_human_format(self):
        """Lines 65-77: human format configuration."""
        from stratifyai.logging_config import configure_logging

        stream = io.StringIO()
        configure_logging(format="human", level="DEBUG", stream=stream)

        logger = logging.getLogger("stratifyai")
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

    def test_configure_logging_json_format(self):
        """Lines 72-73: JSON format configuration."""
        from stratifyai.logging_config import configure_logging

        stream = io.StringIO()
        configure_logging(format="json", level="WARNING", stream=stream)

        logger = logging.getLogger("stratifyai")
        assert logger.level == logging.WARNING

    def test_configure_logging_clears_handlers(self):
        """Line 69: duplicate handler prevention."""
        from stratifyai.logging_config import configure_logging

        stream = io.StringIO()
        configure_logging(format="human", level="INFO", stream=stream)
        configure_logging(format="json", level="INFO", stream=stream)
        logger = logging.getLogger("stratifyai")
        assert len(logger.handlers) == 1

    def test_json_formatter_basic(self):
        """Lines 27-39: JSONFormatter output structure."""
        from stratifyai.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed

    def test_json_formatter_with_correlation_id(self):
        """Line 34: correlation_id in log entry."""
        from stratifyai.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "req-123"  # type: ignore[attr-defined]
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["correlation_id"] == "req-123"

    def test_json_formatter_with_exception(self):
        """Lines 35-36: exception info in log entry."""
        from stratifyai.logging_config import JSONFormatter

        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_json_formatter_with_extra_data(self):
        """Lines 37-38: extra_data in log entry."""
        from stratifyai.logging_config import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"key": "value"}  # type: ignore[attr-defined]
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["data"] == {"key": "value"}

    def test_human_formatter_init(self):
        """Line 49: HumanFormatter uses correct format string."""
        from stratifyai.logging_config import HumanFormatter

        formatter = HumanFormatter()
        assert "%(levelname)" in formatter._fmt
        assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"

    def test_configure_logging_default_stream(self):
        """Line 71: default stream is sys.stderr."""
        from stratifyai.logging_config import configure_logging

        configure_logging(format="human", level="INFO")
        logger = logging.getLogger("stratifyai")
        assert len(logger.handlers) == 1


# ===================================================================
# VectorDB tests
# ===================================================================


class TestVectorDBClient:
    """Tests for vectordb.py covering lines 14-16, 65, 74, 96-154, 174-275, 334, 354, 384-410."""

    def test_chromadb_not_available(self):
        """Lines 14-16, 65: LLMAbstractionError when ChromaDB not installed."""
        with patch("stratifyai.vectordb.CHROMADB_AVAILABLE", False):
            from stratifyai.vectordb import VectorDBClient

            mock_embedding = MagicMock()
            with pytest.raises(LLMAbstractionError, match="ChromaDB is not installed"):
                VectorDBClient(embedding_provider=mock_embedding)

    def _make_vdb_client(self):
        """Create a VectorDBClient with mocked ChromaDB."""
        mock_embedding = AsyncMock()
        with (
            patch("stratifyai.vectordb.CHROMADB_AVAILABLE", True),
            patch("stratifyai.vectordb.Settings", MagicMock()),
            patch("stratifyai.vectordb.chromadb") as mock_chromadb,
        ):
            mock_chroma_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_chroma_client

            from stratifyai.vectordb import VectorDBClient

            client = VectorDBClient(
                embedding_provider=mock_embedding,
                persist_directory="/tmp/test_chroma",
            )
            client._chroma_client = mock_chroma_client
            return client

    def test_create_collection_success(self):
        """Lines 96-98: successful collection creation."""
        client = self._make_vdb_client()
        result = client.create_collection("test_col")
        assert result == "test_col"

    def test_create_collection_already_exists(self):
        """Lines 100-103: error when collection already exists."""
        client = self._make_vdb_client()
        client.client.create_collection.side_effect = Exception(
            "Collection already exists"
        )
        with pytest.raises(LLMAbstractionError, match="already exists"):
            client.create_collection("test_col")

    def test_create_collection_generic_error(self):
        """Line 104: generic create error."""
        client = self._make_vdb_client()
        client.client.create_collection.side_effect = Exception("disk full")
        with pytest.raises(LLMAbstractionError, match="Failed to create"):
            client.create_collection("test_col")

    def test_get_collection_success(self):
        """Lines 118-119: successful get."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col
        result = client.get_collection("test_col")
        assert result == mock_col

    def test_get_collection_not_found(self):
        """Lines 120-121: collection not found."""
        client = self._make_vdb_client()
        client.client.get_collection.side_effect = Exception("not found")
        with pytest.raises(LLMAbstractionError, match="not found"):
            client.get_collection("test_col")

    def test_get_or_create_collection(self):
        """Line 134: get_or_create delegates to client."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_or_create_collection.return_value = mock_col
        result = client.get_or_create_collection("col")
        assert result == mock_col

    def test_list_collections(self):
        """Lines 142-143: list collections returns names."""
        client = self._make_vdb_client()
        mock_col1 = MagicMock()
        mock_col1.name = "col1"
        mock_col2 = MagicMock()
        mock_col2.name = "col2"
        client.client.list_collections.return_value = [mock_col1, mock_col2]
        result = client.list_collections()
        assert result == ["col1", "col2"]

    def test_delete_collection_success(self):
        """Lines 151-152: successful delete."""
        client = self._make_vdb_client()
        client.delete_collection("col")
        client.client.delete_collection.assert_called_once_with(name="col")

    def test_delete_collection_error(self):
        """Lines 153-154: delete error."""
        client = self._make_vdb_client()
        client.client.delete_collection.side_effect = Exception("locked")
        with pytest.raises(LLMAbstractionError, match="Failed to delete"):
            client.delete_collection("col")

    async def test_add_documents(self):
        """Lines 174-203: add documents with auto-generated IDs."""
        from stratifyai.embeddings import EmbeddingResult

        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_or_create_collection.return_value = mock_col

        embed_result = EmbeddingResult(
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            model="test",
            total_tokens=10,
            cost=0.01,
        )
        client.embedding_provider.generate_embeddings = AsyncMock(
            return_value=embed_result
        )

        ids = await client.add_documents(
            "col", ["doc1", "doc2"], metadatas=[{"key": "v1"}, {"key": "v2"}]
        )
        assert len(ids) == 2
        mock_col.add.assert_called_once()

    async def test_add_documents_empty(self):
        """Line 174: empty documents returns empty list."""
        client = self._make_vdb_client()
        result = await client.add_documents("col", [])
        assert result == []

    async def test_add_documents_no_metadata(self):
        """Lines 185-186: auto-generate metadata when none provided."""
        from stratifyai.embeddings import EmbeddingResult

        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_or_create_collection.return_value = mock_col

        embed_result = EmbeddingResult(
            embeddings=[[0.1]], model="test", total_tokens=5, cost=0.005
        )
        client.embedding_provider.generate_embeddings = AsyncMock(
            return_value=embed_result
        )

        ids = await client.add_documents("col", ["doc1"])
        assert len(ids) == 1
        call_args = mock_col.add.call_args
        metadatas = (
            call_args[1]["metadatas"]
            if "metadatas" in call_args[1]
            else call_args[0][2]
        )
        # Should have auto-generated timestamp
        assert "timestamp" in metadatas[0]

    async def test_query(self):
        """Lines 223-253: query with semantic search."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        client.embedding_provider.generate_embedding = AsyncMock(
            return_value=[0.1, 0.2]
        )
        mock_col.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"k": "v1"}, {"k": "v2"}]],
            "distances": [[0.1, 0.5]],
            "ids": [["id1", "id2"]],
        }

        results = await client.query("col", "search text", n_results=2)
        assert len(results) == 2
        assert results[0].document == "doc1"
        assert results[0].distance == 0.1

    def test_get_collection_count(self):
        """Lines 264-265: get document count."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        mock_col.count.return_value = 42
        client.client.get_collection.return_value = mock_col

        count = client.get_collection_count("col")
        assert count == 42

    def test_delete_documents(self):
        """Lines 274-275: delete docs by ID."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        client.delete_documents("col", ["id1", "id2"])
        mock_col.delete.assert_called_once_with(ids=["id1", "id2"])

    async def test_update_documents_with_new_text(self):
        """Lines 292-307: update documents with new text and embeddings."""
        from stratifyai.embeddings import EmbeddingResult

        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        embed_result = EmbeddingResult(
            embeddings=[[0.5]], model="test", total_tokens=5, cost=0.005
        )
        client.embedding_provider.generate_embeddings = AsyncMock(
            return_value=embed_result
        )

        await client.update_documents(
            "col", ids=["id1"], documents=["new text"], metadatas=[{"updated": "true"}]
        )
        mock_col.update.assert_called_once()
        call_kwargs = mock_col.update.call_args[1]
        assert "embeddings" in call_kwargs
        assert "metadatas" in call_kwargs

    async def test_update_documents_metadata_only(self):
        """Lines 304-305: update metadata only (no new embeddings)."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        await client.update_documents(
            "col", ids=["id1"], metadatas=[{"status": "archived"}]
        )
        mock_col.update.assert_called_once()
        call_kwargs = mock_col.update.call_args[1]
        assert "embeddings" not in call_kwargs
        assert call_kwargs["metadatas"] == [{"status": "archived"}]

    def test_add_documents_sync(self):
        """Line 334: sync wrapper for add_documents."""
        from stratifyai.embeddings import EmbeddingResult

        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_or_create_collection.return_value = mock_col

        embed_result = EmbeddingResult(
            embeddings=[[0.1]], model="test", total_tokens=5, cost=0.005
        )
        client.embedding_provider.generate_embeddings = AsyncMock(
            return_value=embed_result
        )

        result = client.add_documents_sync("col", ["doc1"])
        assert len(result) == 1

    def test_query_sync(self):
        """Line 354: sync wrapper for query."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        client.embedding_provider.generate_embedding = AsyncMock(
            return_value=[0.1, 0.2]
        )
        mock_col.query.return_value = {
            "documents": [["doc1"]],
            "metadatas": [[{"k": "v"}]],
            "distances": [[0.1]],
            "ids": [["id1"]],
        }

        results = client.query_sync("col", "search")
        assert len(results) == 1

    def test_get_documents(self):
        """Lines 384-410: get documents with various filters."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        mock_col.get.return_value = {
            "ids": ["id1", "id2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{"k": "v1"}, {"k": "v2"}],
        }

        docs = client.get_documents("col", ids=["id1", "id2"])
        assert len(docs) == 2
        assert docs[0]["id"] == "id1"

    def test_get_documents_with_filters(self):
        """Lines 387-393: get documents with where and limit."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        mock_col.get.return_value = {
            "ids": ["id1"],
            "documents": ["doc1"],
            "metadatas": [{"status": "active"}],
        }

        client.get_documents("col", where={"status": "active"}, limit=10)
        call_kwargs = mock_col.get.call_args[1]
        assert call_kwargs["where"] == {"status": "active"}
        assert call_kwargs["limit"] == 10

    def test_get_documents_empty(self):
        """Lines 398-408: empty result set."""
        client = self._make_vdb_client()
        mock_col = MagicMock()
        client.client.get_collection.return_value = mock_col

        mock_col.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }

        docs = client.get_documents("col")
        assert docs == []


# ===================================================================
# Catalog manager tests
# ===================================================================


class TestCatalogManager:
    """Tests for catalog_manager.py covering lines 59-87, 138-198."""

    def setup_method(self):
        """Reset catalog cache before each test."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = None
        cm._CATALOG_PATH = None

    def test_load_catalog_file_not_found(self):
        """Lines 63-65: FileNotFoundError for missing catalog."""
        from stratifyai.catalog_manager import load_catalog

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.exists.return_value = False
            with pytest.raises(FileNotFoundError, match="Model catalog not found"):
                load_catalog(force_reload=True)

    def test_load_catalog_invalid_json(self):
        """Lines 82-84: ValueError for invalid JSON."""
        from stratifyai.catalog_manager import load_catalog

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_path.return_value = mock_p
            with patch(
                "builtins.open", MagicMock(return_value=io.StringIO("{invalid"))
            ):
                with pytest.raises(ValueError, match="Failed to parse catalog JSON"):
                    load_catalog(force_reload=True)

    def test_load_catalog_not_dict(self):
        """Lines 72-73: ValueError when catalog is not a dict."""
        from stratifyai.catalog_manager import load_catalog

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_path.return_value = mock_p
            with patch(
                "builtins.open", MagicMock(return_value=io.StringIO('"a string"'))
            ):
                with pytest.raises(ValueError, match="must be a JSON object"):
                    load_catalog(force_reload=True)

    def test_load_catalog_missing_providers(self):
        """Lines 75-76: ValueError when 'providers' key missing."""
        from stratifyai.catalog_manager import load_catalog

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_path.return_value = mock_p
            with patch(
                "builtins.open",
                MagicMock(return_value=io.StringIO('{"version": "1.0"}')),
            ):
                with pytest.raises(ValueError, match="missing 'providers' key"):
                    load_catalog(force_reload=True)

    def test_load_catalog_success_and_caching(self):
        """Lines 78-80, 53-54, 58-59: successful load and double-checked locking cache."""
        from stratifyai.catalog_manager import load_catalog

        catalog_data = {
            "version": "1.0",
            "providers": {"test": {"model-1": {"cost_input": 1.0}}},
        }

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_path.return_value = mock_p
            with patch(
                "builtins.open",
                MagicMock(return_value=io.StringIO(json.dumps(catalog_data))),
            ):
                result = load_catalog(force_reload=True)
                assert result["version"] == "1.0"

            # Second call should use cache (line 53-54)
            result2 = load_catalog()
            assert result2 is result

    def test_is_model_deprecated_true(self):
        """Lines 138-141: deprecated model check."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "test": {"old-model": {"deprecated": True}},
            }
        }
        assert cm.is_model_deprecated("test", "old-model") is True

    def test_is_model_deprecated_false(self):
        """Lines 138-141: non-deprecated model."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "test": {"new-model": {"deprecated": False}},
            }
        }
        assert cm.is_model_deprecated("test", "new-model") is False

    def test_is_model_deprecated_unknown(self):
        """Lines 139-140: unknown model returns False."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {"providers": {"test": {}}}
        assert cm.is_model_deprecated("test", "nonexistent") is False

    def test_get_model_replacement_exists(self):
        """Lines 154-158: replacement model found."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "test": {
                    "old-model": {
                        "deprecated": True,
                        "replacement_model": "new-model",
                    }
                },
            }
        }
        assert cm.get_model_replacement("test", "old-model") == "new-model"

    def test_get_model_replacement_none(self):
        """Lines 155-156: no replacement for unknown model."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {"providers": {"test": {}}}
        assert cm.get_model_replacement("test", "nonexistent") is None

    def test_get_model_replacement_not_string(self):
        """Line 158: replacement that is not a string returns None."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "test": {"model": {"replacement_model": 123}},
            }
        }
        assert cm.get_model_replacement("test", "model") is None

    def test_list_all_models_exclude_deprecated(self):
        """Lines 170-184: list models filtering deprecated."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "prov1": {
                    "active": {"deprecated": False},
                    "old": {"deprecated": True},
                },
            }
        }
        result = cm.list_all_models(include_deprecated=False)
        assert "active" in result["prov1"]
        assert "old" not in result["prov1"]

    def test_list_all_models_include_deprecated(self):
        """Lines 175-176: list all models including deprecated."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "providers": {
                "prov1": {
                    "active": {"deprecated": False},
                    "old": {"deprecated": True},
                },
            }
        }
        result = cm.list_all_models(include_deprecated=True)
        assert "active" in result["prov1"]
        assert "old" in result["prov1"]

    def test_get_catalog_version(self):
        """Lines 189-191: get version string."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {"version": "2.0", "providers": {}}
        assert cm.get_catalog_version() == "2.0"

    def test_get_catalog_updated(self):
        """Lines 196-198: get updated timestamp."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {
            "updated": "2026-01-01T00:00:00Z",
            "providers": {},
        }
        assert cm.get_catalog_updated() == "2026-01-01T00:00:00Z"

    def test_get_catalog_version_unknown(self):
        """Line 190: version missing defaults to 'unknown'."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {"providers": {}}
        assert cm.get_catalog_version() == "unknown"

    def test_get_catalog_updated_unknown(self):
        """Line 197: updated missing defaults to 'unknown'."""
        import stratifyai.catalog_manager as cm

        cm._CATALOG_CACHE = {"providers": {}}
        assert cm.get_catalog_updated() == "unknown"

    def test_load_catalog_generic_exception(self):
        """Lines 85-87: generic exception re-raised."""
        from stratifyai.catalog_manager import load_catalog

        with patch("stratifyai.catalog_manager.get_catalog_path") as mock_path:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_path.return_value = mock_p
            with patch("builtins.open", side_effect=PermissionError("no access")):
                with pytest.raises(PermissionError):
                    load_catalog(force_reload=True)


# ---------------------------------------------------------------------------
# reasoning_detector.py coverage
# ---------------------------------------------------------------------------


class TestReasoningDetectorCoverage:
    """Cover uncovered branches in reasoning_detector.py."""

    def test_empty_model_returns_false(self):
        from stratifyai.utils.reasoning_detector import is_reasoning_model

        assert is_reasoning_model("openai", "", {}) is False

    def test_openai_o_series_detected(self):
        from stratifyai.utils.reasoning_detector import is_reasoning_model

        assert is_reasoning_model("openai", "o3-mini", {}) is True

    def test_grok_reasoning_models(self):
        from stratifyai.utils.reasoning_detector import is_reasoning_model

        assert is_reasoning_model("grok", "grok-4", {}) is True
        assert is_reasoning_model("grok", "grok-reasoning-v2", {}) is True
        assert is_reasoning_model("grok", "grok-3-mini-fast", {}) is True
        assert is_reasoning_model("grok", "grok-code-v1", {}) is True

    def test_deepseek_reasoning(self):
        from stratifyai.utils.reasoning_detector import is_reasoning_model

        assert is_reasoning_model("deepseek", "deepseek-reasoner", {}) is True

    def test_groq_reasoning(self):
        from stratifyai.utils.reasoning_detector import is_reasoning_model

        assert is_reasoning_model("groq", "llama-reasoning-v1", {}) is True
        assert is_reasoning_model("groq", "gpt-oss-v1", {}) is True

    def test_get_temperature_for_reasoning_model(self):
        from stratifyai.utils.reasoning_detector import get_temperature_for_model

        result = get_temperature_for_model("openai", "o1", 0.5, model_catalog={})
        assert result == 1.0

    def test_get_temperature_for_non_reasoning_model(self):
        from stratifyai.utils.reasoning_detector import get_temperature_for_model

        result = get_temperature_for_model("openai", "gpt-4o", 0.7, model_catalog={})
        assert result == 0.7


# ---------------------------------------------------------------------------
# token_counter.py coverage
# ---------------------------------------------------------------------------


class TestTokenCounterCoverage:
    """Cover uncovered branches in token_counter.py."""

    def test_estimate_tokens_basic(self):
        from stratifyai.utils.token_counter import estimate_tokens

        result = estimate_tokens("Hello world, this is a test")
        assert result > 0

    def test_estimate_tokens_empty(self):
        from stratifyai.utils.token_counter import estimate_tokens

        result = estimate_tokens("")
        assert result == 0

    def test_count_tokens_for_messages(self):
        from stratifyai.models import Message
        from stratifyai.utils.token_counter import count_tokens_for_messages

        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ]
        result = count_tokens_for_messages(messages)
        assert result > 0

    def test_get_context_window_known(self):
        from stratifyai.utils.token_counter import get_context_window

        result = get_context_window("openai", "gpt-4o")
        assert result > 0

    def test_get_context_window_unknown(self):
        from stratifyai.utils.token_counter import get_context_window

        result = get_context_window("unknown", "fake-model")
        assert result > 0  # should return a default

    def test_check_token_limit_within(self):
        from stratifyai.utils.token_counter import check_token_limit

        exceeds, context_window, pct = check_token_limit(100, "openai", "gpt-4o")
        assert exceeds is False
        assert context_window > 0
        assert pct < 1.0

    def test_check_token_limit_exceeded(self):
        from stratifyai.utils.token_counter import check_token_limit

        exceeds, context_window, pct = check_token_limit(999999999, "openai", "gpt-4o")
        assert exceeds is True


# ---------------------------------------------------------------------------
# mcp_client/engine.py coverage (utility functions + dataclass)
# ---------------------------------------------------------------------------


class TestMCPEngineUtilitiesCoverage:
    """Cover utility functions and ToolExecutionResult in engine.py."""

    def test_render_tool_payload_string(self):
        from stratifyai.mcp_client.engine import _render_tool_payload

        assert _render_tool_payload("hello") == "hello"

    def test_render_tool_payload_dict(self):
        from stratifyai.mcp_client.engine import _render_tool_payload

        result = _render_tool_payload({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_render_tool_payload_truncation(self):
        from stratifyai.mcp_client.engine import (
            _MAX_TOOL_CONTEXT_CHARS,
            _render_tool_payload,
        )

        long_str = "x" * (_MAX_TOOL_CONTEXT_CHARS + 100)
        result = _render_tool_payload(long_str)
        assert result.endswith("... [truncated]")

    def test_format_timestamp_none(self):
        from stratifyai.mcp_client.engine import _format_timestamp

        assert _format_timestamp(None) is None

    def test_format_timestamp_value(self):
        from stratifyai.mcp_client.engine import _format_timestamp

        result = _format_timestamp(0.0)
        assert result == "1970-01-01T00:00:00Z"

    def test_tool_execution_result_to_dict(self):
        from stratifyai.mcp_client.engine import ToolExecutionResult

        result = ToolExecutionResult(
            call_id="c1",
            server_id="srv",
            tool_name="tool",
            namespace="srv.tool",
            arguments={"a": 1},
            result="ok",
        )
        d = result.to_dict()
        assert d["call_id"] == "c1"
        assert d["server_id"] == "srv"
        assert d["result"] == "ok"
        assert d["error"] is None

    def test_tool_execution_result_render_for_prompt_ok(self):
        from stratifyai.mcp_client.engine import ToolExecutionResult

        result = ToolExecutionResult(
            call_id="c1",
            server_id="srv",
            tool_name="tool",
            namespace="srv.tool",
            arguments={"a": 1},
            result="output",
        )
        rendered = result.render_for_prompt()
        assert "Status: ok" in rendered
        assert "output" in rendered

    def test_tool_execution_result_render_for_prompt_error(self):
        from stratifyai.mcp_client.engine import ToolExecutionResult

        result = ToolExecutionResult(
            call_id="c1",
            server_id="srv",
            tool_name="tool",
            namespace="srv.tool",
            arguments={},
            error="something broke",
        )
        rendered = result.render_for_prompt()
        assert "Status: error" in rendered
        assert "something broke" in rendered


# ---------------------------------------------------------------------------
# mcp_client/permissions.py coverage
# ---------------------------------------------------------------------------


class TestMCPPermissionsCoverage:
    """Cover uncovered branches in permissions.py."""

    def test_server_permission_config_from_dict_invalid(self):
        from stratifyai.mcp_client.permissions import ServerPermissionConfig

        config = ServerPermissionConfig.from_dict("not a dict")
        assert config.default_mode is None

    def test_server_permission_config_from_dict_invalid_mode(self):
        from stratifyai.mcp_client.permissions import ServerPermissionConfig

        config = ServerPermissionConfig.from_dict({"default_mode": "invalid_mode"})
        assert config.default_mode is None

    def test_server_permission_config_to_dict(self):
        from stratifyai.mcp_client.permissions import (
            PermissionMode,
            ServerPermissionConfig,
        )

        config = ServerPermissionConfig(
            default_mode=PermissionMode.ALLOW,
            allow=["read_*"],
            deny=["delete_*"],
            confirm=["write_*"],
        )
        d = config.to_dict()
        assert d["default_mode"] == "allow"
        assert d["allow"] == ["read_*"]
        assert d["deny"] == ["delete_*"]
        assert d["confirm"] == ["write_*"]

    def test_matches_pattern_empty(self):
        from stratifyai.mcp_client.permissions import _matches_pattern

        assert _matches_pattern("tool", "srv.tool", "  ") is False

    def test_permission_manager_evaluate_deny(self):
        from stratifyai.mcp_client.permissions import (
            PermissionManager,
            PermissionMode,
            ServerPermissionConfig,
        )

        pm = PermissionManager(
            server_policies={
                "srv": ServerPermissionConfig(deny=["bad_tool"]),
            }
        )
        decision = pm.evaluate("srv", "bad_tool")
        assert decision.mode == PermissionMode.DENY

    async def test_authorize_deny_raises(self):
        from stratifyai.mcp_client.permissions import (
            MCPPermissionError,
            PermissionManager,
            ServerPermissionConfig,
        )

        pm = PermissionManager(
            server_policies={
                "srv": ServerPermissionConfig(deny=["bad_tool"]),
            }
        )
        with pytest.raises(MCPPermissionError):
            await pm.authorize("srv", "bad_tool", {})

    async def test_authorize_confirm_no_handler_raises(self):
        from stratifyai.mcp_client.permissions import (
            MCPConfirmationRequiredError,
            PermissionManager,
            ServerPermissionConfig,
        )

        pm = PermissionManager(
            server_policies={
                "srv": ServerPermissionConfig(confirm=["risky_tool"]),
            }
        )
        with pytest.raises(MCPConfirmationRequiredError):
            await pm.authorize("srv", "risky_tool", {})

    async def test_authorize_confirm_declined_raises(self):
        from stratifyai.mcp_client.permissions import (
            MCPPermissionError,
            PermissionManager,
            ServerPermissionConfig,
        )

        pm = PermissionManager(
            server_policies={
                "srv": ServerPermissionConfig(confirm=["risky_tool"]),
            }
        )
        with pytest.raises(MCPPermissionError, match="declined"):
            await pm.authorize(
                "srv",
                "risky_tool",
                {},
                confirmation_handler=lambda *_: False,
            )

    def test_safety_default_read_only_keyword(self):
        from stratifyai.mcp_client.permissions import (
            PermissionManager,
            PermissionMode,
        )

        pm = PermissionManager()
        decision = pm.evaluate("srv", "fetch")
        assert decision.mode == PermissionMode.ALLOW

    def test_safety_default_unknown_tool_requires_confirm(self):
        from stratifyai.mcp_client.permissions import (
            PermissionManager,
            PermissionMode,
        )

        pm = PermissionManager()
        decision = pm.evaluate("srv", "xyzzy_unknown_9999")
        assert decision.mode == PermissionMode.CONFIRM


# ---------------------------------------------------------------------------
# tool_registry.py — per-tool removal (issue #59)
# ---------------------------------------------------------------------------


class TestToolRegistryPerToolRemoval:
    """Test unregister_tool for individual tool removal."""

    def test_unregister_existing_tool(self):
        from unittest.mock import MagicMock

        from stratifyai.mcp_client.tool_registry import ToolRegistry

        registry = ToolRegistry()
        tool_a = MagicMock()
        tool_a.name = "read_file"
        tool_b = MagicMock()
        tool_b.name = "write_file"
        registry.register_server_tools("fs", [tool_a, tool_b])

        assert registry.find_tool("fs", "read_file") is not None
        assert registry.unregister_tool("fs", "read_file") is True
        assert registry.find_tool("fs", "read_file") is None
        # Other tool still present
        assert registry.find_tool("fs", "write_file") is not None

    def test_unregister_nonexistent_tool(self):
        from stratifyai.mcp_client.tool_registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.unregister_tool("srv", "no_such_tool") is False

    def test_unregister_tool_unknown_server(self):
        from stratifyai.mcp_client.tool_registry import ToolRegistry

        registry = ToolRegistry()
        assert registry.unregister_tool("unknown_server", "tool") is False

    def test_engine_remove_tool(self):
        from unittest.mock import MagicMock, patch

        from stratifyai.mcp_client.engine import MCPClientEngine

        with patch(
            "stratifyai.mcp_client.engine.load_enabled_servers", return_value=[]
        ):
            engine = MCPClientEngine()

        tool = MagicMock()
        tool.name = "search"
        tool.description = "Search stuff"
        tool.inputSchema = {"type": "object"}
        engine._tool_registry.register_server_tools("brave", [tool])

        assert engine.remove_tool("brave", "search") is True
        assert engine.remove_tool("brave", "search") is False
        assert engine.find_tool("brave", "search") is None
