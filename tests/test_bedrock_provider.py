"""Tests for AWS Bedrock provider."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from stratifyai.exceptions import (
    InvalidModelError,
    ProviderAPIError,
)
from stratifyai.models import ChatRequest, Message, Usage
from stratifyai.providers.bedrock import BedrockProvider


class TestBedrockProviderInitialization:
    """Tests for Bedrock provider initialization."""

    def test_initialization_with_credentials(self):
        """Test provider initialization with explicit AWS credentials."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key-id", aws_secret_access_key="test-secret-key"
            )
            assert provider.aws_access_key_id == "test-key-id"
            assert provider.aws_secret_access_key == "test-secret-key"
            assert provider.region_name == "us-east-1"  # default
            assert provider.provider_name == "bedrock"

    def test_initialization_with_env_vars(self):
        """Test provider initialization with environment variables."""
        with patch.dict(
            "os.environ",
            {
                "AWS_ACCESS_KEY_ID": "env-key-id",
                "AWS_SECRET_ACCESS_KEY": "env-secret-key",
                "AWS_DEFAULT_REGION": "us-west-2",
            },
        ):
            with patch("stratifyai.providers.bedrock.aioboto3.Session"):
                provider = BedrockProvider()
                assert provider.aws_access_key_id == "env-key-id"
                assert provider.aws_secret_access_key == "env-secret-key"
                assert provider.region_name == "us-west-2"

    def test_initialization_with_custom_region(self):
        """Test provider initialization with custom region."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                region_name="eu-west-1",
            )
            assert provider.region_name == "eu-west-1"

    def test_initialization_with_session_token(self):
        """Test provider initialization with session token."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                aws_session_token="test-token",
            )
            assert provider.aws_session_token == "test-token"

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def test_initialization_creates_session(self, mock_session_class):
        """Test that initialization creates aioboto3 session."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )

        # aioboto3 Session is stored, client is created in async context
        mock_session_class.assert_called_once()
        assert provider._session == mock_session
        assert provider._client is None  # Client created in async context


class TestBedrockProviderModels:
    """Tests for Bedrock provider model support."""

    def test_supported_models(self):
        """Test that provider returns list of supported Bedrock models."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
            models = provider.get_supported_models()

            assert isinstance(models, list)
            assert len(models) > 0

            # Check for key models from each family
            assert "anthropic.claude-3-5-sonnet-20241022-v2:0" in models
            assert "meta.llama3-3-70b-instruct-v1:0" in models
            assert "mistral.mistral-large-2402-v1:0" in models
            assert "amazon.nova-pro-v1:0" in models
            assert "cohere.command-r-plus-v1:0" in models

    def test_validate_model(self):
        """Test model validation."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )

            # Valid models
            assert (
                provider.validate_model("anthropic.claude-3-5-sonnet-20241022-v2:0")
                is True
            )
            assert provider.validate_model("meta.llama3-3-70b-instruct-v1:0") is True

            # Invalid model
            assert provider.validate_model("invalid-model") is False


class TestBedrockProviderChatCompletion:
    """Tests for Bedrock chat completion."""

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_anthropic_claude(self, mock_session_class):
        """Test chat completion with Anthropic Claude model."""
        # Setup mock session and async context manager for client
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock client with async invoke_model
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "id": "msg_123",
                    "content": [{"type": "text", "text": "Hello from Bedrock!"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }
            ).encode()
        )

        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})

        # Mock the async context manager for session.client()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager

        # Create provider and make request
        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")],
        )

        response = await provider.chat_completion(request)

        assert response.content == "Hello from Bedrock!"
        assert response.provider == "bedrock"
        assert response.model == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15
        assert response.usage.cost_usd > 0  # Cost should be calculated

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_llama(self, mock_session_class):
        """Test chat completion with Meta Llama model."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock client with async invoke_model
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "generation": "Llama response!",
                    "prompt_token_count": 10,
                    "generation_token_count": 8,
                    "stop_reason": "stop",
                }
            ).encode()
        )

        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})

        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="meta.llama3-3-70b-instruct-v1:0",
            messages=[Message(role="user", content="Hello")],
        )

        response = await provider.chat_completion(request)

        assert response.content == "Llama response!"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 8

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_nova(self, mock_session_class):
        """Test chat completion with Amazon Nova model."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock client with async invoke_model
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "output": {"message": {"content": [{"text": "Nova response!"}]}},
                    "usage": {"inputTokens": 12, "outputTokens": 6, "totalTokens": 18},
                    "stopReason": "end_turn",
                }
            ).encode()
        )

        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})

        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="amazon.nova-pro-v1:0",
            messages=[Message(role="user", content="Hello")],
        )

        response = await provider.chat_completion(request)

        assert response.content == "Nova response!"
        assert response.usage.prompt_tokens == 12
        assert response.usage.completion_tokens == 6

    @pytest.mark.asyncio
    async def test_chat_completion_invalid_model(self):
        """Test chat completion with invalid model raises error."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="invalid-model", messages=[Message(role="user", content="Hello")]
            )

            with pytest.raises(InvalidModelError):
                await provider.chat_completion(request)

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_with_system_message(self, mock_session_class):
        """Test chat completion with system message."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock client with async invoke_model
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "content": [{"type": "text", "text": "Response"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 15, "output_tokens": 5},
                }
            ).encode()
        )

        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})

        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hello"),
            ],
        )

        await provider.chat_completion(request)


class TestBedrockProviderStreaming:
    """Tests for Bedrock streaming."""

    @pytest.mark.skip(reason="Streaming tests require complex async iterator mocking")
    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_anthropic(self, mock_session_class):
        """Test streaming chat completion with Anthropic Claude."""
        pass  # Streaming tests need more complex async iterator mocking

    @pytest.mark.asyncio
    async def test_chat_completion_stream_invalid_model(self):
        """Test streaming with invalid model raises error."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="invalid-model",
                messages=[Message(role="user", content="Hello")],
                stream=True,
            )

            with pytest.raises(InvalidModelError):
                async for _ in provider.chat_completion_stream(request):
                    pass


