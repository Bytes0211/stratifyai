"""Reasoning model detection utility.

Provides a single source of truth for detecting reasoning models across all
providers and code paths (REST API, WebSocket, provider implementations).
"""

from typing import Dict, Optional


def is_reasoning_model(
    provider: str,
    model: str,
    model_catalog: Optional[Dict] = None,
) -> bool:
    """
    Detect if a model is a reasoning model requiring temperature=1.0.
    
    This is the single source of truth for reasoning model detection,
    used by REST endpoints, WebSocket handlers, and provider implementations.
    
    Args:
        provider: Provider name (e.g., 'openai', 'deepseek', 'grok')
        model: Model name (e.g., 'o1', 'deepseek-reasoner', 'grok-4')
        model_catalog: Optional model catalog dict. If provided, checks
            the 'reasoning_model' flag first.
    
    Returns:
        True if the model is a reasoning model, False otherwise.
    
    Example:
        >>> is_reasoning_model('openai', 'o1')
        True
        >>> is_reasoning_model('openai', 'gpt-4o')
        False
        >>> is_reasoning_model('deepseek', 'deepseek-reasoner')
        True
    """
    # First check catalog if provided
    if model_catalog:
        provider_models = model_catalog.get(provider, {})
        model_info = provider_models.get(model, {})
        if model_info.get("reasoning_model", False):
            return True
    
    # Pattern-based detection for models not in catalog or missing flag
    if not model:
        return False
    
    model_lower = model.lower()
    
    # OpenAI reasoning models: o1, o3, o-series, gpt-5 (requires temp=1.0)
    if provider in ["openai", "deepseek", "openrouter"]:
        if (
            model_lower.startswith("o1") or
            model_lower.startswith("o3") or
            model_lower.startswith("gpt-5") or
            "reasoner" in model_lower or
            "reasoning" in model_lower or
            # Catch future o-series models (o2, o4, etc.)
            (model_lower.startswith("o") and len(model_lower) > 1 and model_lower[1].isdigit())
        ):
            return True
    
    # Grok reasoning models
    if provider == "grok":
        if (
            "reasoning" in model_lower or
            model_lower == "grok-4" or  # Flagship is reasoning
            model_lower.startswith("grok-3-mini") or  # Mini variants are reasoning
            model_lower.startswith("grok-code")  # Code models are reasoning
        ):
            return True
    
    # DeepSeek reasoning models
    if provider == "deepseek":
        if "reasoner" in model_lower or "reasoning" in model_lower:
            return True
    
    # Groq reasoning models (open-weight reasoning models)
    if provider == "groq":
        if "reasoning" in model_lower or "gpt-oss" in model_lower:
            return True
    
    return False


def get_temperature_for_model(
    provider: str,
    model: str,
    requested_temperature: Optional[float],
    model_catalog: Optional[Dict] = None,
    default_temperature: float = 0.7,
) -> float:
    """
    Get the appropriate temperature for a model.
    
    For reasoning models, returns 1.0 regardless of requested temperature.
    For other models, returns the requested temperature or default.
    
    Args:
        provider: Provider name
        model: Model name
        requested_temperature: User-requested temperature (may be None)
        model_catalog: Optional model catalog dict
        default_temperature: Default temperature for non-reasoning models
    
    Returns:
        Appropriate temperature value for the model
    """
    if is_reasoning_model(provider, model, model_catalog):
        return 1.0
    
    return requested_temperature if requested_temperature is not None else default_temperature
