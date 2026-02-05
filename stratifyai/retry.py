"""Retry logic with exponential backoff and fallback support."""

import asyncio
import logging
from typing import Callable, List, Optional, Type, Tuple
from functools import wraps
from dataclasses import dataclass

from .exceptions import (
    RateLimitError,
    ProviderAPIError,
    MaxRetriesExceededError,
)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: Tuple[Type[Exception], ...] = (
        RateLimitError,
        ProviderAPIError,
    )


def with_retry(
    config: Optional[RetryConfig] = None,
    fallback_models: Optional[List[str]] = None,
    fallback_provider: Optional[str] = None,
):
    """
    Decorator to add async retry logic with exponential backoff.
    
    Args:
        config: Retry configuration
        fallback_models: List of fallback models to try if primary fails
        fallback_provider: Fallback provider to use if primary fails
        
    Usage:
        @with_retry(config=RetryConfig(max_retries=5))
        async def my_llm_call():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        # Try fallbacks if configured
                        if fallback_models or fallback_provider:
                            logging.info(f"Attempting fallback after {attempt + 1} retries")
                            return await _try_fallback_async(
                                func,
                                args,
                                kwargs,
                                fallback_models,
                                fallback_provider,
                                last_exception,
                            )
                        raise MaxRetriesExceededError(
                            f"Max retries ({config.max_retries}) exceeded. Last error: {str(e)}"
                        )
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())
                    
                    logging.warning(
                        f"Retry attempt {attempt + 1}/{config.max_retries} "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return async_wrapper
    return decorator


async def _try_fallback_async(
    func: Callable,
    args: tuple,
    kwargs: dict,
    fallback_models: Optional[List[str]],
    fallback_provider: Optional[str],
    original_error: Exception,
):
    """
    Try fallback models or providers asynchronously.
    
    Args:
        func: Original async function
        args: Function args
        kwargs: Function kwargs
        fallback_models: List of fallback model names
        fallback_provider: Fallback provider name
        original_error: Original exception that triggered fallback
        
    Returns:
        Result from successful fallback
        
    Raises:
        MaxRetriesExceededError: If all fallbacks fail
    """
    # Try fallback models first
    if fallback_models:
        for model in fallback_models:
            try:
                logging.info(f"Trying fallback model: {model}")
                # Update model in kwargs if present
                if 'request' in kwargs and hasattr(kwargs['request'], 'model'):
                    kwargs['request'].model = model
                elif 'model' in kwargs:
                    kwargs['model'] = model
                return await func(*args, **kwargs)
            except Exception as e:
                logging.warning(f"Fallback model {model} failed: {str(e)}")
                continue
    
    # Try fallback provider
    if fallback_provider:
        try:
            logging.info(f"Trying fallback provider: {fallback_provider}")
            if 'provider' in kwargs:
                kwargs['provider'] = fallback_provider
            return await func(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Fallback provider {fallback_provider} failed: {str(e)}")
    
    # All fallbacks failed
    raise MaxRetriesExceededError(
        f"All retries and fallbacks failed. Original error: {str(original_error)}"
    )


def exponential_backoff(
    attempt: int,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay.
    
    Args:
        attempt: Current attempt number (0-indexed)
        initial_delay: Initial delay in seconds
        exponential_base: Base for exponential growth
        max_delay: Maximum delay cap
        jitter: Add random jitter to delay
        
    Returns:
        Delay in seconds
    """
    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
    
    if jitter:
        import random
        delay *= (0.5 + random.random())
    
    return delay
