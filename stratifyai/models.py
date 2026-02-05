"""Data models for unified LLM abstraction layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class Message:
    """Standard message format for all providers (OpenAI-compatible)."""
    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None  # For multi-agent scenarios
    cache_control: Optional[dict] = None  # For providers that support prompt caching (Anthropic, OpenAI)


@dataclass
class Usage:
    """Token usage and cost information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0  # Tokens retrieved from cache
    cache_creation_tokens: int = 0  # Tokens written to cache (Anthropic)
    cache_read_tokens: int = 0  # Tokens read from cache (Anthropic)
    reasoning_tokens: int = 0  # For reasoning models like o1/o3
    cost_usd: float = 0.0
    cost_breakdown: Optional[dict] = None  # Detailed cost breakdown by token type


@dataclass
class ChatRequest:
    """Unified request structure for chat completions."""
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    # Provider-specific extensions
    reasoning_effort: Optional[str] = None  # OpenAI o1/o3
    extra_params: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Standard response from any provider."""
    id: str
    model: str
    content: str
    finish_reason: str
    usage: Usage
    provider: str
    created_at: datetime
    raw_response: dict  # Original provider response for debugging
    latency_ms: Optional[float] = None  # Response latency in milliseconds
