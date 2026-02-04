"""Google Gemini chat interface for StratumAI.

Provides convenient functions for Google Gemini chat completions with sensible defaults.

Default Model: gemini-2.5-flash
Environment Variable: GOOGLE_API_KEY
"""

from typing import Iterator, Optional, Union

from llm_abstraction import LLMClient
from llm_abstraction.models import ChatResponse, Message

# Default configuration
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = None

# Module-level client (lazy initialization)
_client: Optional[LLMClient] = None


def _get_client() -> LLMClient:
    """Get or create the module-level client."""
    global _client
    if _client is None:
        _client = LLMClient(provider="google")
    return _client


def chat(
    prompt: Union[str, list[Message]],
    *,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    stream: bool = False,
    **kwargs,
) -> Union[ChatResponse, Iterator[ChatResponse]]:
    """
    Send a chat completion request to Google Gemini.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name. Default: gemini-2.5-flash
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-2.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        stream: Whether to stream the response. Default: False
        **kwargs: Additional parameters passed to the API.

    Returns:
        ChatResponse object, or Iterator[ChatResponse] if streaming.

    Example:
        >>> from chat import google
        >>> response = google.chat("What is Python?")
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

    return client.chat(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        **kwargs,
    )


def chat_stream(
    prompt: Union[str, list[Message]],
    *,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    **kwargs,
) -> Iterator[ChatResponse]:
    """
    Send a streaming chat completion request to Google Gemini.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name. Default: gemini-2.5-flash
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-2.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        **kwargs: Additional parameters passed to the API.

    Yields:
        ChatResponse chunks.

    Example:
        >>> from chat import google
        >>> for chunk in google.chat_stream("Tell me a story"):
        ...     print(chunk.content, end="", flush=True)
    """
    return chat(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )
