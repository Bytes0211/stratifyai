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
    "bedrock": {
        "min_temperature": 0.0,
        "max_temperature": 1.0,
    },
}

# Anthropic Model Catalog
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    # Claude 4.5 Models (Latest - November 2025)
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
    "claude-opus-4-5-20251101": {
        "context": 1000000,
        "api_max_input": 200000,  # API enforces 200k input limit despite 1M context
        "cost_input": 5.0,
        "cost_output": 25.0,
        "cost_cache_write": 6.25,
        "cost_cache_read": 0.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-opus-4-5": {  # Alias for latest Opus 4.5
        "context": 1000000,
        "api_max_input": 200000,  # API enforces 200k input limit despite 1M context
        "cost_input": 5.0,
        "cost_output": 25.0,
        "cost_cache_write": 6.25,
        "cost_cache_read": 0.50,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-haiku-4-5-20251001": {
        "context": 200000,
        "cost_input": 1.0,
        "cost_output": 5.0,
        "cost_cache_write": 1.25,
        "cost_cache_read": 0.10,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-haiku-4-5": {  # Alias for latest Haiku 4.5
        "context": 200000,
        "cost_input": 1.0,
        "cost_output": 5.0,
        "cost_cache_write": 1.25,
        "cost_cache_read": 0.10,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    # Claude 4.1 Models (August 2025)
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
    # Claude 4 Models (May 2025)
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
    # Claude 3.7 Sonnet (February 2025)
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
    # Claude 3.5 Models (October 2024) - Legacy but still available
    "claude-3-5-sonnet-20241022": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "cost_cache_write": 3.75,
        "cost_cache_read": 0.30,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "claude-3-5-haiku-20241022": {
        "context": 200000,
        "cost_input": 1.0,
        "cost_output": 5.0,
        "cost_cache_write": 1.25,
        "cost_cache_read": 0.10,
        "supports_vision": False,
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
    # Llama 3.3 Models (Production)
    "llama-3.3-70b-versatile": {
        "context": 128000,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
    },
    "llama-3.3-70b-specdec": {
        "context": 128000,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Llama 3.1 Models (Legacy - maintained for compatibility)
    "llama-3.1-70b-versatile": {
        "context": 128000,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
    },
    "llama-3.1-8b-instant": {
        "context": 128000,
        "cost_input": 0.05,
        "cost_output": 0.08,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Groq Tool Use Models
    "llama-3-groq-70b-tool-use": {
        "context": 8192,
        "cost_input": 0.89,
        "cost_output": 0.89,
        "supports_vision": False,
        "supports_tools": True,
    },
    "llama-3-groq-8b-tool-use": {
        "context": 8192,
        "cost_input": 0.19,
        "cost_output": 0.19,
        "supports_vision": False,
        "supports_tools": True,
    },
    # GPT-OSS Models (OpenAI's open-weight models)
    "openai/gpt-oss-120b": {
        "context": 128000,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
        "reasoning_model": True,
    },
    "openai/gpt-oss-20b": {
        "context": 128000,
        "cost_input": 0.05,
        "cost_output": 0.08,
        "supports_vision": False,
        "supports_tools": True,
        "reasoning_model": True,
    },
    # Compound AI System
    "groq/compound": {
        "context": 128000,
        "cost_input": 0.59,
        "cost_output": 0.79,
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
    # Anthropic Claude Models
    "anthropic/claude-opus-4-5": {
        "context": 1000000,
        "cost_input": 5.0,
        "cost_output": 25.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "anthropic/claude-sonnet-4-5": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "anthropic/claude-haiku-4-5": {
        "context": 200000,
        "cost_input": 0.80,
        "cost_output": 4.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "anthropic/claude-3-7-sonnet": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "anthropic/claude-3-5-sonnet": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    # OpenAI Models
    "openai/gpt-5.2": {
        "context": 400000,
        "cost_input": 10.0,
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "openai/gpt-5.1": {
        "context": 200000,
        "cost_input": 10.0,
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "openai/gpt-4o": {
        "context": 128000,
        "cost_input": 2.5,
        "cost_output": 10.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "openai/gpt-4o-mini": {
        "context": 128000,
        "cost_input": 0.15,
        "cost_output": 0.60,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "openai/gpt-4-turbo": {
        "context": 128000,
        "cost_input": 10.0,
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "openai/gpt-4": {
        "context": 8192,
        "cost_input": 30.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "openai/gpt-3.5-turbo": {
        "context": 16385,
        "cost_input": 0.50,
        "cost_output": 1.50,
        "supports_vision": False,
        "supports_tools": True,
    },
    "openai/o1": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "openai/o1-mini": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 12.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "openai/o3-mini": {
        "context": 200000,
        "cost_input": 1.1,
        "cost_output": 4.4,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    # Google Gemini Models
    "google/gemini-3": {
        "context": 1000000,
        "cost_input": 2.5,
        "cost_output": 10.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "google/gemini-2.5-pro": {
        "context": 1000000,
        "cost_input": 1.25,
        "cost_output": 5.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "google/gemini-2.5-flash": {
        "context": 1000000,
        "cost_input": 0.075,
        "cost_output": 0.30,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "google/gemini-2.5-flash-lite": {
        "context": 1000000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
        "free": True,
    },
    "google/gemini-2.0-flash-exp:free": {
        "context": 1000000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": True,
        "free": True,
    },
    # Meta Llama Models
    "meta-llama/llama-4-maverick:free": {
        "context": 512000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": True,
        "free": True,
    },
    "meta-llama/llama-4-scout:free": {
        "context": 512000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": True,
        "free": True,
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "context": 128000,
        "cost_input": 0.35,
        "cost_output": 0.40,
        "supports_vision": False,
        "supports_tools": True,
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "meta-llama/llama-3.1-70b-versatile": {
        "context": 131072,
        "cost_input": 0.59,
        "cost_output": 0.79,
        "supports_vision": False,
        "supports_tools": True,
    },
    "meta-llama/llama-3.1-8b-instant": {
        "context": 131072,
        "cost_input": 0.05,
        "cost_output": 0.08,
        "supports_vision": False,
        "supports_tools": True,
    },
    # DeepSeek Models
    "deepseek/deepseek-v3.2": {
        "context": 64000,
        "cost_input": 0.14,
        "cost_output": 0.28,
        "supports_vision": False,
        "supports_tools": True,
    },
    "deepseek/deepseek-chat": {
        "context": 64000,
        "cost_input": 0.14,
        "cost_output": 0.28,
        "supports_vision": False,
        "supports_tools": True,
    },
    "deepseek/deepseek-chat-v3-0324:free": {
        "context": 64000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "deepseek/deepseek-reasoner": {
        "context": 64000,
        "cost_input": 0.55,
        "cost_output": 2.19,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "deepseek/deepseek-r1": {
        "context": 64000,
        "cost_input": 0.55,
        "cost_output": 2.19,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
    },
    "deepseek/deepseek-r1-zero:free": {
        "context": 64000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
        "fixed_temperature": 1.0,
        "free": True,
    },
    "deepseek/deepseek-v3-base:free": {
        "context": 64000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    # Mistral Models
    "mistralai/mistral-large-3": {
        "context": 128000,
        "cost_input": 2.0,
        "cost_output": 6.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "mistralai/mistral-small-3.1-24b-instruct:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "mistralai/devstral-2:free": {
        "context": 256000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "mistralai/mixtral-8x7b-32768": {
        "context": 32768,
        "cost_input": 0.24,
        "cost_output": 0.24,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Qwen Models
    "qwen/qwen-3-32b": {
        "context": 128000,
        "cost_input": 0.40,
        "cost_output": 0.60,
        "supports_vision": False,
        "supports_tools": True,
    },
    "qwen/qwen2.5-vl-3b-instruct:free": {
        "context": 32000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": False,
        "free": True,
    },
    # X.AI Grok Models
    "x-ai/grok-4.1-fast": {
        "context": 1800000,
        "cost_input": 5.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "x-ai/grok-beta": {
        "context": 131072,
        "cost_input": 5.0,
        "cost_output": 15.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    # NVIDIA Models
    "nvidia/llama-3.1-nemotron-nano-8b-v1:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "nvidia/nemotron-nano-2-vl:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": False,
        "free": True,
    },
    # Moonshot AI Models
    "moonshotai/kimi-vl-a3b-thinking:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": True,
        "supports_tools": False,
        "reasoning_model": True,
        "free": True,
    },
    # Zhipu AI (GLM) Models
    "zhipuai/glm-4.5-air:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "zhipuai/glm-4-32b": {
        "context": 128000,
        "cost_input": 0.50,
        "cost_output": 0.50,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Nous Research Models
    "nousresearch/deephermes-3-llama-3-8b-preview:free": {
        "context": 8192,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": False,
        "free": True,
    },
    # Arcee Models
    "arcee/trinity-large-preview:free": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    # OpenRouter Native Models
    "openrouter/optimus-alpha": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
    "openrouter/quasar-alpha": {
        "context": 128000,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "supports_vision": False,
        "supports_tools": True,
        "free": True,
    },
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

# AWS Bedrock Model Catalog (Native SDK)
BEDROCK_MODELS: Dict[str, Dict[str, Any]] = {
    # Anthropic Claude 3.5 Models
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,  # Bedrock doesn't support prompt caching yet
    },
    "anthropic.claude-3-5-haiku-20241022-v1:0": {
        "context": 200000,
        "cost_input": 1.0,
        "cost_output": 5.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
    # Anthropic Claude 3 Models
    "anthropic.claude-3-opus-20240229-v1:0": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "context": 200000,
        "cost_input": 0.25,
        "cost_output": 1.25,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
    # Meta Llama Models
    "meta.llama3-3-70b-instruct-v1:0": {
        "context": 128000,
        "cost_input": 0.99,
        "cost_output": 0.99,
        "supports_vision": False,
        "supports_tools": False,
    },
    "meta.llama3-2-90b-instruct-v1:0": {
        "context": 128000,
        "cost_input": 1.20,
        "cost_output": 1.20,
        "supports_vision": False,
        "supports_tools": False,
    },
    "meta.llama3-1-70b-instruct-v1:0": {
        "context": 128000,
        "cost_input": 0.99,
        "cost_output": 0.99,
        "supports_vision": False,
        "supports_tools": False,
    },
    "meta.llama3-1-8b-instruct-v1:0": {
        "context": 128000,
        "cost_input": 0.22,
        "cost_output": 0.22,
        "supports_vision": False,
        "supports_tools": False,
    },
    # Mistral AI Models
    "mistral.mistral-large-2402-v1:0": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 9.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "mistral.mistral-small-2402-v1:0": {
        "context": 32000,
        "cost_input": 1.0,
        "cost_output": 3.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    # Amazon Nova Models (current generation)
    "amazon.nova-pro-v1:0": {
        "context": 300000,
        "cost_input": 0.80,
        "cost_output": 3.20,
        "supports_vision": True,
        "supports_tools": False,
    },
    "amazon.nova-lite-v1:0": {
        "context": 300000,
        "cost_input": 0.06,
        "cost_output": 0.24,
        "supports_vision": True,
        "supports_tools": False,
    },
    "amazon.nova-micro-v1:0": {
        "context": 128000,
        "cost_input": 0.035,
        "cost_output": 0.14,
        "supports_vision": False,
        "supports_tools": False,
    },
    # Cohere Models
    "cohere.command-r-plus-v1:0": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "cohere.command-r-v1:0": {
        "context": 128000,
        "cost_input": 0.50,
        "cost_output": 1.50,
        "supports_vision": False,
        "supports_tools": True,
    },
}

# =============================================================================
# CURATED INTERACTIVE MODELS (validated at runtime)
# These provide the best balance of quality, cost, and availability for each provider
# =============================================================================

# OpenAI - 5 curated models
INTERACTIVE_OPENAI_MODELS: Dict[str, Dict[str, Any]] = {
    "gpt-4o": {
        "display_name": "GPT-4o",
        "description": "Best quality, vision/tools support",
        "category": "Current Models",
    },
    "gpt-4o-mini": {
        "display_name": "GPT-4o Mini",
        "description": "BEST VALUE - fast & affordable",
        "category": "Current Models",
    },
    "o3-mini": {
        "display_name": "o3-mini",
        "description": "Cost-effective reasoning",
        "category": "Reasoning Models",
    },
    "o1": {
        "display_name": "o1",
        "description": "Premium reasoning model",
        "category": "Reasoning Models",
    },
    "gpt-4-turbo": {
        "display_name": "GPT-4 Turbo",
        "description": "Legacy flagship, vision support",
        "category": "Legacy Models",
    },
}

# Anthropic - 5 curated models
INTERACTIVE_ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    "claude-sonnet-4-5": {
        "display_name": "Claude Sonnet 4.5",
        "description": "Latest flagship, best balance",
        "category": "Claude 4.5 (Latest)",
    },
    "claude-haiku-4-5": {
        "display_name": "Claude Haiku 4.5",
        "description": "Fast & affordable",
        "category": "Claude 4.5 (Latest)",
    },
    "claude-opus-4-5": {
        "display_name": "Claude Opus 4.5",
        "description": "Premium quality, 1M context",
        "category": "Claude 4.5 (Latest)",
    },
    "claude-3-5-sonnet-20241022": {
        "display_name": "Claude 3.5 Sonnet",
        "description": "Proven stable, vision/tools",
        "category": "Claude 3.5 (Stable)",
    },
    "claude-3-5-haiku-20241022": {
        "display_name": "Claude 3.5 Haiku",
        "description": "Budget option",
        "category": "Claude 3.5 (Stable)",
    },
}

# Google - 3 curated models
INTERACTIVE_GOOGLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "description": "Best quality, 1M context",
        "category": "Gemini 2.5",
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "description": "BEST VALUE - fast & cheap",
        "category": "Gemini 2.5",
    },
    "gemini-2.5-flash-lite": {
        "display_name": "Gemini 2.5 Flash Lite",
        "description": "FREE tier option",
        "category": "Gemini 2.5",
    },
}

# DeepSeek - 2 curated models
INTERACTIVE_DEEPSEEK_MODELS: Dict[str, Dict[str, Any]] = {
    "deepseek-chat": {
        "display_name": "DeepSeek Chat",
        "description": "General purpose, tools support",
        "category": "DeepSeek",
    },
    "deepseek-reasoner": {
        "display_name": "DeepSeek Reasoner",
        "description": "Reasoning model (R1)",
        "category": "DeepSeek",
    },
}

# Groq - 4 curated models
INTERACTIVE_GROQ_MODELS: Dict[str, Dict[str, Any]] = {
    "llama-3.3-70b-versatile": {
        "display_name": "Llama 3.3 70B",
        "description": "Best quality open model",
        "category": "Llama Models",
    },
    "llama-3.1-8b-instant": {
        "display_name": "Llama 3.1 8B",
        "description": "FASTEST - ultra low latency",
        "category": "Llama Models",
    },
    "openai/gpt-oss-120b": {
        "display_name": "GPT-OSS 120B",
        "description": "OpenAI open-weight reasoning",
        "category": "Reasoning Models",
    },
    "groq/compound": {
        "display_name": "Compound AI",
        "description": "Multi-model system",
        "category": "Groq Native",
    },
}

# Grok (X.AI) - 1 curated model
INTERACTIVE_GROK_MODELS: Dict[str, Dict[str, Any]] = {
    "grok-beta": {
        "display_name": "Grok Beta",
        "description": "X.AI flagship model",
        "category": "Grok",
    },
}

# OpenRouter - 7 curated models (mix of free and paid)
INTERACTIVE_OPENROUTER_MODELS: Dict[str, Dict[str, Any]] = {
    "anthropic/claude-sonnet-4-5": {
        "display_name": "Claude Sonnet 4.5",
        "description": "Best Anthropic model",
        "category": "Premium Models",
    },
    "openai/gpt-4o": {
        "display_name": "GPT-4o",
        "description": "Best OpenAI model",
        "category": "Premium Models",
    },
    "google/gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "description": "Best value option",
        "category": "Premium Models",
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "display_name": "Llama 3.3 70B",
        "description": "FREE - best open model",
        "category": "Free Models",
    },
    "deepseek/deepseek-chat-v3-0324:free": {
        "display_name": "DeepSeek V3",
        "description": "FREE - excellent quality",
        "category": "Free Models",
    },
    "deepseek/deepseek-r1": {
        "display_name": "DeepSeek R1",
        "description": "Reasoning model",
        "category": "Reasoning Models",
    },
    "mistralai/mistral-large-3": {
        "display_name": "Mistral Large 3",
        "description": "European alternative",
        "category": "Premium Models",
    },
}

# Ollama - 3 curated models (local)
INTERACTIVE_OLLAMA_MODELS: Dict[str, Dict[str, Any]] = {
    "llama3.2": {
        "display_name": "Llama 3.2",
        "description": "Best local model",
        "category": "Local Models",
    },
    "mistral": {
        "display_name": "Mistral",
        "description": "Fast & efficient",
        "category": "Local Models",
    },
    "codellama": {
        "display_name": "Code Llama",
        "description": "Code specialist",
        "category": "Local Models",
    },
}

# Bedrock - 5 curated models
INTERACTIVE_BEDROCK_MODELS: Dict[str, Dict[str, Any]] = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "display_name": "Claude 3 Sonnet",
        "description": "High quality, vision/tools",
        "category": "Anthropic Claude 3",
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "display_name": "Claude 3 Haiku",
        "description": "Fast & cheap Claude",
        "category": "Anthropic Claude 3",
    },
    "amazon.nova-pro-v1:0": {
        "display_name": "Nova Pro",
        "description": "Best Nova quality, vision",
        "category": "Amazon Nova",
    },
    "amazon.nova-lite-v1:0": {
        "display_name": "Nova Lite",
        "description": "BEST VALUE - 96% cheaper",
        "category": "Amazon Nova",
    },
    "amazon.nova-micro-v1:0": {
        "display_name": "Nova Micro",
        "description": "FASTEST/CHEAPEST",
        "category": "Amazon Nova",
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
    "bedrock": BEDROCK_MODELS,
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
    "bedrock": "AWS_ACCESS_KEY_ID",  # AWS credentials (also uses AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
}
