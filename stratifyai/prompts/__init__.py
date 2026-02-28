"""Prompt template system for StratifyAI."""

from stratifyai.prompts.models import PromptParameter, PromptTemplate
from stratifyai.prompts.registry import PromptRegistry

# Singleton registry instance
registry = PromptRegistry()

__all__ = [
    "PromptParameter",
    "PromptTemplate",
    "PromptRegistry",
    "registry",
]
