"""StratumAI - Unified Intelligence Across Every Model Layer.

A production-ready Python module providing a unified, abstracted interface for
accessing multiple frontier LLM providers through a consistent API.
"""

__version__ = "0.1.0"

from .caching import (
    ResponseCache,
    cache_response,
    clear_cache,
    generate_cache_key,
    get_cache_stats,
)
from .client import LLMClient, ProviderType
from .exceptions import (
    AuthenticationError,
    BudgetExceededError,
    InvalidModelError,
    InvalidProviderError,
    LLMAbstractionError,
    MaxRetriesExceededError,
    ProviderAPIError,
    ProviderError,
    RateLimitError,
    ValidationError,
)
from .models import ChatRequest, ChatResponse, Message, Usage
from .providers.base import BaseProvider
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.deepseek import DeepSeekProvider
from .providers.groq import GroqProvider
from .providers.grok import GrokProvider
from .providers.ollama import OllamaProvider
from .providers.openrouter import OpenRouterProvider

__all__ = [
    # Core client
    "LLMClient",
    "ProviderType",
    # Data models
    "Message",
    "ChatRequest",
    "ChatResponse",
    "Usage",
    # Providers
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "GroqProvider",
    "GrokProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    # Caching
    "ResponseCache",
    "cache_response",
    "generate_cache_key",
    "get_cache_stats",
    "clear_cache",
    # Exceptions
    "LLMAbstractionError",
    "ProviderError",
    "InvalidProviderError",
    "ProviderAPIError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidModelError",
    "BudgetExceededError",
    "MaxRetriesExceededError",
    "ValidationError",
]
