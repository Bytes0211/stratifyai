"""Provider model validation utility.

Validates model availability for all providers using their respective APIs.
"""

import os
import time
from typing import Dict, List, Any, Optional


def validate_provider_models(
    provider: str,
    model_ids: List[str],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate which models are available for a given provider.
    
    Args:
        provider: Provider name (openai, anthropic, google, etc.)
        model_ids: List of model IDs to validate
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        Dict containing:
            - valid_models: List of model IDs that are available
            - invalid_models: List of model IDs that are NOT available
            - validation_time_ms: Time taken to validate in milliseconds
            - error: Error message if validation failed (None if successful)
    """
    validators = {
        "openai": _validate_openai,
        "anthropic": _validate_anthropic,
        "google": _validate_google,
        "deepseek": _validate_deepseek,
        "groq": _validate_groq,
        "grok": _validate_grok,
        "openrouter": _validate_openrouter,
        "ollama": _validate_ollama,
        "bedrock": _validate_bedrock,
    }
    
    validator = validators.get(provider)
    if not validator:
        return {
            "valid_models": model_ids,
            "invalid_models": [],
            "validation_time_ms": 0,
            "error": f"No validator for provider: {provider}",
        }
    
    return validator(model_ids, api_key)


def _validate_openai(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate OpenAI models using models.list() API."""
    result = _init_result()
    start_time = time.time()
    
    try:
        import openai
        
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            result["error"] = "OPENAI_API_KEY not configured"
            result["valid_models"] = model_ids
            return result
        
        client = openai.OpenAI(api_key=key)
        response = client.models.list()
        available_ids = {model.id for model in response.data}
        
        for model_id in model_ids:
            if model_id in available_ids:
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
                
    except ImportError:
        result["error"] = "openai package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_anthropic(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Anthropic credentials (no models list API available)."""
    result = _init_result()
    start_time = time.time()
    
    try:
        import anthropic
        
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            result["error"] = "ANTHROPIC_API_KEY not configured"
            result["valid_models"] = model_ids
            return result
        
        # Anthropic doesn't have a models list API, so we just verify auth
        # by checking if the key format looks valid
        if key.startswith("sk-ant-"):
            result["valid_models"] = model_ids
        else:
            result["error"] = "Invalid API key format"
            result["valid_models"] = model_ids
                
    except ImportError:
        result["error"] = "anthropic package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_google(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Google models using client.models.list()."""
    result = _init_result()
    start_time = time.time()
    
    try:
        from google import genai
        
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            result["error"] = "GOOGLE_API_KEY not configured"
            result["valid_models"] = model_ids
            return result
        
        client = genai.Client(api_key=key)
        models = client.models.list()
        
        # Extract model names (they come as "models/gemini-2.5-pro" format)
        available_ids = set()
        for model in models:
            name = model.name.replace("models/", "")
            available_ids.add(name)
            # Also add without version suffix for matching
            if "-" in name:
                available_ids.add(name.rsplit("-", 1)[0])
        
        for model_id in model_ids:
            # Check exact match or prefix match
            if model_id in available_ids or any(model_id in aid for aid in available_ids):
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
                
    except ImportError:
        result["error"] = "google-genai package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_openai_compatible(
    model_ids: List[str],
    base_url: str,
    api_key: Optional[str],
    env_var: str,
) -> Dict[str, Any]:
    """Generic validator for OpenAI-compatible APIs."""
    result = _init_result()
    start_time = time.time()
    
    try:
        import httpx
        
        key = api_key or os.getenv(env_var)
        if not key:
            result["error"] = f"{env_var} not configured"
            result["valid_models"] = model_ids
            return result
        
        headers = {"Authorization": f"Bearer {key}"}
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
        
        # Extract model IDs from response
        available_ids = set()
        for model in data.get("data", []):
            available_ids.add(model.get("id", ""))
        
        for model_id in model_ids:
            if model_id in available_ids:
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
                
    except ImportError:
        result["error"] = "httpx package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_deepseek(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate DeepSeek models using OpenAI-compatible API."""
    return _validate_openai_compatible(
        model_ids,
        "https://api.deepseek.com/v1",
        api_key,
        "DEEPSEEK_API_KEY",
    )