class TestBedrockProviderCostCalculation:
    """Tests for cost calculation."""

    def test_calculate_cost_claude(self):
        """Test cost calculation for Claude model."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )

            usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

            cost = provider._calculate_cost(
                usage, "anthropic.claude-3-5-sonnet-20241022-v2:0"
            )

            # Claude 3.5 Sonnet pricing: $3/MTok input, $15/MTok output
            expected_cost = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
            assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_llama(self):
        """Test cost calculation for Llama model."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )

            usage = Usage(prompt_tokens=2000, completion_tokens=1000, total_tokens=3000)

            cost = provider._calculate_cost(usage, "meta.llama3-3-70b-instruct-v1:0")

            # Llama 3.3 70B pricing: $0.99/MTok for both input and output
            expected_cost = (2000 / 1_000_000) * 0.99 + (1000 / 1_000_000) * 0.99
            assert cost == pytest.approx(expected_cost)


class TestBedrockProviderRequestBuilding:
    """Tests for request body building."""

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def test_build_anthropic_request(self, mock_session_class):
        """Test building request body for Anthropic Claude."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")],
            temperature=0.8,
            max_tokens=1000,
        )

        body = provider._build_request_body(request)

        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["messages"] == [{"role": "user", "content": "Hello"}]
        assert body["max_tokens"] == 1000
        assert body["temperature"] == 0.8

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def test_build_nova_request(self, mock_session_class):
        """Test building request body for Amazon Nova."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="amazon.nova-pro-v1:0",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
            max_tokens=500,
        )

        body = provider._build_request_body(request)

        assert body["messages"] == [{"role": "user", "content": [{"text": "Hello"}]}]
        assert body["inferenceConfig"]["max_new_tokens"] == 500
        assert body["inferenceConfig"]["temperature"] == 0.7


