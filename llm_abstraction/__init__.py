"""StratumAI - Unified Intelligence Across Every Model Layer.

A production-ready Python module providing a unified, abstracted interface for
accessing multiple frontier LLM providers through a consistent API.
"""

__version__ = "0.1.0"

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