def _validate_groq(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Groq models using OpenAI-compatible API."""
    return _validate_openai_compatible(
        model_ids,
        "https://api.groq.com/openai/v1",
        api_key,
        "GROQ_API_KEY",
    )


def _validate_grok(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Grok (X.AI) models using OpenAI-compatible API."""
    return _validate_openai_compatible(
        model_ids,
        "https://api.x.ai/v1",
        api_key,
        "GROK_API_KEY",
    )


def _validate_openrouter(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate OpenRouter models using their models API."""
    result = _init_result()
    start_time = time.time()
    
    try:
        import httpx
        
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            result["error"] = "OPENROUTER_API_KEY not configured"
            result["valid_models"] = model_ids
            return result
        
        headers = {"Authorization": f"Bearer {key}"}
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        
        # Extract model IDs from response
        available_ids = set()
        for model in data.get("data", []):
            available_ids.add(model.get("id", ""))
        
        for model_id in model_ids:
            if model_id in available_ids:
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
                
    except ImportError:
        result["error"] = "httpx package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_ollama(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Ollama models using local API."""
    result = _init_result()
    start_time = time.time()
    
    try:
        import httpx
        
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        
        # Extract model names from response
        available_ids = set()
        for model in data.get("models", []):
            name = model.get("name", "")
            available_ids.add(name)
            # Also add without tag suffix (e.g., "llama3.2" from "llama3.2:latest")
            if ":" in name:
                available_ids.add(name.split(":")[0])
        
        for model_id in model_ids:
            if model_id in available_ids:
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
                
    except ImportError:
        result["error"] = "httpx package not installed"
        result["valid_models"] = model_ids
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "ConnectError" in error_msg:
            result["error"] = "Ollama not running (start with: ollama serve)"
        else:
            result["error"] = f"Validation failed: {error_msg}"
        result["valid_models"] = model_ids
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def _validate_bedrock(model_ids: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Validate Bedrock models using boto3."""
    # Import the existing bedrock validator
    from .bedrock_validator import validate_bedrock_models
    return validate_bedrock_models(model_ids)


def _init_result() -> Dict[str, Any]:
    """Initialize empty result dict."""
    return {
        "valid_models": [],
        "invalid_models": [],
        "validation_time_ms": 0,
        "error": None,
    }


def get_validated_interactive_models(provider: str, all_models: bool = False) -> Dict[str, Any]:
    """
    Get validated models for a provider with metadata.
    
    Args:
        provider: Provider name
        all_models: If True, validate ALL models for the provider (not just curated)
        
    Returns:
        Dict containing:
            - models: Dict mapping model_id to metadata
            - validation_result: Full validation result dict
    """
    from ..config import (
        INTERACTIVE_OPENAI_MODELS,
        INTERACTIVE_ANTHROPIC_MODELS,
        INTERACTIVE_GOOGLE_MODELS,
        INTERACTIVE_DEEPSEEK_MODELS,
        INTERACTIVE_GROQ_MODELS,
        INTERACTIVE_GROK_MODELS,
        INTERACTIVE_OPENROUTER_MODELS,
        INTERACTIVE_OLLAMA_MODELS,
        INTERACTIVE_BEDROCK_MODELS,
        OPENAI_MODELS,
        ANTHROPIC_MODELS,
        GOOGLE_MODELS,
        DEEPSEEK_MODELS,
        GROQ_MODELS,
        GROK_MODELS,
        OPENROUTER_MODELS,
        OLLAMA_MODELS,
        BEDROCK_MODELS,
    )
    
    # Map provider to interactive and full model configs
    provider_configs = {
        "openai": (INTERACTIVE_OPENAI_MODELS, OPENAI_MODELS),
        "anthropic": (INTERACTIVE_ANTHROPIC_MODELS, ANTHROPIC_MODELS),
        "google": (INTERACTIVE_GOOGLE_MODELS, GOOGLE_MODELS),
        "deepseek": (INTERACTIVE_DEEPSEEK_MODELS, DEEPSEEK_MODELS),
        "groq": (INTERACTIVE_GROQ_MODELS, GROQ_MODELS),
        "grok": (INTERACTIVE_GROK_MODELS, GROK_MODELS),
        "openrouter": (INTERACTIVE_OPENROUTER_MODELS, OPENROUTER_MODELS),
        "ollama": (INTERACTIVE_OLLAMA_MODELS, OLLAMA_MODELS),
        "bedrock": (INTERACTIVE_BEDROCK_MODELS, BEDROCK_MODELS),
    }
    
    if provider not in provider_configs:
        return {
            "models": {},
            "validation_result": {
                "valid_models": [],
                "invalid_models": [],
                "validation_time_ms": 0,
                "error": f"Unknown provider: {provider}",
            },
        }
    
    interactive_models, full_models = provider_configs[provider]
    
    # Use all models or just curated interactive models
    if all_models:
        model_ids = list(full_models.keys())
    else:
        model_ids = list(interactive_models.keys())
    
    # Validate
    validation_result = validate_provider_models(provider, model_ids)
    
    # Build validated models dict with full metadata
    models = {}
    for model_id in validation_result["valid_models"]:
        interactive_meta = interactive_models.get(model_id, {})
        full_config = full_models.get(model_id, {})
        
        models[model_id] = {
            **full_config,
            **interactive_meta,
        }
    
    return {
        "models": models,
        "validation_result": validation_result,
    }
