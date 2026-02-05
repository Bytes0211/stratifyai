"""Tests for AWS Bedrock provider."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from stratifyai.providers.bedrock import BedrockProvider
from stratifyai.models import ChatRequest, Message, Usage
from stratifyai.exceptions import AuthenticationError, InvalidModelError, ProviderAPIError


class TestBedrockProviderInitialization:
    """Tests for Bedrock provider initialization."""
    
    def test_initialization_with_credentials(self):
        """Test provider initialization with explicit AWS credentials."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key-id",
                aws_secret_access_key="test-secret-key"
            )
            assert provider.aws_access_key_id == "test-key-id"
            assert provider.aws_secret_access_key == "test-secret-key"
            assert provider.region_name == "us-east-1"  # default
            assert provider.provider_name == "bedrock"
    
    def test_initialization_with_env_vars(self):
        """Test provider initialization with environment variables."""
        with patch.dict("os.environ", {
            "AWS_ACCESS_KEY_ID": "env-key-id",
            "AWS_SECRET_ACCESS_KEY": "env-secret-key",
            "AWS_DEFAULT_REGION": "us-west-2"
        }):
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
                region_name="eu-west-1"
            )
            assert provider.region_name == "eu-west-1"
    
    def test_initialization_with_session_token(self):
        """Test provider initialization with session token."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                aws_session_token="test-token"
            )
            assert provider.aws_session_token == "test-token"
    
    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def test_initialization_creates_session(self, mock_session_class):
        """Test that initialization creates aioboto3 session."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
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
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            models = provider.get_supported_models()
            
            assert isinstance(models, list)
            assert len(models) > 0
            
            # Check for key models from each family
            assert "anthropic.claude-3-5-sonnet-20241022-v2:0" in models
            assert "meta.llama3-3-70b-instruct-v1:0" in models
            assert "mistral.mistral-large-2402-v1:0" in models
            assert "amazon.titan-tg1-large" in models
            assert "cohere.command-r-plus-v1:0" in models
    
    def test_validate_model(self):
        """Test model validation."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            
            # Valid models
            assert provider.validate_model("anthropic.claude-3-5-sonnet-20241022-v2:0") is True
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
        mock_body.read = AsyncMock(return_value=json.dumps({
            "id": "msg_123",
            "content": [{"type": "text", "text": "Hello from Bedrock!"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5
            }
        }).encode())
        
        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})
        
        # Mock the async context manager for session.client()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager
        
        # Create provider and make request
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")]
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
        mock_body.read = AsyncMock(return_value=json.dumps({
            "generation": "Llama response!",
            "prompt_token_count": 10,
            "generation_token_count": 8,
            "stop_reason": "stop"
        }).encode())
        
        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})
        
        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="meta.llama3-3-70b-instruct-v1:0",
            messages=[Message(role="user", content="Hello")]
        )
        
        response = await provider.chat_completion(request)
        
        assert response.content == "Llama response!"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 8
    
    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    @pytest.mark.asyncio
    async def test_chat_completion_titan(self, mock_session_class):
        """Test chat completion with Amazon Titan model."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Create mock client with async invoke_model
        mock_client = AsyncMock()
        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=json.dumps({
            "results": [{
                "outputText": "Titan response!",
                "inputTextTokenCount": 12,
                "outputTextTokenCount": 6,
                "completionReason": "FINISH"
            }]
        }).encode())
        
        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})
        
        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="amazon.titan-tg1-large",
            messages=[Message(role="user", content="Hello")]
        )
        
        response = await provider.chat_completion(request)
        
        assert response.content == "Titan response!"
        assert response.usage.prompt_tokens == 12
        assert response.usage.completion_tokens == 6
    
    @pytest.mark.asyncio
    async def test_chat_completion_invalid_model(self):
        """Test chat completion with invalid model raises error."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="invalid-model",
                messages=[Message(role="user", content="Hello")]
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
        mock_body.read = AsyncMock(return_value=json.dumps({
            "content": [{"type": "text", "text": "Response"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 5}
        }).encode())
        
        mock_client.invoke_model = AsyncMock(return_value={"body": mock_body})
        
        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hello")
            ]
        )
        
        response = await provider.chat_completion(request)


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
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="invalid-model",
                messages=[Message(role="user", content="Hello")],
                stream=True
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
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            
            usage = Usage(
                prompt_tokens=1000,
                completion_tokens=500,
                total_tokens=1500
            )
            
            cost = provider._calculate_cost(usage, "anthropic.claude-3-5-sonnet-20241022-v2:0")
            
            # Claude 3.5 Sonnet pricing: $3/MTok input, $15/MTok output
            expected_cost = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
            assert cost == pytest.approx(expected_cost)
    
    def test_calculate_cost_llama(self):
        """Test cost calculation for Llama model."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            
            usage = Usage(
                prompt_tokens=2000,
                completion_tokens=1000,
                total_tokens=3000
            )
            
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
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")],
            temperature=0.8,
            max_tokens=1000
        )
        
        body = provider._build_request_body(request)
        
        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["messages"] == [{"role": "user", "content": "Hello"}]
        assert body["max_tokens"] == 1000
        assert body["temperature"] == 0.8
    
    @patch("stratifyai.providers.bedrock.aioboto3.Session")
    def test_build_titan_request(self, mock_session_class):
        """Test building request body for Amazon Titan."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="amazon.titan-tg1-large",
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
            max_tokens=500
        )
        
        body = provider._build_request_body(request)
        
        assert "inputText" in body
        assert body["textGenerationConfig"]["maxTokenCount"] == 500
        assert body["textGenerationConfig"]["temperature"] == 0.7


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
            "Error": {
                "Code": "ValidationException",
                "Message": "Invalid request"
            }
        }
        mock_client.invoke_model = AsyncMock(side_effect=ClientError(error_response, "InvokeModel"))
        
        # Mock the async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.client.return_value = mock_context_manager
        
        provider = BedrockProvider(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret"
        )
        request = ChatRequest(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[Message(role="user", content="Hello")]
        )
        
        with pytest.raises(ProviderAPIError) as exc_info:
            await provider.chat_completion(request)
        
        assert "ValidationException" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_temperature_validation(self):
        """Test temperature validation for Bedrock (0.0-1.0)."""
        with patch("stratifyai.providers.bedrock.aioboto3.Session"):
            provider = BedrockProvider(
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            request = ChatRequest(
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                messages=[Message(role="user", content="Hello")],
                temperature=2.0  # Invalid for Bedrock
            )
            
            from stratifyai.exceptions import ValidationError
            with pytest.raises(ValidationError):
                await provider.chat_completion(request)
