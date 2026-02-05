"""StratifyAI - Unified Intelligence Across Every Model Layer.

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
    InsufficientBalanceError,
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
from .cost_tracker import CostTracker, CostEntry
from .retry import RetryConfig, with_retry
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.deepseek import DeepSeekProvider
from .providers.groq import GroqProvider
from .providers.grok import GrokProvider
from .providers.ollama import OllamaProvider
from .providers.openrouter import OpenRouterProvider
from .providers.bedrock import BedrockProvider
from .router import Router, RoutingStrategy, ModelMetadata
from .embeddings import (
    EmbeddingProvider,
    EmbeddingResult,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
)
from .vectordb import VectorDBClient, SearchResult
from .rag import RAGClient, RAGResponse, IndexingResult

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
    "BedrockProvider",
    # Caching
    "ResponseCache",
    "cache_response",
    "generate_cache_key",
    "get_cache_stats",
    "clear_cache",
    # Cost Tracking
    "CostTracker",
    "CostEntry",
    # Retry
    "RetryConfig",
    "with_retry",
    # Router
    "Router",
    "RoutingStrategy",
    "ModelMetadata",
    # Embeddings
    "EmbeddingProvider",
    "EmbeddingResult",
    "OpenAIEmbeddingProvider",
    "create_embedding_provider",
    # Vector Database
    "VectorDBClient",
    "SearchResult",
    # RAG
    "RAGClient",
    "RAGResponse",
    "IndexingResult",
    # Exceptions
    "LLMAbstractionError",
    "ProviderError",
    "InvalidProviderError",
    "ProviderAPIError",
    "AuthenticationError",
    "InsufficientBalanceError",
    "RateLimitError",
    "InvalidModelError",
    "BudgetExceededError",
    "MaxRetriesExceededError",
    "ValidationError",
]
