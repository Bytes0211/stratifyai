"""StratifyAI - Unified Intelligence Across Every Model Layer.

A production-ready Python module providing a unified, abstracted interface for
accessing multiple frontier LLM providers through a consistent API.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stratifyai")
except PackageNotFoundError:
    __version__ = "0.1.3"

from .caching import (
    PersistentResponseCache,
    ResponseCache,
    cache_response,
    clear_cache,
    generate_cache_key,
    get_cache_stats,
)
from .client import LLMClient, ProviderType, close_all_providers
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
from .utils.token_counter import count_tokens_for_messages as count_tokens, estimate_tokens
from .utils.model_selector import ModelSelector
from .utils.reasoning_detector import is_reasoning_model
from .catalog_manager import get_catalog_version, load_catalog
from .logging_config import configure_logging
from .embeddings import (
    EmbeddingProvider,
    EmbeddingResult,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
)
from .vectordb import VectorDBClient, SearchResult
from .rag import RAGClient, RAGResponse, IndexingResult
from .prompts import PromptParameter, PromptTemplate, PromptRegistry, registry

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
