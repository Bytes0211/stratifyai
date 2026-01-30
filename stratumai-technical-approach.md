# StratumAI - Unified Intelligence Across Every Model Layer

Technical Approach: Multi-Provider LLM API Abstraction Module

## Executive Summary

This document outlines the technical approach for building StratumAI, a production-ready Python module that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama) through a consistent API, eliminating vendor lock-in and simplifying multi-model development.

**Core Goals:**
- Single unified interface for all providers
- Zero code changes when switching models
- Automatic fallback and retry logic
- Cost tracking and usage monitoring
- Type-safe, well-documented API
- Production-ready error handling
- Support for advanced features (streaming, caching, function calling)

---

## Architecture Overview

### 1. Core Design Principles

**Abstraction First**: Hide provider-specific differences behind a unified interface
- Normalize request/response schemas
- Standardize authentication patterns
- Consistent error handling
- Unified streaming interface

**Provider Strategy Pattern**: Each provider implements a common interface
- Base abstract class defines contract
- Provider-specific implementations handle API differences
- Factory pattern for provider instantiation

**Configuration-Driven**: All provider details externalized
- Model catalogs with metadata
- Cost tables for tracking
- Capability matrices (context limits, features)
- Environment-based API key management

---

## Module Structure

```
llm_abstraction/
├── __init__.py
├── client.py              # Main unified client
├── providers/
│   ├── __init__.py
│   ├── base.py           # Abstract base provider
│   ├── openai.py         # OpenAI implementation
│   ├── anthropic.py      # Anthropic implementation
│   ├── google.py         # Google Gemini implementation
│   ├── deepseek.py       # DeepSeek implementation
│   ├── groq.py           # Groq implementation
│   ├── grok.py           # Grok (X.AI) implementation
│   ├── openrouter.py     # OpenRouter implementation
│   └── ollama.py         # Ollama local models
├── models.py             # Data models (Message, Response, Usage)
├── config.py             # Configuration and metadata
├── exceptions.py         # Custom exceptions
├── utils.py              # Helper functions
└── router.py             # Optional: intelligent routing (future)
```

---

## 2. Core Components

### 2.1 Unified Message Format

All providers use OpenAI-compatible message format:

```python
from typing import Literal, TypedDict, Optional, List
from dataclasses import dataclass

class Message(TypedDict):
    """Standard message format for all providers."""
    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str]  # For multi-agent scenarios

@dataclass
class ChatRequest:
    """Unified request structure."""
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
    extra_params: dict = None
```

### 2.2 Unified Response Format

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Usage:
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0  # For reasoning models
    cost_usd: float = 0.0

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
    raw_response: dict  # Original provider response
```

### 2.3 Base Provider Interface

```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional

class BaseProvider(ABC):
    """Abstract base class that all providers must implement."""
    
    def __init__(self, api_key: str, config: dict = None):
        """Initialize provider with API key and optional config."""
        self.api_key = api_key
        self.config = config or {}
        self._client = None
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider-specific client."""
        pass
    
    @abstractmethod
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat completion request."""
        pass
    
    @abstractmethod
    def chat_completion_stream(
        self, request: ChatRequest
    ) -> Iterator[ChatResponse]:
        """Execute a streaming chat completion request."""
        pass
    
    @abstractmethod
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """Convert provider-specific response to unified format."""
        pass
    
    @abstractmethod
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """Calculate cost for the request."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    def validate_model(self, model: str) -> bool:
        """Check if model is supported by this provider."""
        return model in self.get_supported_models()
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Return list of models supported by this provider."""
        pass
```

### 2.4 Provider Implementation Example: OpenAI

```python
from openai import OpenAI
from typing import Iterator, List
import os

