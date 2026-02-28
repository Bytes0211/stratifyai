"""Configuration and model metadata for all providers.

Model catalogs are now loaded from catalog/models.json via catalog_manager.
This file maintains provider constraints and INTERACTIVE_*_MODELS for UI curation.
"""

from typing import Dict, Any

# Import all providers from the centralized catalog
from .catalog_manager import (
    get_openai_models,
    get_anthropic_models,
    get_google_models,
    get_deepseek_models,
    get_groq_models,
    get_grok_models,
    get_openrouter_models,
    get_ollama_models,
    get_bedrock_models,
)

# Load model catalogs from catalog/models.json
OPENAI_MODELS: Dict[str, Dict[str, Any]] = get_openai_models()

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

# Model Catalogs - Loaded from catalog/models.json
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = get_anthropic_models()
GOOGLE_MODELS: Dict[str, Dict[str, Any]] = get_google_models()
DEEPSEEK_MODELS: Dict[str, Dict[str, Any]] = get_deepseek_models()
GROQ_MODELS: Dict[str, Dict[str, Any]] = get_groq_models()
GROK_MODELS: Dict[str, Dict[str, Any]] = get_grok_models()
OPENROUTER_MODELS: Dict[str, Dict[str, Any]] = get_openrouter_models()
OLLAMA_MODELS: Dict[str, Dict[str, Any]] = get_ollama_models()
BEDROCK_MODELS: Dict[str, Dict[str, Any]] = get_bedrock_models()

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
        "description": "Legacy flagship, tools support",
        "category": "Legacy Models",
    },
}

# Anthropic - 5 curated models
INTERACTIVE_ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = {
    "claude-sonnet-4-20250514": {
        "display_name": "Claude Sonnet 4",
        "description": "Latest flagship model",
        "category": "Claude 4 (Latest)",
    },
    "claude-3-7-sonnet-20250219": {
        "display_name": "Claude 3.7 Sonnet",
        "description": "Advanced reasoning",
        "category": "Claude 3.7",
    },
    "claude-3-5-sonnet-20241022": {
        "display_name": "Claude 3.5 Sonnet",
        "description": "Proven stable, vision/tools",
        "category": "Claude 3.5 (Stable)",
    },
    "claude-3-5-haiku-20241022": {
        "display_name": "Claude 3.5 Haiku",
        "description": "Fast & affordable",
        "category": "Claude 3.5 (Stable)",
    },
    "claude-3-haiku-20240307": {
        "display_name": "Claude 3 Haiku",
        "description": "BEST VALUE - cheapest option",
        "category": "Claude 3",
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

# Grok (X.AI) - 7 curated models
INTERACTIVE_GROK_MODELS: Dict[str, Dict[str, Any]] = {
    "grok-4-1-fast-reasoning": {
        "display_name": "Grok 4.1 Fast (Reasoning)",
        "description": "BEST VALUE - 2M context, agentic tools",
        "category": "Grok 4.1 Fast (Latest)",
    },
    "grok-4-1-fast-non-reasoning": {
        "display_name": "Grok 4.1 Fast (Non-Reasoning)",
        "description": "FASTEST - instant responses, 2M context",
        "category": "Grok 4.1 Fast (Latest)",
    },
    "grok-code-fast-1": {
        "display_name": "Grok Code Fast",
        "description": "FREE - specialized for coding",
        "category": "Grok Specialized",
    },
    "grok-4": {
        "display_name": "Grok 4",
        "description": "Flagship reasoning model",
        "category": "Grok 4 (Premium)",
    },
    "grok-3": {
        "display_name": "Grok 3",
        "description": "Stable production model",
        "category": "Grok 3",
    },
    "grok-3-mini": {
        "display_name": "Grok 3 Mini",
        "description": "Configurable reasoning effort",
        "category": "Grok 3",
    },
    "grok-2-1212": {
        "display_name": "Grok 2",
        "description": "Legacy stable model",
        "category": "Grok 2 (Legacy)",
    },
}

# OpenRouter - 11 curated models (mix of free and paid, multiple 1M context options)
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
        "description": "BEST VALUE - 1M context, fast/cheap",
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
    "anthropic/claude-opus-4-5": {
        "display_name": "Claude Opus 4.5",
        "description": "Premium quality, 1M context",
        "category": "1M Context Models",
    },
    "google/gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "description": "Best quality, 1M context",
        "category": "1M Context Models",
    },
    "google/gemini-3": {
        "display_name": "Gemini 3",
        "description": "Latest Google, 1M context",
        "category": "1M Context Models",
    },
    "google/gemini-2.0-flash-exp:free": {
        "display_name": "Gemini 2.0 Flash Exp",
        "description": "FREE - 1M context, vision/tools",
        "category": "Free Models (1M Context)",
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
