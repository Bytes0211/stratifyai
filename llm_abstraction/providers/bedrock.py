"""AWS Bedrock provider implementation."""

import json
import os
from datetime import datetime
from typing import AsyncIterator, List, Optional

try:
    import aioboto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
except ImportError:
    raise ImportError(
        "aioboto3 is required for AWS Bedrock async support. "
        "Install with: pip install aioboto3>=12.0.0"
    )

from ..config import BEDROCK_MODELS, PROVIDER_CONSTRAINTS
from ..exceptions import AuthenticationError, InvalidModelError, ProviderAPIError
from ..models import ChatRequest, ChatResponse, Usage
from .base import BaseProvider


class BedrockProvider(BaseProvider):
    """AWS Bedrock provider implementation using aioboto3 for async support."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,  # For compatibility with LLMClient (AWS_BEARER_TOKEN_BEDROCK)
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        region_name: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize AWS Bedrock provider.
        
        Args:
            api_key: AWS bearer token (defaults to AWS_BEARER_TOKEN_BEDROCK env var)
                    or for compatibility with LLMClient interface
            aws_access_key_id: AWS access key (defaults to AWS_ACCESS_KEY_ID env var)
            aws_secret_access_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY env var)
            aws_session_token: AWS session token (defaults to AWS_SESSION_TOKEN env var)
            region_name: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
            config: Optional provider-specific configuration
            
        Raises:
            ValueError: If AWS credentials are not available (with helpful setup instructions)
        """
        # AWS Bedrock supports multiple authentication methods:
        # 1. Bearer token (AWS_BEARER_TOKEN_BEDROCK)
        # 2. Access key + secret key (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
        # 3. IAM roles (when running on AWS infrastructure)
        # 4. ~/.aws/credentials file
        
        # Check for bearer token first (simplest method)
        bearer_token = api_key or os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        
        # Check for access key credentials
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        # Use APIKeyHelper for better error messages if no credentials found
        if not bearer_token and not (self.aws_access_key_id and self.aws_secret_access_key):
            from ..api_key_helper import get_api_key_or_error
            try:
                get_api_key_or_error("bedrock", bearer_token)
            except ValueError:
                # Allow to proceed if using IAM roles or ~/.aws/credentials
                # boto3 will handle the credential chain
                pass
        
        # BaseProvider expects api_key, so we'll use access_key_id as a placeholder
        # (Bedrock doesn't use API keys like other providers)
        super().__init__(self.aws_access_key_id or "aws-credentials", config)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize AWS Bedrock session for async client creation."""
        try:
            # Create aioboto3 session with explicit credentials if provided
            session_params = {"region_name": self.region_name}
            if self.aws_access_key_id and self.aws_secret_access_key:
                session_params["aws_access_key_id"] = self.aws_access_key_id
                session_params["aws_secret_access_key"] = self.aws_secret_access_key
                if self.aws_session_token:
                    session_params["aws_session_token"] = self.aws_session_token
            
            # Store session for async client creation
            # aioboto3 clients must be created within async context
            self._session = aioboto3.Session(**session_params)
            self._client = None  # Will be created in async context
            
        except NoCredentialsError:
            raise AuthenticationError(
                "AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "environment variables or configure ~/.aws/credentials"
            )
        except Exception as e:
            raise ProviderAPIError(
                f"Failed to initialize AWS Bedrock session: {str(e)}",
                "bedrock"
            )
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "bedrock"
    
    def get_supported_models(self) -> List[str]:
        """Return list of supported Bedrock models."""
        return list(BEDROCK_MODELS.keys())
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion request using Bedrock.
        
        Args:
            request: Unified chat request
            
        Returns:
            Unified chat response with cost tracking
            
        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        if not self.validate_model(request.model):
            raise InvalidModelError(request.model, self.provider_name)
        
        # Validate temperature constraints for Bedrock (0.0 to 1.0)
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 1.0)
        )
        
        # Build request body based on model family
        body = self._build_request_body(request)
        
        try:
            # Create async client and invoke Bedrock model
            async with self._session.client("bedrock-runtime") as client:
                response = await client.invoke_model(
                    modelId=request.model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body)
                )
                
                # Parse response - aioboto3 returns StreamingBody
                response_body_bytes = await response["body"].read()
                response_body = json.loads(response_body_bytes)
                
                # Normalize response based on model family
                return self._normalize_response(response_body, request.model)
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            raise ProviderAPIError(
                f"Bedrock API error ({error_code}): {error_message}",
                self.provider_name
            )
        except Exception as e:
            raise ProviderAPIError(
                f"Chat completion failed: {str(e)}",
                self.provider_name
            )
    
    async def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """
        Execute streaming chat completion request.
        
        Args:
            request: Unified chat request
            
        Yields:
            Unified chat response chunks
            
        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        if not self.validate_model(request.model):
            raise InvalidModelError(request.model, self.provider_name)
        
        # Validate temperature constraints
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 1.0)
        )
        
        # Build request body
        body = self._build_request_body(request)
        
        try:
            # Create async client and invoke Bedrock model with streaming
            async with self._session.client("bedrock-runtime") as client:
                response = await client.invoke_model_with_response_stream(
                    modelId=request.model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body)
                )
                
                # Process streaming response
                stream = response.get("body")
                if stream:
                    async for event in stream:
                        chunk_data = event.get("chunk")
                        if chunk_data:
                            chunk = json.loads(chunk_data["bytes"].decode())
                            yield self._normalize_stream_chunk(chunk, request.model)
                        
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            raise ProviderAPIError(
                f"Bedrock streaming error ({error_code}): {error_message}",
                self.provider_name
            )
        except Exception as e:
            raise ProviderAPIError(
                f"Streaming chat completion failed: {str(e)}",
                self.provider_name
            )
    
    def _build_request_body(self, request: ChatRequest) -> dict:
        """
        Build request body based on model family.
        
        Different Bedrock models have different request formats:
        - Anthropic Claude: Uses Messages API format
        - Meta Llama: Uses prompt-based format
        - Mistral: Uses messages format
        - Cohere: Uses prompt-based format
        - Amazon Titan: Uses inputText format
        
        Args:
            request: Unified chat request
            
        Returns:
            Model-specific request body
        """
        model_id = request.model
        
        # Anthropic Claude models
        if model_id.startswith("anthropic.claude"):
            return self._build_anthropic_request(request)
        
        # Meta Llama models
        elif model_id.startswith("meta.llama"):
            return self._build_llama_request(request)
        
        # Mistral models
        elif model_id.startswith("mistral."):
            return self._build_mistral_request(request)
        
        # Cohere models
        elif model_id.startswith("cohere."):
            return self._build_cohere_request(request)
        
        # Amazon Nova models (new generation)
        elif model_id.startswith("amazon.nova"):
            return self._build_nova_request(request)
        
        # Amazon Titan models (legacy)
        elif model_id.startswith("amazon.titan"):
            return self._build_titan_request(request)
        
        else:
            raise InvalidModelError(
                f"Unknown model family for {model_id}",
                self.provider_name
            )
    
    def _build_anthropic_request(self, request: ChatRequest) -> dict:
        """Build request for Anthropic Claude models."""
        # Separate system message from conversation
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        
        if system_message:
            body["system"] = system_message
        
        if request.top_p != 1.0:
            body["top_p"] = request.top_p
        
        if request.stop:
            body["stop_sequences"] = request.stop
        
        return body
    
    def _build_llama_request(self, request: ChatRequest) -> dict:
        """Build request for Meta Llama models."""
        # Llama uses a prompt-based format
        prompt = self._messages_to_prompt(request.messages)
        
        return {
            "prompt": prompt,
            "max_gen_len": request.max_tokens or 2048,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
    
    def _build_mistral_request(self, request: ChatRequest) -> dict:
        """Build request for Mistral models."""
        # Convert to prompt format
        prompt = self._messages_to_prompt(request.messages)
        
        return {
            "prompt": prompt,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
    
    def _build_cohere_request(self, request: ChatRequest) -> dict:
        """Build request for Cohere models."""
        # Cohere uses a message-based format similar to OpenAI
        messages = []
        for msg in request.messages:
            messages.append({"role": msg.role, "message": msg.content})
        
        return {
            "message": messages[-1]["message"] if messages else "",
            "chat_history": messages[:-1] if len(messages) > 1 else [],
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature,
            "p": request.top_p,
        }
    
    def _build_nova_request(self, request: ChatRequest) -> dict:
        """Build request for Amazon Nova models."""
        # Nova uses messages API similar to Claude
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": [{"text": msg.content}]})
        
        body = {
            "messages": messages,
            "inferenceConfig": {
                "max_new_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "top_p": request.top_p,
            },
            "schemaVersion": "messages-v1",
        }
        
        if system_message:
            body["system"] = [{"text": system_message}]
        
        if request.stop:
            body["inferenceConfig"]["stopSequences"] = request.stop
        
        return body
    
    def _build_titan_request(self, request: ChatRequest) -> dict:
        """Build request for Amazon Titan models."""
        # Titan uses inputText format
        prompt = self._messages_to_prompt(request.messages)
        
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": request.max_tokens or 2048,
                "temperature": request.temperature,
                "topP": request.top_p,
                "stopSequences": request.stop or [],
            }
        }
    
    def _messages_to_prompt(self, messages: List) -> str:
        """
        Convert message list to a single prompt string.
        
        Args:
            messages: List of Message objects
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        return "\n\n".join(prompt_parts) + "\n\nAssistant:"
    
    def _normalize_response(self, raw_response: dict, model: str) -> ChatResponse:
        """
        Convert Bedrock response to unified format.
        
        Args:
            raw_response: Raw Bedrock API response
            model: Model ID used
            
        Returns:
            Normalized ChatResponse with cost
        """
        # Parse response based on model family
        if model.startswith("anthropic.claude"):
            content = self._parse_anthropic_response(raw_response)
            usage = self._extract_anthropic_usage(raw_response)
            finish_reason = raw_response.get("stop_reason", "stop")
        
        elif model.startswith("meta.llama"):
            content = raw_response.get("generation", "")
            usage = self._extract_llama_usage(raw_response, content, model)
            finish_reason = raw_response.get("stop_reason", "stop")
        
        elif model.startswith("mistral."):
            content = raw_response.get("outputs", [{}])[0].get("text", "")
            usage = self._estimate_usage(content, model)
            finish_reason = raw_response.get("stop_reason", "stop")
        
        elif model.startswith("cohere."):
            content = raw_response.get("text", "")
            usage = self._extract_cohere_usage(raw_response, model)
            finish_reason = raw_response.get("finish_reason", "COMPLETE")
        
        elif model.startswith("amazon.nova"):
            content = self._parse_nova_response(raw_response)
            usage = self._extract_nova_usage(raw_response)
            finish_reason = raw_response.get("stopReason", "end_turn")
        
        elif model.startswith("amazon.titan"):
            content = raw_response.get("results", [{}])[0].get("outputText", "")
            usage = self._extract_titan_usage(raw_response, model)
            finish_reason = raw_response.get("results", [{}])[0].get("completionReason", "FINISH")
        
        else:
            content = str(raw_response)
            usage = Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            finish_reason = "stop"
        
        # Calculate cost
        cost = self._calculate_cost(usage, model)
        usage.cost_usd = cost
        
        return ChatResponse(
            id=raw_response.get("id", f"bedrock-{datetime.now().timestamp()}"),
            model=model,
            content=content,
            finish_reason=finish_reason,
            usage=usage,
            provider=self.provider_name,
            created_at=datetime.now(),
            raw_response=raw_response
        )
    
    def _parse_anthropic_response(self, response: dict) -> str:
        """Extract content from Anthropic Claude response."""
        content = ""
        if response.get("content"):
            for block in response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")
        return content
    
    def _extract_anthropic_usage(self, response: dict) -> Usage:
        """Extract usage from Anthropic Claude response."""
        usage_data = response.get("usage", {})
        return Usage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
        )
    
    def _extract_llama_usage(self, response: dict, content: str, model: str) -> Usage:
        """Extract or estimate usage for Llama models."""
        # Llama doesn't always return token counts, so we estimate
        prompt_tokens = response.get("prompt_token_count", 0)
        completion_tokens = response.get("generation_token_count", 0)
        
        # If not provided, estimate (rough: 1 token ≈ 4 characters)
        if completion_tokens == 0 and content:
            completion_tokens = len(content) // 4
        
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    def _extract_cohere_usage(self, response: dict, model: str) -> Usage:
        """Extract usage from Cohere response."""
        # Cohere may not always provide token counts
        prompt_tokens = response.get("prompt_tokens", 0)
        completion_tokens = response.get("generation_tokens", 0)
        
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    def _parse_nova_response(self, response: dict) -> str:
        """Extract content from Amazon Nova response."""
        content = ""
        output = response.get("output", {})
        if output.get("message"):
            for block in output["message"].get("content", []):
                if block.get("text"):
                    content += block["text"]
        return content
    
    def _extract_nova_usage(self, response: dict) -> Usage:
        """Extract usage from Amazon Nova response."""
        usage_data = response.get("usage", {})
        return Usage(
            prompt_tokens=usage_data.get("inputTokens", 0),
            completion_tokens=usage_data.get("outputTokens", 0),
            total_tokens=usage_data.get("totalTokens", 0)
        )
    
    def _extract_titan_usage(self, response: dict, model: str) -> Usage:
        """Extract usage from Titan response."""
        result = response.get("results", [{}])[0]
        prompt_tokens = result.get("inputTextTokenCount", 0)
        completion_tokens = result.get("outputTextTokenCount", 0)
        
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    def _estimate_usage(self, content: str, model: str) -> Usage:
        """Estimate token usage when not provided by API."""
        # Rough estimation: 1 token ≈ 4 characters
        completion_tokens = len(content) // 4
        
        return Usage(
            prompt_tokens=0,  # Can't estimate prompt tokens without request
            completion_tokens=completion_tokens,
            total_tokens=completion_tokens
        )
    
    def _normalize_stream_chunk(self, chunk: dict, model: str) -> ChatResponse:
        """
        Convert streaming chunk to unified format.
        
        Args:
            chunk: Raw streaming chunk
            model: Model ID used
            
        Returns:
            Normalized ChatResponse chunk
        """
        # Parse chunk based on model family
        if model.startswith("anthropic.claude"):
            if chunk.get("type") == "content_block_delta":
                content = chunk.get("delta", {}).get("text", "")
            else:
                content = ""
        elif model.startswith("meta.llama"):
            content = chunk.get("generation", "")
        elif model.startswith("mistral."):
            content = chunk.get("outputs", [{}])[0].get("text", "")
        elif model.startswith("amazon.nova"):
            # Nova streaming format
            if chunk.get("contentBlockDelta"):
                content = chunk["contentBlockDelta"].get("delta", {}).get("text", "")
            else:
                content = ""
        elif model.startswith("amazon.titan"):
            content = chunk.get("outputText", "")
        else:
            content = ""
        
        return ChatResponse(
            id=f"bedrock-stream-{datetime.now().timestamp()}",
            model=model,
            content=content,
            finish_reason="",
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            provider=self.provider_name,
            created_at=datetime.now(),
            raw_response=chunk
        )
    
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """
        Calculate cost for Bedrock request.
        
        Args:
            usage: Token usage information
            model: Model ID used
            
        Returns:
            Cost in USD
        """
        model_info = BEDROCK_MODELS.get(model, {})
        
        # Get cost per million tokens
        input_cost_per_mtok = model_info.get("cost_input", 0.0)
        output_cost_per_mtok = model_info.get("cost_output", 0.0)
        
        # Calculate cost
        input_cost = (usage.prompt_tokens / 1_000_000) * input_cost_per_mtok
        output_cost = (usage.completion_tokens / 1_000_000) * output_cost_per_mtok
        
        return input_cost + output_cost
