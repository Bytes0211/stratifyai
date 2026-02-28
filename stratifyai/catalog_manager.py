"""Model catalog manager for loading and caching model metadata.

This module loads the model catalog from catalog/models.json and provides
a dictionary interface compatible with the existing config.py structure.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global catalog cache with thread safety
_catalog_lock = threading.Lock()
_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_PATH: Optional[Path] = None


def get_catalog_path() -> Path:
    """Get path to catalog/models.json file."""
    global _CATALOG_PATH
    if _CATALOG_PATH is None:
        # Get path relative to this file's directory
        module_dir = Path(__file__).parent
        project_root = module_dir.parent
        _CATALOG_PATH = project_root / "catalog" / "models.json"
    return _CATALOG_PATH


def load_catalog(force_reload: bool = False) -> Dict[str, Any]:
    """Load model catalog from JSON file.
    
    Args:
        force_reload: If True, reload from disk even if cached
        
    Returns:
        Catalog dictionary with structure:
        {
            "version": "1.0.0",
            "updated": "2026-02-06T05:59:00Z",
            "providers": {
                "anthropic": {
                    "model-id": {...}
                }
            }
        }
    """
    global _CATALOG_CACHE
    
    # Double-checked locking for thread safety
    if _CATALOG_CACHE is not None and not force_reload:
        return _CATALOG_CACHE
    
    with _catalog_lock:
        # Re-check after acquiring lock
        if _CATALOG_CACHE is not None and not force_reload:
            return _CATALOG_CACHE
        
        catalog_path = get_catalog_path()
        
        if not catalog_path.exists():
            logger.error(f"Catalog file not found: {catalog_path}")
            raise FileNotFoundError(f"Model catalog not found at {catalog_path}")
        
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            # Validate basic structure
            if not isinstance(catalog, dict):
                raise ValueError("Catalog must be a JSON object")
            
            if "providers" not in catalog:
                raise ValueError("Catalog missing 'providers' key")
            
            _CATALOG_CACHE = catalog
            logger.info(f"Loaded catalog version {catalog.get('version', 'unknown')}")
            return catalog
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in catalog: {e}")
            raise ValueError(f"Failed to parse catalog JSON: {e}")
        except Exception as e:
            logger.error(f"Error loading catalog: {e}")
            raise


def get_provider_models(provider: str) -> Dict[str, Dict[str, Any]]:
    """Get models for a specific provider.
    
    Args:
        provider: Provider name (e.g., 'anthropic', 'openai')
        
    Returns:
        Dictionary of model_id -> model_metadata
        
    Example:
        >>> models = get_provider_models("anthropic")
        >>> models["claude-3-haiku-20240307"]["cost_input"]
        0.25
    """
    catalog = load_catalog()
    providers = catalog.get("providers", {})
    
    if provider not in providers:
        logger.warning(f"Provider '{provider}' not found in catalog")
        return {}
    
    return providers[provider]


def get_model_metadata(provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific model.
    
    Args:
        provider: Provider name
        model_id: Model ID
        
    Returns:
        Model metadata dictionary or None if not found
    """
    models = get_provider_models(provider)
    return models.get(model_id)


def is_model_deprecated(provider: str, model_id: str) -> bool:
    """Check if a model is deprecated.
    
    Args:
        provider: Provider name
        model_id: Model ID
        
    Returns:
        True if model is deprecated, False otherwise
    """
    metadata = get_model_metadata(provider, model_id)
    if metadata is None:
        return False
    return metadata.get("deprecated", False)


def get_model_replacement(provider: str, model_id: str) -> Optional[str]:
    """Get replacement model ID for a deprecated model.
    
    Args:
        provider: Provider name
        model_id: Model ID
        
    Returns:
        Replacement model ID or None
    """
    metadata = get_model_metadata(provider, model_id)
    if metadata is None:
        return None
    return metadata.get("replacement_model")


def list_all_models(include_deprecated: bool = False) -> Dict[str, list]:
    """List all models across all providers.
    
    Args:
        include_deprecated: If False, filter out deprecated models
        
    Returns:
        Dictionary of provider -> list of model IDs
    """
    catalog = load_catalog()
    providers = catalog.get("providers", {})
    
    result = {}
    for provider, models in providers.items():
        if include_deprecated:
            result[provider] = list(models.keys())
        else:
            result[provider] = [
                model_id for model_id, metadata in models.items()
                if not metadata.get("deprecated", False)
            ]
    
    return result


def get_catalog_version() -> str:
    """Get catalog version string."""
    catalog = load_catalog()
    return catalog.get("version", "unknown")


def get_catalog_updated() -> str:
    """Get catalog last updated timestamp."""
    catalog = load_catalog()
    return catalog.get("updated", "unknown")


# Convenience functions for backward compatibility with config.py
def get_anthropic_models() -> Dict[str, Dict[str, Any]]:
    """Get Anthropic models catalog (backward compatibility)."""
    return get_provider_models("anthropic")


def get_openai_models() -> Dict[str, Dict[str, Any]]:
    """Get OpenAI models catalog (backward compatibility)."""
    return get_provider_models("openai")


def get_google_models() -> Dict[str, Dict[str, Any]]:
    """Get Google models catalog (backward compatibility)."""
    return get_provider_models("google")


def get_deepseek_models() -> Dict[str, Dict[str, Any]]:
    """Get DeepSeek models catalog (backward compatibility)."""
    return get_provider_models("deepseek")


def get_groq_models() -> Dict[str, Dict[str, Any]]:
    """Get Groq models catalog (backward compatibility)."""
    return get_provider_models("groq")


def get_grok_models() -> Dict[str, Dict[str, Any]]:
    """Get Grok models catalog (backward compatibility)."""
    return get_provider_models("grok")


def get_openrouter_models() -> Dict[str, Dict[str, Any]]:
    """Get OpenRouter models catalog (backward compatibility)."""
    return get_provider_models("openrouter")


def get_ollama_models() -> Dict[str, Dict[str, Any]]:
    """Get Ollama models catalog (backward compatibility)."""
    return get_provider_models("ollama")


def get_bedrock_models() -> Dict[str, Dict[str, Any]]:
    """Get Bedrock models catalog (backward compatibility)."""
    return get_provider_models("bedrock")