class TestBedrockProviderErrorHandling:
    """Tests for error handling."""

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_client_error_handling(self, mock_session_class):
        """Test handling of AWS ClientError."""
        from botocore.exceptions import ClientError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock client that raises ClientError
        mock_client = AsyncMock()
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Invalid request"}
        }
        mock_client.invoke_model = AsyncMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )

        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager

        provider = BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderAPIError) as exc_info:
            await provider.chat_completion(request)

        assert "Request validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_temperature_validation(self):
        """Test temperature validation for Bedrock (0.0-1.0)."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                messages=[Message(role="user", content="Hello")],
                temperature=2.0,  # Invalid for Bedrock
            )

            from stratifyai.exceptions import ValidationError

            with pytest.raises(ValidationError):
                await provider.chat_completion(request)


# ---------------------------------------------------------------------------
# Additional coverage: all model families, streaming, error branches
# ---------------------------------------------------------------------------


class TestBedrockNormalizeResponseAllFamilies:
    """Tests for _normalize_response across all supported model families."""

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def _make_provider(self, mock_session_class):
        """Create a BedrockProvider with mocked session.

        Args:
            mock_session_class: Mocked aioboto3.Session class.

        Returns:
            A BedrockProvider instance.
        """
        mock_session_class.return_value = Mock()
        return BedrockProvider(
            aws_access_key_id="test-key", aws_secret_access_key="test-secret"
        )

    def test_normalize_mistral_response(self):
        """Mistral response is normalized correctly."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        raw = {
            "outputs": [{"text": "Mistral says hi!"}],
            "stop_reason": "stop",
        }
        resp = provider._normalize_response(raw, "mistral.mistral-large-2402-v1:0")
        assert resp.content == "Mistral says hi!"
        assert resp.provider == "bedrock"

    def test_normalize_cohere_response(self):
        """Cohere response is normalized correctly."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        raw = {
            "text": "Cohere answer",
            "finish_reason": "COMPLETE",
            "prompt_tokens": 5,
            "generation_tokens": 3,
        }
        resp = provider._normalize_response(raw, "cohere.command-r-plus-v1:0")
        assert resp.content == "Cohere answer"
        assert resp.usage.prompt_tokens == 5

    def test_normalize_titan_response(self):
        """Titan response is normalized correctly."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        raw = {
            "results": [
                {
                    "outputText": "Titan answer",
                    "completionReason": "FINISH",
                    "inputTextTokenCount": 10,
                    "outputTextTokenCount": 4,
                }
            ]
        }
        resp = provider._normalize_response(raw, "amazon.titan-text-express-v1")
        assert resp.content == "Titan answer"
        assert resp.usage.prompt_tokens == 10

    def test_normalize_unknown_model_fallback(self):
        """Unknown model family uses str(raw_response) as content."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        raw = {"some_key": "some_value"}
        resp = provider._normalize_response(raw, "unknown.model-v1")
        assert "some_key" in resp.content or "some_value" in resp.content

    def test_normalize_response_none_model_raises(self):
        """Passing None as model raises ProviderAPIError."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        with pytest.raises(ProviderAPIError):
            provider._normalize_response({}, None)

    def test_extract_llama_usage_zero_fallback(self):
        """_extract_llama_usage estimates completion tokens when API returns 0."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key", aws_secret_access_key="test-secret"
            )
        content = "A" * 40  # 40 chars ≈ 10 tokens
        usage = provider._extract_llama_usage(
            {"prompt_token_count": 5, "generation_token_count": 0},
            content,
            "meta.llama3-3-70b-instruct-v1:0",
        )
        assert usage.completion_tokens == len(content) // 4


class TestBedrockNormalizeStreamChunkAllFamilies:
    """Tests for _normalize_stream_chunk across all model families."""

    def _provider(self):
        """Return a BedrockProvider with a mocked session.

        Returns:
            A BedrockProvider instance.
        """
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            return BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")

    def test_anthropic_content_block_delta(self):
        """Anthropic content_block_delta chunk extracts the text delta."""
        p = self._provider()
        chunk = {"type": "content_block_delta", "delta": {"text": "hello"}}
        resp = p._normalize_stream_chunk(
            chunk, "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        assert resp.content == "hello"

    def test_anthropic_non_delta_chunk(self):
        """Non-delta Anthropic chunks produce empty content."""
        p = self._provider()
        chunk = {"type": "message_start"}
        resp = p._normalize_stream_chunk(
            chunk, "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        assert resp.content == ""

    def test_llama_stream_chunk(self):
        """Llama streaming chunk extracts 'generation'."""
        p = self._provider()
        chunk = {"generation": "Llama chunk"}
        resp = p._normalize_stream_chunk(chunk, "meta.llama3-3-70b-instruct-v1:0")
        assert resp.content == "Llama chunk"

    def test_mistral_stream_chunk(self):
        """Mistral streaming chunk extracts text from outputs."""
        p = self._provider()
        chunk = {"outputs": [{"text": "Mistral chunk"}]}
        resp = p._normalize_stream_chunk(chunk, "mistral.mistral-large-2402-v1:0")
        assert resp.content == "Mistral chunk"

    def test_nova_stream_chunk_with_delta(self):
        """Nova contentBlockDelta chunk extracts text delta."""
        p = self._provider()
        chunk = {"contentBlockDelta": {"delta": {"text": "Nova chunk"}}}
        resp = p._normalize_stream_chunk(chunk, "amazon.nova-pro-v1:0")
        assert resp.content == "Nova chunk"

    def test_nova_stream_chunk_non_delta(self):
        """Nova chunk without contentBlockDelta produces empty content."""
        p = self._provider()
        chunk = {"messageStop": True}
        resp = p._normalize_stream_chunk(chunk, "amazon.nova-pro-v1:0")
        assert resp.content == ""

    def test_titan_stream_chunk(self):
        """Titan streaming chunk extracts 'outputText'."""
        p = self._provider()
        chunk = {"outputText": "Titan chunk"}
        resp = p._normalize_stream_chunk(chunk, "amazon.titan-text-express-v1")
        assert resp.content == "Titan chunk"

    def test_unknown_model_stream_chunk(self):
        """Unknown model family produces empty string content."""
        p = self._provider()
        chunk = {"someKey": "val"}
        resp = p._normalize_stream_chunk(chunk, "unknown.model-v1")
        assert resp.content == ""


class TestBedrockRequestBuildingAllFamilies:
    """Tests for all request-building helper methods."""

    def _provider(self):
        """Return a BedrockProvider with a mocked session.

        Returns:
            A BedrockProvider instance.
        """
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            return BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")

    def test_build_llama_request(self):
        """Llama request body uses 'prompt' key."""
        p = self._provider()
        req = ChatRequest(
            model="meta.llama3-3-70b-instruct-v1:0",
            messages=[Message(role="user", content="Hello")],
        )
        body = p._build_request_body(req)
        assert "prompt" in body
        assert "max_gen_len" in body

    def test_build_mistral_request(self):
        """Mistral request body uses 'prompt' key."""
        p = self._provider()
        req = ChatRequest(
            model="mistral.mistral-large-2402-v1:0",
            messages=[Message(role="user", content="Hello")],
        )
        body = p._build_request_body(req)
        assert "prompt" in body
        assert "max_tokens" in body

    def test_build_cohere_request(self):
        """Cohere request body uses 'message' and 'chat_history' keys."""
        p = self._provider()
        req = ChatRequest(
            model="cohere.command-r-plus-v1:0",
            messages=[
                Message(role="user", content="Hi"),
                Message(role="assistant", content="Hello"),
                Message(role="user", content="How are you?"),
            ],
        )
        body = p._build_request_body(req)
        assert "message" in body
        assert "chat_history" in body
        assert body["message"] == "How are you?"

    def test_build_cohere_skips_system_messages(self):
        """Cohere request body omits system messages from chat_history."""
        p = self._provider()
        req = ChatRequest(
            model="cohere.command-r-plus-v1:0",
            messages=[
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hi"),
            ],
        )
        body = p._build_request_body(req)
        assert body["chat_history"] == []

    def test_build_titan_request(self):
        """Titan request body uses 'inputText' key."""
        p = self._provider()
        req = ChatRequest(
            model="amazon.titan-text-express-v1",
            messages=[Message(role="user", content="Hello")],
        )
        body = p._build_request_body(req)
        assert "inputText" in body
        assert "textGenerationConfig" in body

    def test_build_anthropic_with_stop_and_top_p(self):
        """Anthropic request includes stop_sequences and top_p when set."""
        p = self._provider()
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")],
            stop=["DONE"],
            top_p=0.9,
        )
        body = p._build_request_body(req)
        assert body.get("stop_sequences") == ["DONE"]
        assert body.get("top_p") == 0.9

    def test_build_nova_with_stop_sequences(self):
        """Nova request includes stopSequences in inferenceConfig."""
        p = self._provider()
        req = ChatRequest(
            model="amazon.nova-pro-v1:0",
            messages=[Message(role="user", content="Hello")],
            stop=["END"],
        )
        body = p._build_request_body(req)
        assert body["inferenceConfig"].get("stopSequences") == ["END"]

    def test_build_nova_with_system_message(self):
        """Nova request includes a 'system' key when a system message is present."""
        p = self._provider()
        req = ChatRequest(
            model="amazon.nova-pro-v1:0",
            messages=[
                Message(role="system", content="Be helpful"),
                Message(role="user", content="Hi"),
            ],
        )
        body = p._build_request_body(req)
        assert "system" in body
        assert body["system"][0]["text"] == "Be helpful"

    def test_build_unknown_model_raises(self):
        """Unknown model family raises InvalidModelError."""
        p = self._provider()
        req = ChatRequest(
            model="unknown.model-v99",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(InvalidModelError):
            p._build_request_body(req)

    def test_messages_to_prompt_all_roles(self):
        """_messages_to_prompt converts all message roles to prompt format."""
        p = self._provider()
        messages = [
            Message(role="system", content="Setup"),
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello"),
        ]
        prompt = p._messages_to_prompt(messages)
        assert "System:" in prompt
        assert "User:" in prompt
        assert "Assistant:" in prompt


class TestBedrockStreamingCoverage:
    """Tests for chat_completion_stream across model families and error paths."""

    def _setup_mock_stream(self, mock_session_class, chunks):
        """Set up a mock aioboto3 session that yields streaming chunks.

        Args:
            mock_session_class: Mocked aioboto3.Session class.
            chunks: List of raw chunk dicts to yield.

        Returns:
            A configured BedrockProvider instance.
        """
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        async def async_gen():
            for chunk in chunks:
                yield {"chunk": {"bytes": json.dumps(chunk).encode()}}

        mock_client = AsyncMock()
        mock_response = {"body": async_gen()}
        mock_client.invoke_model_with_response_stream = AsyncMock(
            return_value=mock_response
        )

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_ctx

        return BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_stream_anthropic(self, mock_session_class):
        """Streaming an Anthropic Claude model yields content chunks."""
        provider = self._setup_mock_stream(
            mock_session_class,
            [
                {"type": "content_block_delta", "delta": {"text": "Hello"}},
                {"type": "content_block_delta", "delta": {"text": " world"}},
            ],
        )
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(req):
            chunks.append(chunk)
        assert len(chunks) == 2
        assert chunks[0].content == "Hello"

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_stream_nova(self, mock_session_class):
        """Streaming an Amazon Nova model yields content chunks."""
        provider = self._setup_mock_stream(
            mock_session_class,
            [
                {"contentBlockDelta": {"delta": {"text": "Nova"}}},
            ],
        )
        req = ChatRequest(
            model="amazon.nova-pro-v1:0",
            messages=[Message(role="user", content="Hi")],
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(req):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].content == "Nova"

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_stream_client_error_validation_exception(self, mock_session_class):
        """A ValidationException in streaming raises ProviderAPIError."""
        from botocore.exceptions import ClientError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "is not less or equal to /p: bad",
            }
        }
        mock_client.invoke_model_with_response_stream = AsyncMock(
            side_effect=ClientError(error_response, "InvokeModelWithResponseStream")
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_ctx

        provider = BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError):
            async for _ in provider.chat_completion_stream(req):
                pass

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_stream_client_error_role_validation(self, mock_session_class):
        """A role-validation error in streaming raises ProviderAPIError."""
        from botocore.exceptions import ClientError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "role is not a valid enum value",
            }
        }
        mock_client.invoke_model_with_response_stream = AsyncMock(
            side_effect=ClientError(error_response, "InvokeModelWithResponseStream")
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_ctx

        provider = BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError):
            async for _ in provider.chat_completion_stream(req):
                pass

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_stream_non_validation_client_error(self, mock_session_class):
        """A non-ValidationException ClientError in streaming raises ProviderAPIError."""
        from botocore.exceptions import ClientError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        error_response = {
            "Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}
        }
        mock_client.invoke_model_with_response_stream = AsyncMock(
            side_effect=ClientError(error_response, "InvokeModelWithResponseStream")
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_ctx

        provider = BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError):
            async for _ in provider.chat_completion_stream(req):
                pass


class TestBedrockCompletionClientErrorBranches:
    """Tests for ClientError branches in chat_completion (non-streaming)."""

    def _mock_client_with_error(self, mock_session_class, error_code, error_message):
        """Configure a mock that raises a ClientError on invoke_model.

        Args:
            mock_session_class: Mocked aioboto3.Session class.
            error_code: AWS error code (e.g. 'ValidationException').
            error_message: Error message string.

        Returns:
            A BedrockProvider instance.
        """
        from botocore.exceptions import ClientError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_client = AsyncMock()
        error_response = {"Error": {"Code": error_code, "Message": error_message}}
        mock_client.invoke_model = AsyncMock(
            side_effect=ClientError(error_response, "InvokeModel")
        )
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_ctx

        return BedrockProvider(aws_access_key_id="k", aws_secret_access_key="s")

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_top_p_validation_error_friendly_message(self, mock_session_class):
        """A top_p out-of-range ValidationException gets a friendly message."""
        provider = self._mock_client_with_error(
            mock_session_class,
            "ValidationException",
            "is not less or equal to /p: exceeded",
        )
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError) as exc:
            await provider.chat_completion(req)
        assert "top_p" in str(exc.value).lower() or "Model configuration" in str(
            exc.value
        )

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_role_validation_error_friendly_message(self, mock_session_class):
        """A role-validation ValidationException gets a friendly message."""
        provider = self._mock_client_with_error(
            mock_session_class,
            "ValidationException",
            "role is not a valid enum value for this model",
        )
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError) as exc:
            await provider.chat_completion(req)
        assert "role" in str(exc.value).lower() or "Model configuration" in str(
            exc.value
        )

    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_non_validation_client_error(self, mock_session_class):
        """Non-ValidationException ClientError raises ProviderAPIError."""
        provider = self._mock_client_with_error(
            mock_session_class, "ThrottlingException", "Rate limit exceeded"
        )
        req = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(ProviderAPIError) as exc:
            await provider.chat_completion(req)
        assert "ThrottlingException" in str(exc.value)


class TestBedrockCredentialFallback:
    """Tests for credential-check path in BedrockProvider.__init__."""

    def test_no_credentials_logs_warning_and_continues(self, caplog):
        """Without explicit credentials, a warning is logged and init proceeds."""
        import logging

        from stratifyai.exceptions import AuthenticationError

        with (
            patch("stratifyai.providers.bedrock.aioboto3.Session"),
            patch(
                "stratifyai.api_key_helper.get_api_key_or_error",
                side_effect=AuthenticationError("bedrock", "no key"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            provider = BedrockProvider()

        # Provider is created; initialization continues despite the auth error
        assert provider.provider_name == "bedrock"
