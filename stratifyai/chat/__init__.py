"""Chat package for StratifyAI provider-specific chat interfaces.

This package provides convenient, provider-specific chat functions.
Model must be specified for each request.

Usage:
    # Model is always required
    from stratifyai.chat import openai, anthropic, google
    response = await openai.chat("Hello!", model="gpt-4.1-mini")
    
    # Builder pattern (model required first)
    from stratifyai.chat import anthropic
    client = (
        anthropic
        .with_model("claude-opus-4-5")
        .with_system("You are a helpful assistant")
        .with_developer("Use markdown formatting")
    )
    response = await client.chat("Hello!")
    
    # With additional parameters
    response = await anthropic.chat(
        "Explain quantum computing",
        model="claude-sonnet-4-5",
        temperature=0.5,
        max_tokens=500,
    )
"""

from stratifyai.chat.builder import ChatBuilder
from stratifyai.chat import (
    stratifyai_openai as openai,
    stratifyai_anthropic as anthropic,
    stratifyai_google as google,
    stratifyai_deepseek as deepseek,
    stratifyai_groq as groq,
    stratifyai_grok as grok,
    stratifyai_openrouter as openrouter,
    stratifyai_ollama as ollama,
    stratifyai_bedrock as bedrock,
)

__all__ = [
    "ChatBuilder",
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
