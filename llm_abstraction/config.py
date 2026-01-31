"""Configuration and model metadata for all providers."""

from typing import Dict, Any

# OpenAI Model Catalog
OPENAI_MODELS: Dict[str, Dict[str, Any]] = {
    # Current production models
    "gpt-4o": {
        "context": 128000,
        "cost_input": 2.5,
        "cost_output": 10.0,
        "cost_cache_write": 1.25,
        "cost_cache_read": 1.25,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gpt-4o-mini": {
        "context": 128000,
        "cost_input": 0.15,
        "cost_output": 0.60,
        "cost_cache_write": 0.075,
        "cost_cache_read": 0.075,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gpt-4-turbo": {
        "context": 128000,
        "cost_input": 10.0,
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-4": {
        "context": 8192,
        "cost_input": 30.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "gpt-3.5-turbo": {
        "context": 16385,
        "cost_input": 0.50,
        "cost_output": 1.50,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Future models (placeholders)
    "gpt-5": {
        "context": 128000,
        "cost_input": 10.0,  # Per 1M tokens
        "cost_output": 30.0,
        "cost_cache_write": 12.5,  # 25% more than input
        "cost_cache_read": 1.0,  # 90% discount on input
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
        "fixed_temperature": 1.0,
    },
    "gpt-5-mini": {
        "context": 128000,
        "cost_input": 2.0,
        "cost_output": 6.0,
        "cost_cache_write": 2.5,
        "cost_cache_read": 0.2,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gpt-5-nano": {
        "context": 128000,
        "cost_input": 1.0,
        "cost_output": 3.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "gpt-4.1": {
        "context": 128000,
        "cost_input": 2.5,
        "cost_output": 10.0,
        "cost_cache_write": 3.125,
        "cost_cache_read": 0.25,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gpt-4.1-mini": {
        "context": 128000,
        "cost_input": 0.15,
        "cost_output": 0.60,
        "cost_cache_write": 0.1875,
        "cost_cache_read": 0.015,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "o1": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "o1-mini": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 12.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "o3-mini": {
        "context": 200000,
        "cost_input": 1.1,
        "cost_output": 4.4,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "o1-preview": {
        "context": 128000,
        "cost_input": 15.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "o1-2024-12-17": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "o1-mini-2024-09-12": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 12.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
}

# Provider-specific constraints
PROVIDER_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "anthropic": {
        "min_temperature": 0.0,
        "max_temperature": 1.0,
    },
    "openai": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "google": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "deepseek": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "groq": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "grok": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "openrouter": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
    "ollama": {
        "min_temperature": 0.0,
        "max_temperature": 2.0,
    },
}

# Anthropic Model Catalog
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    # Claude 4.5 Models
    "claude-sonnet-4-5-20250929": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "cost_cache_write": 3.75,  # 25% more than input
        "cost_cache_read": 0.30,  # 90% discount on input
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-sonnet-4-5": {  # Alias for latest Sonnet 4.5
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "cost_cache_write": 3.75,
        "cost_cache_read": 0.30,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-opus-4-5-20251124": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "cost_cache_write": 18.75,
        "cost_cache_read": 1.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-opus-4-5": {  # Alias for latest Opus 4.5
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "cost_cache_write": 18.75,
        "cost_cache_read": 1.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-haiku-4-5-20251001": {
        "context": 200000,
        "cost_input": 0.80,
        "cost_output": 4.0,
        "cost_cache_write": 1.0,
        "cost_cache_read": 0.08,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-haiku-4-5": {  # Alias for latest Haiku 4.5
        "context": 200000,
        "cost_input": 0.80,
        "cost_output": 4.0,
        "cost_cache_write": 1.0,
        "cost_cache_read": 0.08,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    # Claude 4 Models
    "claude-sonnet-4-20250514": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "cost_cache_write": 3.75,
        "cost_cache_read": 0.30,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-opus-4-1-20250805": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "cost_cache_write": 18.75,
        "cost_cache_read": 1.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-opus-4-20250514": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "cost_cache_write": 18.75,
        "cost_cache_read": 1.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    # Claude 3.7 Models (Still supported)
    "claude-3-7-sonnet-20250219": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "cost_cache_write": 3.75,
        "cost_cache_read": 0.30,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
}

# Google Gemini Model Catalog (OpenAI-compatible)
GOOGLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {
        "context": 1000000,
        "cost_input": 1.25,
        "cost_output": 5.0,
        "cost_cache_write": 1.5625,
        "cost_cache_read": 0.125,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gemini-2.5-flash": {
        "context": 1000000,
        "cost_input": 0.075,
        "cost_output": 0.30,
        "cost_cache_write": 0.09375,
        "cost_cache_read": 0.0075,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "gemini-2.5-flash-lite": {
        "context": 1000000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
    },
}

# DeepSeek Model Catalog (OpenAI-compatible)
DEEPSEEK_MODELS: Dict[str, Dict[str, Any]] = {
    "deepseek-chat": {
        "context": 64000,
        "cost_input": 0.14,
        "cost_output": 0.28,
        "supports_vision": False,
        "supports_tools": True,
    },
    "deepseek-reasoner": {
        "context": 64000,
        "cost_input": 0.55,
        "cost_output": 2.19,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
}

# Groq Model Catalog (OpenAI-compatible)
GROQ_MODELS: Dict[str, Dict[str, Any]] = {
    "llama-3.1-70b-versatile": {
        "context": 131072,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
    },
    "llama-3.1-8b-instant": {
        "context": 131072,
        "cost_input": 0.05,
        "cost_output": 0.08,
        "supports_vision": False,
        "supports_tools": True,
    },
    "mixtral-8x7b-32768": {
        "context": 32768,
        "cost_input": 0.24,
        "cost_output": 0.24,
        "supports_vision": False,
        "supports_tools": True,
    },
}

# Grok (X.AI) Model Catalog (OpenAI-compatible)
GROK_MODELS: Dict[str, Dict[str, Any]] = {
    "grok-beta": {
        "context": 131072,
        "cost_input": 5.0,
        "cost_output": 15.0,
        "supports_vision": False,
        "supports_tools": True,
    },
}

# OpenRouter Model Catalog (Supports many models)
OPENROUTER_MODELS: Dict[str, Dict[str, Any]] = {
    "anthropic/claude-3-5-sonnet": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "openai/gpt-4-turbo": {
        "context": 128000,
        "cost_input": 10.0,
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Add more OpenRouter models as needed
}

# Ollama Model Catalog (Local models)
OLLAMA_MODELS: Dict[str, Dict[str, Any]] = {
    "llama3.2": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
    },
    "mistral": {
        "context": 32768,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
    },
    "codellama": {
        "context": 16384,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
    },
}

# Unified model catalog
MODEL_CATALOG: Dict[str, Dict[str, Dict[str, Any]]] = {
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "google": GOOGLE_MODELS,
    "deepseek": DEEPSEEK_MODELS,
    "groq": GROQ_MODELS,
    "grok": GROK_MODELS,
    "openrouter": OPENROUTER_MODELS,
    "ollama": OLLAMA_MODELS,
}

# Provider base URLs for OpenAI-compatible providers
PROVIDER_BASE_URLS: Dict[str, str] = {
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "deepseek": "https://api.deepseek.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "grok": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
}

# Environment variable names for API keys
PROVIDER_ENV_VARS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "grok": "GROK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}
