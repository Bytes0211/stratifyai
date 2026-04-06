"""StratifyAI - Unified Intelligence Across Every Model Layer.

A production-ready Python module providing a unified, abstracted interface for
accessing multiple frontier LLM providers through a consistent API.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stratifyai")
except PackageNotFoundError:
    __version__ = "2.0.0"

from .caching import (
    PersistentResponseCache,
    ResponseCache,
    cache_response,
    clear_cache,
    generate_cache_key,
    get_cache_stats,
)
from .catalog_manager import get_catalog_version, load_catalog
from .client import LLMClient, ProviderType, close_all_providers
from .cost_tracker import CostEntry, CostTracker
from .embeddings import (
    EmbeddingProvider,
    EmbeddingResult,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
)
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
from .logging_config import configure_logging
from .models import ChatRequest, ChatResponse, Message, Usage
from .prompts import PromptParameter, PromptRegistry, PromptTemplate, registry
from .providers.anthropic import AnthropicProvider
from .providers.base import BaseProvider
from .providers.bedrock import BedrockProvider
from .providers.deepseek import DeepSeekProvider
from .providers.google import GoogleProvider
from .providers.grok import GrokProvider
from .providers.groq import GroqProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .providers.openrouter import OpenRouterProvider
from .rag import IndexingResult, RAGClient, RAGResponse
from .retry import RetryConfig, with_retry
from .router import ModelMetadata, Router, RoutingStrategy
from .utils.model_selector import ModelSelector
from .utils.reasoning_detector import is_reasoning_model
from .utils.token_counter import count_tokens_for_messages as count_tokens
from .utils.token_counter import estimate_tokens
from .vectordb import SearchResult, VectorDBClient

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
    "PersistentResponseCache",
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
    # Prompt Templates
    "PromptParameter",
    "PromptTemplate",
    "PromptRegistry",
    "registry",
    # Utilities
    "count_tokens",
    "estimate_tokens",
    "ModelSelector",
    "is_reasoning_model",
    "get_catalog_version",
    "load_catalog",
    "configure_logging",
    "close_all_providers",
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