class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""
    
    MODELS = {
        "gpt-5": {"context": 128000, "cost_input": 10.0, "cost_output": 30.0},
        "gpt-5-mini": {"context": 128000, "cost_input": 2.0, "cost_output": 6.0},
        "gpt-5-nano": {"context": 128000, "cost_input": 1.0, "cost_output": 3.0},
        "gpt-4.1": {"context": 128000, "cost_input": 2.5, "cost_output": 10.0},
        "gpt-4.1-mini": {"context": 128000, "cost_input": 0.15, "cost_output": 0.60},
    }
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        config: dict = None
    ):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        super().__init__(api_key, config)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client."""
        self._client = OpenAI(api_key=self.api_key)
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def get_supported_models(self) -> List[str]:
        return list(self.MODELS.keys())
    
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute chat completion."""
        if not self.validate_model(request.model):
            raise ValueError(
                f"Model {request.model} not supported by OpenAI"
            )
        
        # Build OpenAI-specific request
        openai_params = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop,
        }
        
        # Add reasoning_effort for o-series models
        if request.reasoning_effort and "o" in request.model:
            openai_params["reasoning_effort"] = request.reasoning_effort
        
        # Add any extra params
        if request.extra_params:
            openai_params.update(request.extra_params)
        
        # Make request
        raw_response = self._client.chat.completions.create(**openai_params)
        
        # Normalize and return
        return self._normalize_response(raw_response.model_dump())
    
    def chat_completion_stream(
        self, request: ChatRequest
    ) -> Iterator[ChatResponse]:
        """Execute streaming chat completion."""
        request_dict = {
            "model": request.model,
            "messages": request.messages,
            "stream": True,
        }
        
        stream = self._client.chat.completions.create(**request_dict)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield self._normalize_response(chunk.model_dump())
    
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """Convert OpenAI response to unified format."""
        choice = raw_response["choices"][0]
        usage_dict = raw_response.get("usage", {})
        
        usage = Usage(
            prompt_tokens=usage_dict.get("prompt_tokens", 0),
            completion_tokens=usage_dict.get("completion_tokens", 0),
            total_tokens=usage_dict.get("total_tokens", 0),
            cached_tokens=usage_dict.get(
                "prompt_tokens_details", {}
            ).get("cached_tokens", 0),
            reasoning_tokens=usage_dict.get("completion_tokens_details", {})
                .get("reasoning_tokens", 0),
        )
        
        usage.cost_usd = self._calculate_cost(
            usage, raw_response["model"]
        )
        
        return ChatResponse(
            id=raw_response["id"],
            model=raw_response["model"],
            content=choice["message"]["content"],
            finish_reason=choice["finish_reason"],
            usage=usage,
            provider=self.provider_name,
            created_at=datetime.fromtimestamp(raw_response["created"]),
            raw_response=raw_response,
        )
    
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """Calculate cost in USD."""
        model_info = self.MODELS.get(model, {})
        cost_input = model_info.get("cost_input", 0)
        cost_output = model_info.get("cost_output", 0)
        
        # Costs are per 1M tokens
        input_cost = (usage.prompt_tokens / 1_000_000) * cost_input
        output_cost = (usage.completion_tokens / 1_000_000) * cost_output
        
        return input_cost + output_cost
```

### 2.5 OpenAI-Compatible Provider Pattern

For providers with OpenAI-compatible APIs (Gemini, DeepSeek, Groq, Grok, Ollama):

```python
class OpenAICompatibleProvider(BaseProvider):
    """Base class for OpenAI-compatible providers."""
    
    BASE_URL: str = None  # Override in subclass
    MODELS: dict = None   # Override in subclass
    ENV_VAR: str = None   # Override in subclass
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        config: dict = None
    ):
        api_key = api_key or os.getenv(self.ENV_VAR)
        if not api_key and self.ENV_VAR != "OLLAMA_API_KEY":
            raise ValueError(f"{self.provider_name} API key not provided")
        super().__init__(api_key, config)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client with custom base URL."""
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL
        )
    
    # Rest of implementation similar to OpenAIProvider...

class GeminiProvider(OpenAICompatibleProvider):
    """Google Gemini provider."""
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    ENV_VAR = "GOOGLE_API_KEY"
    MODELS = {
        "gemini-2.5-pro": {"context": 1000000, "cost_input": 1.25, "cost_output": 5.0},
        "gemini-2.5-flash": {"context": 1000000, "cost_input": 0.075, "cost_output": 0.30},
        "gemini-2.5-flash-lite": {"context": 1000000, "cost_input": 0.0, "cost_output": 0.0},
    }
    
    @property
    def provider_name(self) -> str:
        return "google"
```

### 2.6 Unified Client

```python
from typing import Optional, Dict, Union
from enum import Enum

class ProviderType(str, Enum):
    """Supported provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    GROK = "grok"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"

