"""Chat package for StratumAI provider-specific chat interfaces.

This package provides convenient, provider-specific chat functions with
sensible defaults for each supported LLM provider.

Usage:
    from chat import openai, anthropic, google
    
    # Quick chat with defaults
    response = openai.chat("Hello, world!")
    
    # With custom parameters
    response = anthropic.chat(
        "Explain quantum computing",
        model="claude-sonnet-4-5",
        temperature=0.5,
        max_tokens=500,
    )
"""

from chat import (
    stratumai_openai as openai,
    stratumai_anthropic as anthropic,
    stratumai_google as google,
    stratumai_deepseek as deepseek,
    stratumai_groq as groq,
    stratumai_grok as grok,
    stratumai_openrouter as openrouter,
    stratumai_ollama as ollama,
    stratumai_bedrock as bedrock,
)

__all__ = [
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "groq",
    "grok",
    "openrouter",
    "ollama",
    "bedrock",
]
