"""Data models for unified LLM abstraction layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class Message:
    """Standard message format for all providers (OpenAI-compatible)."""
    role: Literal["system", "user", "assistant"]
    content: str  # Can be plain text or contain [IMAGE:mime_type]\nbase64_data format
    name: Optional[str] = None  # For multi-agent scenarios
    cache_control: Optional[dict] = None  # For providers that support prompt caching (Anthropic, OpenAI)
    
    def has_image(self) -> bool:
        """Check if message contains image data."""
        return "[IMAGE:" in self.content
    
    def parse_vision_content(self) -> tuple[Optional[str], Optional[tuple[str, str]]]:
        """Parse content into text and image data.
        
        Returns:
            (text_content, (mime_type, base64_data)) or (text_content, None) if no image
        """
        if not self.has_image():
            return (self.content, None)
        
        # Split content by [IMAGE:...] marker
        parts = self.content.split("[IMAGE:")
        text_parts = []
        image_data = None
        
        for i, part in enumerate(parts):
            if i == 0:
                # First part is text before image
                if part.strip():
                    text_parts.append(part.strip())
            else:
                # This part starts with mime_type]
                if "]" in part:
                    mime_type, rest = part.split("]", 1)
                    # rest contains the base64 data (possibly with leading/trailing whitespace)
                    base64_data = rest.strip()
                    if base64_data:
                        image_data = (mime_type.strip(), base64_data)
        
        text_content = "\n".join(text_parts).strip() if text_parts else None
        return (text_content, image_data)


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
