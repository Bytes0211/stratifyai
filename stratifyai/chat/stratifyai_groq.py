"""Groq chat interface for StratifyAI.

Provides convenient functions for Groq chat completions.
Groq provides ultra-fast inference for open-source models.
Model must be specified for each request.

Environment Variable: GROQ_API_KEY

Usage:
    # Model is always required
    from stratifyai.chat import groq
    response = await groq.chat("Hello!", model="llama-3.3-70b-versatile")
    
    # Builder pattern (model required)
    client = (
        groq
        .with_model("mixtral-8x7b-32768")
        .with_system("You are a helpful assistant")
        .with_developer("Use markdown")
    )
    response = await client.chat("Hello!")
"""

import asyncio
from typing import AsyncIterator, Optional, Union

from stratifyai import LLMClient
from stratifyai.models import ChatResponse, Message
from stratifyai.chat.builder import ChatBuilder, create_module_builder

# Default configuration (no default model - must be specified)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = None

# Module-level client (lazy initialization)
_client: Optional[LLMClient] = None


def _get_client() -> LLMClient:
    """Get or create the module-level client."""
    global _client
    if _client is None:
        _client = LLMClient(provider="groq")
    return _client


# Module-level builder for chaining
_builder = create_module_builder(
    provider="groq",
    default_temperature=DEFAULT_TEMPERATURE,
    default_max_tokens=DEFAULT_MAX_TOKENS,
    client_factory=_get_client,
)


# Builder pattern methods (delegate to _builder)
def with_model(model: str) -> ChatBuilder:
    """Set the model to use. Returns a new ChatBuilder for chaining."""
    return _builder.with_model(model)


def with_system(prompt: str) -> ChatBuilder:
    """Set the system prompt. Returns a new ChatBuilder for chaining."""
    return _builder.with_system(prompt)


def with_developer(instructions: str) -> ChatBuilder:
    """Set developer instructions. Returns a new ChatBuilder for chaining."""
    return _builder.with_developer(instructions)


def with_temperature(temperature: float) -> ChatBuilder:
    """Set the temperature. Returns a new ChatBuilder for chaining."""
    return _builder.with_temperature(temperature)


def with_max_tokens(max_tokens: int) -> ChatBuilder:
    """Set max tokens. Returns a new ChatBuilder for chaining."""
    return _builder.with_max_tokens(max_tokens)


def with_options(**kwargs) -> ChatBuilder:
    """Set additional options. Returns a new ChatBuilder for chaining."""
    return _builder.with_options(**kwargs)


async def chat(
    prompt: Union[str, list[Message]],
    *,
    model: str,
    system: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    stream: bool = False,
    **kwargs,
) -> Union[ChatResponse, AsyncIterator[ChatResponse]]:
    """
    Send a chat completion request to Groq.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name (required). E.g., "llama-3.3-70b-versatile", "mixtral-8x7b-32768"
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-2.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        stream: Whether to stream the response. Default: False
        **kwargs: Additional parameters passed to the API.

    Returns:
        ChatResponse object, or AsyncIterator[ChatResponse] if streaming.

    Example:
        >>> from stratifyai.chat import groq
        >>> response = await groq.chat("What is Python?", model="llama-3.3-70b-versatile")
        >>> print(response.content)
    """
    client = _get_client()

    # Build messages list
    if isinstance(prompt, str):
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
    else:
        messages = prompt

    return await client.chat(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        **kwargs,
    )


async def chat_stream(
    prompt: Union[str, list[Message]],
    *,
    model: str,
    system: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs,
) -> AsyncIterator[ChatResponse]:
    """
    Send a streaming chat completion request to Groq.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name (required). E.g., "llama-3.3-70b-versatile"
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-2.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        **kwargs: Additional parameters passed to the API.

    Yields:
        ChatResponse chunks.

    Example:
        >>> from stratifyai.chat import groq
        >>> async for chunk in groq.chat_stream("Tell me a story", model="llama-3.3-70b-versatile"):
        ...     print(chunk.content, end="", flush=True)
    """
    return await chat(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )


def chat_sync(
    prompt,
    *,
    model: str,
    system=None,
    temperature=DEFAULT_TEMPERATURE,
    max_tokens=DEFAULT_MAX_TOKENS,
    **kwargs,
):
    """Synchronous wrapper for chat()."""
    return asyncio.run(chat(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
        **kwargs,
    ))