class LLMClient:
    """Unified client for all LLM providers."""
    
    _provider_registry: Dict[str, type] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GeminiProvider,
        "deepseek": DeepSeekProvider,
        "groq": GroqProvider,
        "grok": GrokProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
    }
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize unified LLM client.
        
        Args:
            api_keys: Optional dict of provider -> api_key mappings.
                     If not provided, reads from environment variables.
        """
        self.api_keys = api_keys or {}
        self._providers: Dict[str, BaseProvider] = {}
    
    def _get_provider(self, model: str) -> BaseProvider:
        """Get or create provider for the given model."""
        # Determine provider from model string
        provider_name = self._detect_provider(model)
        
        # Create provider if not cached
        if provider_name not in self._providers:
            provider_class = self._provider_registry[provider_name]
            api_key = self.api_keys.get(provider_name)
            self._providers[provider_name] = provider_class(api_key)
        
        return self._providers[provider_name]
    
    def _detect_provider(self, model: str) -> str:
        """Detect provider from model string."""
        # Simple heuristics - could be more sophisticated
        if model.startswith("gpt"):
            return "openai"
        elif model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gemini"):
            return "google"
        elif model.startswith("deepseek"):
            return "deepseek"
        elif "llama" in model or "mixtral" in model:
            return "ollama"
        else:
            raise ValueError(f"Cannot detect provider for model: {model}")
    
    def chat(
        self,
        model: str,
        messages: List[Message],
        **kwargs
    ) -> ChatResponse:
        """
        Execute a chat completion with any model.
        
        Args:
            model: Model name (e.g., "gpt-4.1-mini", "claude-sonnet-4-5")
            messages: List of message dicts
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            ChatResponse object with unified format
        
        Example:
            >>> client = LLMClient()
            >>> response = client.chat(
            ...     model="gpt-4.1-mini",
            ...     messages=[{"role": "user", "content": "Hello!"}],
            ...     temperature=0.7
            ... )
            >>> print(response.content)
        """
        provider = self._get_provider(model)
        request = ChatRequest(model=model, messages=messages, **kwargs)
        return provider.chat_completion(request)
    
    def chat_stream(
        self,
        model: str,
        messages: List[Message],
        **kwargs
    ) -> Iterator[ChatResponse]:
        """Execute a streaming chat completion."""
        provider = self._get_provider(model)
        request = ChatRequest(
            model=model, messages=messages, stream=True, **kwargs
        )
        return provider.chat_completion_stream(request)
    
    def list_models(
        self, provider: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """List all available models, optionally filtered by provider."""
        if provider:
            provider_class = self._provider_registry[provider]
            return {provider: provider_class.MODELS.keys()}
        
        return {
            name: list(cls.MODELS.keys())
            for name, cls in self._provider_registry.items()
        }
```

---

## 3. Advanced Features

### 3.1 Automatic Retry with Fallback

```python
from typing import List, Optional
import time

class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    fallback_models: Optional[List[str]] = None

def with_retry(
    client: LLMClient,
    request: ChatRequest,
    retry_config: RetryConfig
) -> ChatResponse:
    """Execute request with automatic retry and fallback."""
    models_to_try = [request.model]
    if retry_config.fallback_models:
        models_to_try.extend(retry_config.fallback_models)
    
    last_error = None
    
    for model in models_to_try:
        request.model = model
        delay = retry_config.initial_delay
        
        for attempt in range(retry_config.max_retries):
            try:
                return client.chat(
                    model=request.model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
            except Exception as e:
                last_error = e
                if attempt < retry_config.max_retries - 1:
                    time.sleep(delay)
                    delay = min(
                        delay * retry_config.exponential_base,
                        retry_config.max_delay
                    )
    
    raise Exception(
        f"All retry attempts failed. Last error: {last_error}"
    )
```

### 3.2 Decorators for Common Patterns

```python
from functools import wraps
from typing import Callable
import logging

def log_llm_call(func: Callable) -> Callable:
    """Decorator to log LLM API calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(__name__)
        model = kwargs.get("model", "unknown")
        logger.info(f"LLM call started: model={model}")
        
        try:
            response = func(*args, **kwargs)
            logger.info(
                f"LLM call completed: model={model}, "
                f"tokens={response.usage.total_tokens}, "
                f"cost=${response.usage.cost_usd:.4f}"
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: model={model}, error={e}")
            raise
    
    return wrapper

def cache_response(cache_ttl: int = 3600):
    """Decorator to cache LLM responses."""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            cache_key = str((args, frozenset(kwargs.items())))
            
            if cache_key in cache:
                cached_time, cached_response = cache[cache_key]
                if time.time() - cached_time < cache_ttl:
                    return cached_response
            
            response = func(*args, **kwargs)
            cache[cache_key] = (time.time(), response)
            return response
        
        return wrapper
    return decorator
```

### 3.3 Cost Tracking and Budget Management

```python
from dataclasses import dataclass, field
from typing import List
import threading

@dataclass
class CostTracker:
    """Track costs across all LLM calls."""
    total_cost: float = 0.0
    call_history: List[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    budget_limit: Optional[float] = None
    
    def record_call(
        self, 
        model: str, 
        provider: str, 
        usage: Usage
    ) -> None:
        """Record a new LLM call."""
        with self.lock:
            self.total_cost += usage.cost_usd
            self.call_history.append({
                "timestamp": datetime.now(),
                "model": model,
                "provider": provider,
                "cost": usage.cost_usd,
                "tokens": usage.total_tokens,
            })
            
            if (
                self.budget_limit 
                and self.total_cost > self.budget_limit
            ):
                raise BudgetExceededError(
                    f"Budget limit ${self.budget_limit:.2f} exceeded. "
                    f"Current spend: ${self.total_cost:.2f}"
                )
    
    def get_summary(self) -> dict:
        """Get cost summary."""
        with self.lock:
            return {
                "total_cost": self.total_cost,
                "total_calls": len(self.call_history),
                "cost_by_provider": self._group_by("provider"),
                "cost_by_model": self._group_by("model"),
            }
    
    def _group_by(self, key: str) -> dict:
        """Group costs by a specific key."""
        grouped = {}
        for call in self.call_history:
            k = call[key]
            if k not in grouped:
                grouped[k] = {"cost": 0.0, "calls": 0}
            grouped[k]["cost"] += call["cost"]
            grouped[k]["calls"] += 1
        return grouped
```

### 3.4 Intelligent Router (Future Enhancement)

```python
from typing import Protocol
from enum import Enum

class RoutingStrategy(str, Enum):
    """Routing strategy types."""
    COST = "cost"
    QUALITY = "quality"
    LATENCY = "latency"
    HYBRID = "hybrid"

class Router:
    """Intelligent model router."""
    
    def __init__(
        self, 
        client: LLMClient,
        strategy: RoutingStrategy = RoutingStrategy.HYBRID
    ):
        self.client = client
        self.strategy = strategy
        self._load_model_metadata()
    
    def _load_model_metadata(self) -> None:
        """Load model capabilities and performance data."""
        self.model_metadata = {
            "gpt-5": {
                "quality_score": 0.95,
                "cost_per_1k": 0.01,
                "avg_latency_ms": 2000,
                "context_window": 128000,
                "capabilities": ["reasoning", "vision", "tools"],
            },
            "gpt-4.1-mini": {
                "quality_score": 0.80,
                "cost_per_1k": 0.0008,
                "avg_latency_ms": 800,
                "context_window": 128000,
                "capabilities": ["tools"],
            },
            # Add other models...
        }
    
    def route(
        self, 
        messages: List[Message],
        required_capabilities: List[str] = None
    ) -> str:
        """
        Select the best model for the given request.
        
        Args:
            messages: Conversation messages
            required_capabilities: Required model capabilities
        
        Returns:
            Selected model name
        """
        complexity = self._analyze_complexity(messages)
        
        # Filter models by capabilities
        candidates = [
            model for model, meta in self.model_metadata.items()
            if self._meets_requirements(meta, required_capabilities)
        ]
        
        if self.strategy == RoutingStrategy.COST:
            return self._select_by_cost(candidates)
        elif self.strategy == RoutingStrategy.QUALITY:
            return self._select_by_quality(candidates, complexity)
        elif self.strategy == RoutingStrategy.HYBRID:
            return self._select_hybrid(candidates, complexity)
        else:
            return candidates[0]
    
    def _analyze_complexity(self, messages: List[Message]) -> float:
        """Analyze prompt complexity (0.0 - 1.0)."""
        # Simple heuristic: check for reasoning keywords
        text = " ".join(m["content"] for m in messages)
        reasoning_keywords = [
            "analyze", "explain", "reasoning", "proof",
            "step by step", "complex", "calculate"
        ]
        
        score = sum(
            1 for keyword in reasoning_keywords 
            if keyword in text.lower()
        ) / len(reasoning_keywords)
        
        return min(score, 1.0)
    
    def _select_hybrid(
        self, 
        candidates: List[str], 
        complexity: float
    ) -> str:
        """Hybrid selection balancing cost, quality, latency."""
        scores = {}
        
        for model in candidates:
            meta = self.model_metadata[model]
            
            # Weighted score based on complexity
            quality_weight = complexity
            cost_weight = 1 - complexity
            
            quality_score = meta["quality_score"]
            # Normalize cost (lower is better)
            cost_score = 1 - (meta["cost_per_1k"] / 0.05)
            
            scores[model] = (
                quality_weight * quality_score + 
                cost_weight * cost_score
            )
        
        return max(scores, key=scores.get)
```

---

## 4. Configuration and Model Metadata

### 4.1 Model Configuration File

```python
# config.py

MODEL_CATALOG = {
    "openai": {
        "gpt-5": {
            "context_window": 128000,
            "max_output": 32000,
            "cost_input_per_1m": 10.0,
            "cost_output_per_1m": 30.0,
            "capabilities": ["reasoning", "vision", "tools", "streaming"],
            "supports_system_prompt": True,
            "supports_caching": True,
        },
        "gpt-4.1-mini": {
            "context_window": 128000,
            "max_output": 16000,
            "cost_input_per_1m": 0.15,
            "cost_output_per_1m": 0.60,
            "capabilities": ["tools", "streaming", "vision"],
            "supports_system_prompt": True,
            "supports_caching": True,
        },
    },
    "anthropic": {
        "claude-sonnet-4-5-20250929": {
            "context_window": 200000,
            "max_output": 8000,
            "cost_input_per_1m": 3.0,
            "cost_output_per_1m": 15.0,
            "cost_cache_write_per_1m": 3.75,
            "cost_cache_read_per_1m": 0.30,
            "capabilities": ["tools", "vision", "streaming", "thinking"],
            "supports_system_prompt": True,
            "supports_caching": True,
        },
    },
    "google": {
        "gemini-2.5-flash-lite": {
            "context_window": 1000000,
            "max_output": 8000,
            "cost_input_per_1m": 0.0,
            "cost_output_per_1m": 0.0,
            "capabilities": ["tools", "vision", "streaming"],
            "supports_system_prompt": True,
            "supports_caching": True,
        },
    },
    # Other providers...
}

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
    "grok": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
}
```

---

## 5. Error Handling and Exceptions

```python
# exceptions.py

class LLMException(Exception):
    """Base exception for LLM operations."""
    pass

class ProviderException(LLMException):
    """Provider-specific error."""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")

class APIKeyMissingError(LLMException):
    """API key not found."""
    pass

class ModelNotSupportedError(LLMException):
    """Model not supported by provider."""
    pass

class RateLimitError(ProviderException):
    """Rate limit exceeded."""
    pass

class BudgetExceededError(LLMException):
    """Budget limit exceeded."""
    pass

class InvalidRequestError(LLMException):
    """Invalid request parameters."""
    pass

class ProviderUnavailableError(ProviderException):
    """Provider service unavailable."""
    pass
```

---

## 6. Usage Examples

### 6.1 Basic Usage

```python
from llm_abstraction import LLMClient

# Initialize client (reads API keys from environment)
client = LLMClient()

# Simple chat completion
response = client.chat(
    model="gpt-4.1-mini",
    messages=[
        {"role": "user", "content": "Explain quantum computing in one sentence"}
    ],
    temperature=0.7
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

### 6.2 Switching Models Without Code Changes

```python
# Start with OpenAI
model = "gpt-4.1-mini"

# Switch to Anthropic - no code changes needed!
model = "claude-sonnet-4-5-20250929"

# Switch to Google - still no code changes!
model = "gemini-2.5-flash-lite"

# Same interface for all
response = client.chat(
    model=model,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 6.3 Streaming Responses

```python
for chunk in client.chat_stream(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Write a poem about Python"}]
):
    print(chunk.content, end="", flush=True)
```

### 6.4 With Cost Tracking

```python
from llm_abstraction import LLMClient, CostTracker

client = LLMClient()
tracker = CostTracker(budget_limit=10.0)

# Make multiple calls
for i in range(10):
    response = client.chat(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": f"Question {i}"}]
    )
    tracker.record_call(
        response.model, response.provider, response.usage
    )

# Get summary
print(tracker.get_summary())
```

### 6.5 With Retry and Fallback

```python
from llm_abstraction import with_retry, RetryConfig

config = RetryConfig(
    max_retries=3,
    fallback_models=["gpt-4.1-mini", "gemini-2.5-flash-lite"]
)

# Will automatically retry and fallback if primary model fails
response = with_retry(
    client=client,
    request=ChatRequest(
        model="gpt-5",
        messages=[{"role": "user", "content": "Hello"}]
    ),
    retry_config=config
)
```

### 6.6 Multi-Model Comparison

```python
models = [
    "gpt-4.1-mini",
    "claude-sonnet-4-5-20250929",
    "gemini-2.5-flash-lite",
    "deepseek-reasoner",
]

question = [{"role": "user", "content": "What is the meaning of life?"}]

for model in models:
    response = client.chat(model=model, messages=question)
    print(f"\n{model}:")
    print(response.content)
    print(f"Cost: ${response.usage.cost_usd:.4f}")
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
import unittest
from unittest.mock import Mock, patch
from llm_abstraction import OpenAIProvider, ChatRequest

class TestOpenAIProvider(unittest.TestCase):
    
    def setUp(self):
        self.provider = OpenAIProvider(api_key="test-key")
    
    def test_model_validation(self):
        self.assertTrue(self.provider.validate_model("gpt-4.1-mini"))
        self.assertFalse(self.provider.validate_model("invalid-model"))
    
    @patch('openai.OpenAI')
    def test_chat_completion(self, mock_client):
        # Mock response
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "id": "test-id",
            "model": "gpt-4.1-mini",
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            "created": 1234567890
        }
        
        mock_client.return_value.chat.completions.create.return_value = (
            mock_response
        )
        
        # Test
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "test"}]
        )
        response = self.provider.chat_completion(request)
        
        self.assertEqual(response.content, "Test response")
        self.assertEqual(response.usage.total_tokens, 30)
