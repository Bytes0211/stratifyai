"""Unit tests for data models."""

from datetime import datetime

import pytest

from stratifyai.models import ChatRequest, ChatResponse, Message, Usage


class TestMessage:
    """Tests for Message dataclass."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(role="user", content="Hello, world!")
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.name is None
    
    def test_message_with_name(self):
        """Test message with name field."""
        msg = Message(role="assistant", content="Hi!", name="bot")
        assert msg.role == "assistant"
        assert msg.content == "Hi!"
        assert msg.name == "bot"


class TestUsage:
    """Tests for Usage dataclass."""
    
    def test_usage_basic(self):
        """Test basic usage creation."""
        usage = Usage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.cached_tokens == 0
        assert usage.reasoning_tokens == 0
        assert usage.cost_usd == 0.0
    
    def test_usage_with_cost(self):
        """Test usage with cost tracking."""
        usage = Usage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cost_usd=0.05
        )
        assert usage.cost_usd == 0.05
    
    def test_usage_with_reasoning_tokens(self):
        """Test usage with reasoning tokens (o1/o3 models)."""
        usage = Usage(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            reasoning_tokens=150
        )
        assert usage.reasoning_tokens == 150


class TestChatRequest:
    """Tests for ChatRequest dataclass."""
    
    def test_request_minimal(self):
        """Test minimal request creation."""
        messages = [Message(role="user", content="Hello")]
        request = ChatRequest(model="gpt-4.1-mini", messages=messages)
        
        assert request.model == "gpt-4.1-mini"
        assert len(request.messages) == 1
        assert request.temperature == 0.7  # Default
        assert request.max_tokens is None
        assert request.stream is False
    
    def test_request_with_params(self):
        """Test request with all parameters."""
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello")
        ]
        request = ChatRequest(
            model="gpt-5",
            messages=messages,
            temperature=0.5,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stop=["END"]
        )
        
        assert request.model == "gpt-5"
        assert len(request.messages) == 2
        assert request.temperature == 0.5
        assert request.max_tokens == 1000
        assert request.top_p == 0.9
        assert request.frequency_penalty == 0.5
        assert request.presence_penalty == 0.5
        assert request.stop == ["END"]
    
    def test_request_with_reasoning_effort(self):
        """Test request with reasoning_effort for o-series models."""
        messages = [Message(role="user", content="Solve this")]
        request = ChatRequest(
            model="o1",
            messages=messages,
            reasoning_effort="high"
        )
        assert request.reasoning_effort == "high"


class TestChatResponse:
    """Tests for ChatResponse dataclass."""
    
    def test_response_creation(self):
        """Test response creation."""
        usage = Usage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost_usd=0.001
        )
        
        response = ChatResponse(
            id="chatcmpl-123",
            model="gpt-4.1-mini",
            content="Hello, how can I help?",
            finish_reason="stop",
            usage=usage,
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-4.1-mini"
        assert response.content == "Hello, how can I help?"
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens == 30
        assert response.provider == "openai"
        assert isinstance(response.created_at, datetime)
