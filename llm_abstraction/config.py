"""Configuration and model metadata for all providers."""

from typing import Dict, Any

# OpenAI Model Catalog
OPENAI_MODELS: Dict[str, Dict[str, Any]] = {
    "gpt-5": {
        "context": 128000,
        "cost_input": 10.0,  # Per 1M tokens
        "cost_output": 30.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-5-mini": {
        "context": 128000,
        "cost_input": 2.0,
        "cost_output": 6.0,
        "supports_vision": True,
        "supports_tools": True,
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
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-4.1-mini": {
        "context": 128000,
        "cost_input": 0.15,
        "cost_output": 0.60,
        "supports_vision": True,
        "supports_tools": True,
    },
    "o1": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 60.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
    },
    "o1-mini": {
        "context": 128000,
        "cost_input": 3.0,
        "cost_output": 12.0,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
    },
    "o3-mini": {
        "context": 200000,
        "cost_input": 1.1,
        "cost_output": 4.4,
        "supports_vision": False,
        "supports_tools": False,
        "reasoning_model": True,
    },
}

# Anthropic Model Catalog
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    "claude-3-5-sonnet-20241022": {
        "context": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "claude-3-5-haiku-20241022": {
        "context": 200000,
        "cost_input": 0.80,
        "cost_output": 4.0,
        "supports_vision": False,
        "supports_tools": True,
    },
    "claude-3-opus-20240229": {
        "context": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "supports_vision": True,
        "supports_tools": True,
    },
}

# Google Gemini Model Catalog (OpenAI-compatible)
GOOGLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {
        "context": 1000000,
        "cost_input": 1.25,
        "cost_output": 5.0,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gemini-2.5-flash": {
        "context": 1000000,
        "cost_input": 0.075,
        "cost_output": 0.30,
        "supports_vision": True,
        "supports_tools": True,
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
    "deepseek": "https://api.deepseek.com",
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
