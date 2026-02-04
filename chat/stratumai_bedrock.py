"""AWS Bedrock chat interface for StratumAI.

Provides convenient functions for AWS Bedrock chat completions with sensible defaults.

Default Model: anthropic.claude-3-5-sonnet-20241022-v2:0
Requires: AWS credentials (env vars, ~/.aws/credentials, or IAM role)
"""

from typing import Iterator, Optional, Union

from llm_abstraction import LLMClient
from llm_abstraction.models import ChatResponse, Message

# Default configuration
DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = None

# Module-level client (lazy initialization)
_client: Optional[LLMClient] = None


def _get_client() -> LLMClient:
    """Get or create the module-level client."""
    global _client
    if _client is None:
        _client = LLMClient(provider="bedrock")
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
    Send a chat completion request to AWS Bedrock.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name. Default: anthropic.claude-3-5-sonnet-20241022-v2:0
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-1.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        stream: Whether to stream the response. Default: False
        **kwargs: Additional parameters passed to the API.

    Returns:
        ChatResponse object, or Iterator[ChatResponse] if streaming.

    Example:
        >>> from chat import bedrock
        >>> response = bedrock.chat("What is Python?")
        >>> print(response.content)

        # Use a different model
        >>> response = bedrock.chat(
        ...     "Explain AI",
        ...     model="meta.llama3-3-70b-instruct-v1:0"
        ... )
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
    Send a streaming chat completion request to AWS Bedrock.

    Args:
        prompt: User message string or list of Message objects.
        model: Model name. Default: anthropic.claude-3-5-sonnet-20241022-v2:0
        system: Optional system prompt (ignored if prompt is list of Messages).
        temperature: Sampling temperature (0.0-1.0). Default: 0.7
        max_tokens: Maximum tokens to generate. Default: None (model default)
        **kwargs: Additional parameters passed to the API.

    Yields:
        ChatResponse chunks.

    Example:
        >>> from chat import bedrock
        >>> for chunk in bedrock.chat_stream("Tell me a story"):
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
