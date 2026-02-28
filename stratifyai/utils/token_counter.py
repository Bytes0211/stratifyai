"""Token counting utilities for estimating LLM token usage."""

from typing import List, Optional
import tiktoken

from ..models import Message


def estimate_tokens(text: str, provider: str = "openai", model: Optional[str] = None) -> int:
    """
    Estimate the number of tokens in a text string.
    
    Uses provider-specific tokenizers when available, falls back to
    character-based estimation (1 token ≈ 4 characters).
    
    Args:
        text: The text to estimate tokens for
        provider: The LLM provider (openai, anthropic, google, etc.)
        model: Optional specific model name for more accurate counting
        
    Returns:
        Estimated number of tokens
        
    Examples:
        >>> estimate_tokens("Hello, world!", provider="openai")
        4
        >>> estimate_tokens("Hello, world!", provider="anthropic")
        3
    """
    if not text:
        return 0
    
    # OpenAI models - use tiktoken
    if provider == "openai":
        try:
            # Use model-specific encoding if provided
            if model:
                # Map common model names to encodings
                if model.startswith(("gpt-4", "gpt-3.5")):
                    encoding = tiktoken.encoding_for_model(model)
                elif model.startswith(("o1", "o3")):
                    # o1/o3 models use same encoding as gpt-4
                    encoding = tiktoken.encoding_for_model("gpt-4")
                else:
                    # Default to cl100k_base (gpt-4, gpt-3.5-turbo)
                    encoding = tiktoken.get_encoding("cl100k_base")
            else:
                # Default to cl100k_base
                encoding = tiktoken.get_encoding("cl100k_base")
            
            return len(encoding.encode(text))
        except Exception:
            # Fall back to character-based if tiktoken fails
            pass
    
    # Anthropic models - approximate with character count
    # Claude tokenizer is more aggressive than OpenAI
    # Roughly 1 token ≈ 3.5 characters for English text
    if provider == "anthropic":
        return int(len(text) / 3.5)
    
    # Google Gemini - similar to OpenAI
    if provider == "google":
        return int(len(text) / 4)
    
    # DeepSeek, Groq, Grok, OpenRouter - approximate with OpenAI encoding
    if provider in ["deepseek", "groq", "grok", "openrouter"]:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass
    
    # Ollama - local models, use conservative estimate
    if provider == "ollama":
        return int(len(text) / 4)
    
    # Default fallback: 1 token ≈ 4 characters
    return int(len(text) / 4)


def count_tokens_for_messages(messages: List[Message], provider: str = "openai", model: Optional[str] = None) -> int:
    """
    Count tokens for a list of messages, including formatting overhead.
    
    Different models have different formatting requirements that add tokens.
    This function accounts for those overheads.
    
    Args:
        messages: List of Message objects
        provider: The LLM provider
        model: Optional specific model name
        
    Returns:
        Total estimated token count including formatting
        
    Examples:
        >>> from stratifyai.models import Message
        >>> messages = [Message(role="user", content="Hello")]
        >>> count_tokens_for_messages(messages, provider="openai")
        7  # Content tokens + formatting tokens
    """
    if not messages:
        return 0
    
    # Count content tokens
    total_tokens = 0
    for message in messages:
        # Count message content
        total_tokens += estimate_tokens(message.content, provider, model)
        
        # Add role tokens
        total_tokens += estimate_tokens(message.role, provider, model)
    
    # Add formatting overhead per message
    # OpenAI format: <|start|>role\ncontent<|end|>\n
    # Roughly 4-7 tokens per message for formatting
    if provider == "openai":
        tokens_per_message = 4
        if model and model.startswith("gpt-3.5"):
            tokens_per_message = 4
        elif model and model.startswith("gpt-4"):
            tokens_per_message = 3
        total_tokens += tokens_per_message * len(messages)
        total_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>
    
    # Anthropic Messages API has minimal overhead
    elif provider == "anthropic":
        total_tokens += 2 * len(messages)  # Minimal formatting overhead
    
    # Other providers - approximate 3 tokens per message
    else:
        total_tokens += 3 * len(messages)
    
    return total_tokens


def get_context_window(provider: str, model: str) -> int:
    """
    Get the context window size for a specific model.
    
    Args:
        provider: The LLM provider
        model: The model name
        
    Returns:
        Context window size in tokens
    """
    from ..config import MODEL_CATALOG
    
    model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
    return model_info.get("context", 128000)  # Default to 128k


def check_token_limit(token_count: int, provider: str, model: str, threshold: float = 0.8) -> tuple[bool, int, float]:
    """
    Check if token count is approaching the model's context limit.
    
    Args:
        token_count: Number of tokens
        provider: The LLM provider
        model: The model name
        threshold: Warning threshold (default 0.8 = 80%)
        
    Returns:
        Tuple of (exceeds_threshold, context_window, percentage_used)
        
    Examples:
        >>> check_token_limit(100000, "openai", "gpt-4o", threshold=0.8)
        (False, 128000, 0.78125)
        >>> check_token_limit(110000, "openai", "gpt-4o", threshold=0.8)
        (True, 128000, 0.859375)
    """
    context_window = get_context_window(provider, model)
    
    # Check for API-imposed input limits (e.g., Claude Opus 4.5)
    from ..config import MODEL_CATALOG
    model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
    api_max_input = model_info.get("api_max_input")
    if api_max_input and api_max_input < context_window:
        context_window = api_max_input
    
    percentage_used = token_count / context_window if context_window > 0 else 1.0
    exceeds_threshold = percentage_used > threshold
    
    return exceeds_threshold, context_window, percentage_used
