"""MCP error mapping and sanitization."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, NoReturn

from stratifyai.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    InvalidModelError,
    InvalidProviderError,
    MaxRetriesExceededError,
    ProviderAPIError,
    RateLimitError,
    ValidationError,
)
from stratifyai.utils.sanitizer import sanitize_error


class MCPErrorCode(str, Enum):
    AUTH_FAILED = "auth_failed"
    INVALID_PROVIDER = "invalid_provider"
    INVALID_MODEL = "invalid_model"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_ERROR = "provider_error"
    RATE_LIMITED = "rate_limited"
    CONTENT_TOO_LARGE = "content_too_large"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


EXCEPTION_MAP: dict[type[Exception], MCPErrorCode] = {
    AuthenticationError: MCPErrorCode.AUTH_FAILED,
    InvalidProviderError: MCPErrorCode.INVALID_PROVIDER,
    InvalidModelError: MCPErrorCode.INVALID_MODEL,
    BudgetExceededError: MCPErrorCode.BUDGET_EXCEEDED,
    ProviderAPIError: MCPErrorCode.PROVIDER_ERROR,
    RateLimitError: MCPErrorCode.RATE_LIMITED,
    MaxRetriesExceededError: MCPErrorCode.PROVIDER_ERROR,
    ValidationError: MCPErrorCode.VALIDATION_ERROR,
}


def mcp_error(
    exc: Exception,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Build a structured MCP error dict from a StratifyAI exception.

    The message is sanitized to prevent API key leakage.
    """
    error_code = MCPErrorCode.INTERNAL_ERROR
    for exc_type, code in EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            error_code = code
            break

    message = sanitize_error(str(exc))

    result: dict[str, Any] = {
        "error_code": error_code.value,
        "error_type": type(exc).__name__,
        "message": message,
    }
    if provider is not None:
        result["provider"] = provider
    if model is not None:
        result["model"] = model
    return result


def raise_tool_error(
    exc: Exception,
    provider: str | None = None,
    model: str | None = None,
) -> NoReturn:
    """Raise a ValueError with JSON-serialized MCP error payload.

    FastMCP converts ValueError into a structured tool error response.
    """
    raise ValueError(json.dumps(mcp_error(exc, provider, model))) from exc