```

### 7.2 Integration Tests

```python
class TestIntegration(unittest.TestCase):
    
    def test_real_openai_call(self):
        """Test actual OpenAI API call (requires valid API key)."""
        client = LLMClient()
        response = client.chat(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "Say 'test' once"}]
        )
        
        self.assertIsNotNone(response.content)
        self.assertGreater(response.usage.total_tokens, 0)
        self.assertGreater(response.usage.cost_usd, 0)
```

---

## 8. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Set up project structure
- [ ] Implement base provider interface
- [ ] Implement OpenAI provider
- [ ] Implement unified client
- [ ] Basic error handling
- [ ] Unit tests for core components

### Phase 2: Provider Expansion (Week 2)
- [ ] Implement Anthropic provider
- [ ] Implement Google Gemini provider
- [ ] Implement OpenAI-compatible providers (DeepSeek, Groq, Grok, Ollama)
- [ ] Provider-specific tests
- [ ] Integration tests

### Phase 3: Advanced Features (Week 3)
- [ ] Streaming support
- [ ] Cost tracking
- [ ] Retry logic with fallbacks
- [ ] Caching decorator
- [ ] Logging decorator
- [ ] Budget management

### Phase 4: Router and Optimization (Week 4)
- [ ] Basic router implementation
- [ ] Complexity analysis
- [ ] Model selection strategies
- [ ] Performance benchmarking
- [ ] Documentation

### Phase 5: Production Readiness
- [ ] Comprehensive documentation
- [ ] Example applications
- [ ] Performance optimization
- [ ] Security audit
- [ ] Package for PyPI

---

## 9. Dependencies

```toml
# pyproject.toml

[project]
name = "llm-abstraction"
version = "0.1.0"
description = "Unified interface for multiple LLM providers"
requires-python = ">=3.10"
dependencies = [
    "openai>=1.0.0",
    "anthropic>=0.25.0",
    "google-generativeai>=0.8.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "typing-extensions>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "black>=24.0.0",
    "ruff>=0.5.0",
    "mypy>=1.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-mock>=3.0.0",
]
```

---

## 10. Best Practices and Considerations

### Security
- Never commit API keys
- Use environment variables or secure vaults
- Validate all inputs
- Sanitize error messages (don't leak keys)

### Performance
- Connection pooling for HTTP clients
- Async support for concurrent requests (future)
- Response caching where appropriate
- Lazy loading of providers

### Cost Management
- Always track token usage
- Set budget limits
- Use cheaper models for development
- Implement prompt caching

### Observability
- Comprehensive logging
- Request/response tracking
- Performance metrics
- Cost reporting

### Maintainability
- Type hints everywhere
- Comprehensive docstrings
- Unit tests for all components
- Clear error messages

---

## 11. Future Enhancements

1. **Async Support**: Add async/await interface for concurrent requests
2. **Advanced Router**: ML-based routing with self-learning
3. **Prompt Templates**: Built-in prompt engineering utilities
4. **Function Calling**: Unified interface for tool use
5. **Vision Support**: Standardized image input handling
6. **Agent Framework**: Higher-level agent abstractions
7. **Monitoring Dashboard**: Real-time usage and cost tracking
8. **Provider Health Checks**: Automatic failover on outages
9. **Response Validation**: Schema validation for structured outputs
10. **Multi-Modal Support**: Audio, video, code execution

---

## Conclusion

This technical approach provides a comprehensive blueprint for building a production-ready, multi-provider LLM abstraction layer. The design emphasizes:

- **Flexibility**: Easy to add new providers
- **Reliability**: Built-in retry and fallback mechanisms
- **Cost Control**: Comprehensive tracking and budget management
- **Developer Experience**: Intuitive API with minimal code changes
- **Production Ready**: Error handling, logging, testing

The module will eliminate vendor lock-in, simplify multi-model development, and provide a foundation for sophisticated routing and orchestration strategies.

---

**Next Steps**: Begin Phase 1 implementation, starting with the base provider interface and OpenAI provider implementation.
