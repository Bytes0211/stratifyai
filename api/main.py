"""FastAPI application for StratifyAI."""

import asyncio
import hashlib
import hmac
import logging
import os
import re as _re_module
import shlex
import shutil
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import tomllib
from dotenv import load_dotenv
from fastapi import (
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from stratifyai import ChatRequest, LLMClient, Message, Router, RoutingStrategy
from stratifyai.api_key_helper import APIKeyHelper
from stratifyai.caching import get_cache_stats
from stratifyai.catalog_manager import load_catalog
from stratifyai.config import MODEL_CATALOG
from stratifyai.cost_tracker import CostTracker
from stratifyai.exceptions import AuthenticationError
from stratifyai.mcp_catalog import (
    build_claude_code_commands,
    build_client_config,
    detect_client_config_path,
    get_configured_servers,
    get_mcp_client_settings,
    remove_server_from_config,
    remove_servers_from_config,
    validate_prerequisites,
    write_client_config,
    write_mcp_client_settings,
)
from stratifyai.mcp_catalog import (
    load_catalog as load_mcp_server_catalog,
)
from stratifyai.mcp_client import MCPClientEngine
from stratifyai.mcp_client.permissions import ServerPermissionConfig
from stratifyai.middleware import TrackedLLMClient
from stratifyai.observability import (
    bind_correlation_id,
    build_log_extra,
    metrics_registry,
    reset_correlation_id,
)
from stratifyai.utils.reasoning_detector import (
    get_temperature_for_model,
    is_reasoning_model,
)
from stratifyai.utils.sanitizer import sanitize_error

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Read version from pyproject.toml (single source of truth)
def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project = data.get("project")
                if isinstance(project, dict):
                    version = project.get("version")
                    if isinstance(version, str):
                        return version
    except Exception:
        pass
    return "2.1.0"


API_VERSION = _get_version()
APP_START_TIME = time.time()


def _format_timestamp(value: float | None) -> str | None:
    """Format UNIX timestamps as UTC ISO-8601 strings for API responses."""
    if value is None:
        return None
    return (
        datetime.fromtimestamp(value, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _get_executor_max_workers() -> int:
    """Return a safe ThreadPoolExecutor size from environment configuration."""
    raw_value = os.getenv("STRATIFYAI_THREAD_POOL_WORKERS", "4")
    try:
        workers = int(raw_value)
    except (TypeError, ValueError):
        return 4
    return workers if 1 <= workers <= 32 else 4


# Shared ThreadPoolExecutor for async validation tasks (BUG-008)
_executor = ThreadPoolExecutor(max_workers=_get_executor_max_workers())

# Cache for catalog validation results with TTL (P1: avoid live API calls on every request)
_catalog_cache: dict[str, Any] | None = None
_catalog_cache_ts: float = 0.0
_all_models_cache: dict[str, Any] | None = None
_all_models_cache_ts: float = 0.0
_CATALOG_CACHE_TTL = 300.0  # 5 minutes in seconds

# Client cache for connection pooling (BUG-003)
_client_cache: dict[str, LLMClient] = {}
_client_cache_lock = threading.Lock()
_mcp_chat_engine: MCPClientEngine | None = None
_mcp_chat_engine_lock: asyncio.Lock | None = None
_mcp_chat_engine_lock_loop: asyncio.AbstractEventLoop | None = None


def get_client(provider: str) -> LLMClient:
    """Get or create a cached LLMClient for connection pooling."""
    with _client_cache_lock:
        if provider not in _client_cache:
            _client_cache[provider] = LLMClient(provider=provider)
        return _client_cache[provider]


def get_tracked_client(provider: str) -> TrackedLLMClient:
    """Get a TrackedLLMClient wrapping the cached LLMClient."""
    return TrackedLLMClient(client=get_client(provider), cost_tracker=cost_tracker)


def _get_mcp_chat_engine_lock() -> asyncio.Lock:
    """Return a loop-local async lock for lazy MCP engine initialization."""
    global _mcp_chat_engine_lock, _mcp_chat_engine_lock_loop
    loop = asyncio.get_running_loop()
    if _mcp_chat_engine_lock is None or _mcp_chat_engine_lock_loop is not loop:
        _mcp_chat_engine_lock = asyncio.Lock()
        _mcp_chat_engine_lock_loop = loop
    return _mcp_chat_engine_lock


async def get_mcp_chat_engine(refresh: bool = False) -> MCPClientEngine:
    """Get or lazily initialize the shared MCP chat engine.

    When ``refresh`` is true, the engine re-reads supported local MCP client
    config files (Claude Desktop, Cursor, VS Code) so newly configured servers
    appear in the Web UI without requiring an API restart.

    Note: initialization is intentionally lazy and non-connecting here. Passive
    dashboard loads should not try to spawn every external MCP server because a
    single misconfigured server must not take down the whole Web UI with a 500.
    Servers are started on demand when the user explicitly starts one or a chat
    session attempts to use it.
    """
    global _mcp_chat_engine
    if _mcp_chat_engine is None or refresh:
        async with _get_mcp_chat_engine_lock():
            if _mcp_chat_engine is None:
                _mcp_chat_engine = MCPClientEngine(client="auto")
            elif refresh:
                await _mcp_chat_engine.sync_configured_servers(client="auto")
    return _mcp_chat_engine


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Extract bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    return token or None


def _hash_token(token: str) -> str:
    """Return a short stable hash for a token without exposing raw values."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def _rate_limit_key(request: Request) -> str:
    """Use API key hash for rate limiting, fallback to client IP when absent."""
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token:
        return f"key:{_hash_token(token)}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def _sanitize_error_payload(value: Any) -> Any:
    """Recursively sanitize error payloads before logging or returning to clients."""
    if isinstance(value, str):
        return sanitize_error(value)
    if isinstance(value, dict):
        return {k: _sanitize_error_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_error_payload(item) for item in value]
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: emit startup warnings."""
    if not os.getenv("STRATIFYAI_API_KEY"):
        logger.warning(
            "STRATIFYAI_API_KEY is not set. API auth is disabled (development mode)."
        )
    yield

    global _mcp_chat_engine
    if _mcp_chat_engine is not None:
        await _mcp_chat_engine.stop()
        _mcp_chat_engine = None


# Initialize FastAPI app
app = FastAPI(
    title="StratifyAI API",
    description="Unified API for multiple LLM providers",
    version=API_VERSION,
    lifespan=lifespan,
)
limiter = Limiter(key_func=_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    """Attach correlation IDs and record basic HTTP observability."""
    correlation_id, token = bind_correlation_id(request.headers.get("X-Correlation-ID"))
    request.state.correlation_id = correlation_id

    start = time.perf_counter()
    metrics_registry.record_http_request(request.method, request.url.path)
    logger.info(
        "HTTP request started: %s %s",
        request.method,
        request.url.path,
        extra=build_log_extra(method=request.method, path=request.url.path),
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        metrics_registry.record_http_response(
            request.method, request.url.path, 500, duration_ms
        )
        logger.exception(
            "HTTP request failed: %s %s latency=%.0fms",
            request.method,
            request.url.path,
            duration_ms,
            extra=build_log_extra(
                method=request.method,
                path=request.url.path,
                latency_ms=duration_ms,
                status_code=500,
            ),
        )
        reset_correlation_id(token)
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    metrics_registry.record_http_response(
        request.method, request.url.path, response.status_code, duration_ms
    )
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(
        "HTTP request completed: %s %s status=%d latency=%.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra=build_log_extra(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=duration_ms,
        ),
    )
    reset_correlation_id(token)
    return response


# Configure CORS with safer defaults.
# - In development, localhost origins are allowed by default.
# - Wildcard mode requires explicit CORS_ALLOW_ALL=true.
_default_local_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS")
_cors_allow_all = os.getenv("CORS_ALLOW_ALL", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if _cors_allow_all:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
else:
    _allowed_origins = (
        [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
        if _cors_origins
        else _default_local_origins
    )
    if os.getenv("STRATIFYAI_API_KEY") and not _cors_origins:
        logger.warning(
            "CORS_ALLOWED_ORIGINS not set while STRATIFYAI_API_KEY is enabled. "
            "Using localhost-only defaults. Set CORS_ALLOWED_ORIGINS for production."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )

# Global cost tracker
cost_tracker = CostTracker()

# Upper bound for inbound websocket payload size (raw JSON text length)
_WS_MAX_PAYLOAD_CHARS = 2_000_000
# Upper bound for attached file payload size before any decoding/processing.
_MAX_FILE_PAYLOAD_CHARS = 5_000_000

_SUMMARIZATION_MODEL_BY_PROVIDER = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "google": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.1-8b-instant",
    "grok": "grok-4-1-fast-non-reasoning",
    "openrouter": "google/gemini-2.5-flash",
    "ollama": "llama3.2",
    "bedrock": "anthropic.claude-3-5-haiku-20241022-v1:0",
}

# WebSocket rate limiting with TTL eviction.
# Each key is a client IP mapping to a deque of request timestamps.
# _WS_RATE_LIMIT_MAX_IPS caps the total number of tracked IPs so that
# a long-running server doesn't leak memory from unique visitors.
_ws_rate_limit: dict[str, deque] = defaultdict(deque)
_ws_rate_limit_lock = threading.RLock()
_WS_RATE_LIMIT_MAX_IPS = 10_000
_WS_RATE_LIMIT_WINDOW_SECS = 60

_VALID_MESSAGE_ROLES = frozenset({"system", "user", "assistant"})


def _ensure_file_payload_size(file_content: str | None, file_name: str | None) -> None:
    """Reject oversized file payloads before decoding or temporary-file work."""
    if not file_content:
        return

    if len(file_content) > _MAX_FILE_PAYLOAD_CHARS:
        label = file_name or "attached file"
        raise HTTPException(
            status_code=413,
            detail={
                "error": "file_too_large",
                "message": (
                    f"{label} exceeds the maximum allowed size of "
                    f"{_MAX_FILE_PAYLOAD_CHARS:,} characters"
                ),
                "max_chars": _MAX_FILE_PAYLOAD_CHARS,
            },
        )


def _get_summarization_model(provider: str) -> str:
    """Return the low-cost summarization model configured for a provider."""
    return _SUMMARIZATION_MODEL_BY_PROVIDER.get(provider, "gpt-4o-mini")


def _evict_stale_ws_entries() -> None:
    """Remove expired sliding-window entries and prune idle IPs.

    Called once per WebSocket connection before the per-IP check so that
    the dict never grows unboundedly.
    """
    with _ws_rate_limit_lock:
        now = time.time()
        stale_ips: list[str] = []
        for ip, window in list(_ws_rate_limit.items()):
            # Drop timestamps older than the window
            while window and now - window[0] > _WS_RATE_LIMIT_WINDOW_SECS:
                window.popleft()
            # Mark empty windows for removal
            if not window:
                stale_ips.append(ip)
        for ip in stale_ips:
            del _ws_rate_limit[ip]

        # Hard cap: if still too many IPs, drop the oldest half
        if len(_ws_rate_limit) > _WS_RATE_LIMIT_MAX_IPS:
            sorted_ips = sorted(
                _ws_rate_limit,
                key=lambda k: _ws_rate_limit[k][0] if _ws_rate_limit[k] else 0,
            )
            for ip in sorted_ips[: len(sorted_ips) // 2]:
                del _ws_rate_limit[ip]


def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    """Verify bearer token if STRATIFYAI_API_KEY is configured.

    Uses ``hmac.compare_digest`` for constant-time comparison to prevent
    timing side-channel attacks.
    """
    expected = os.getenv("STRATIFYAI_API_KEY")
    if not expected:
        return
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _sanitize_file_name(file_name: str | None) -> str | None:
    """Validate and sanitize user-supplied filename."""
    if not file_name:
        return None
    if len(file_name) > 255:
        raise HTTPException(status_code=400, detail="Invalid file_name: too long")
    if any(ord(c) < 32 for c in file_name) or "\x00" in file_name:
        raise HTTPException(
            status_code=400, detail="Invalid file_name: contains control characters"
        )
    return Path(file_name).name


def _enforce_budget() -> None:
    """Block cost-incurring calls when budget is exceeded."""
    if cost_tracker.is_over_budget():
        raise HTTPException(
            status_code=402,
            detail={"error": "budget_exceeded", "message": "Budget limit reached"},
        )


# Mount static files - serve both legacy static assets and new SPA build
static_dir = os.path.join(os.path.dirname(__file__), "static")
dist_dir = os.path.join(static_dir, "dist")

# Check for SPA build first (Vite outputs to dist/)
if os.path.exists(dist_dir):
    # Mount dist assets at root for SPA
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(dist_dir, "assets")),
        name="assets",
    )
# Always mount static for logos and legacy files
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Request/Response models
class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""

    provider: str
    model: str
    messages: list[dict]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    file_content: str | None = None  # Base64 encoded file content or plain text
    file_name: str | None = None  # Original filename for type detection
    chunked: bool = False  # Enable smart chunking and summarization
    chunk_size: int = Field(default=50000, ge=1000, le=100000)
    active_mcp_servers: list[str] = Field(default_factory=list)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in MODEL_CATALOG:
            raise ValueError(
                f"provider must be one of: {', '.join(sorted(MODEL_CATALOG))}"
            )
        return value

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value: list[dict]) -> list[dict]:
        if not value:
            raise ValueError("messages must be a non-empty list")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return value

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 4_000_000:
            raise ValueError("max_tokens must be between 1 and 4000000")
        return value


class StreamMessage(BaseModel):
    """Validated message payload for WebSocket and HTTP requests."""

    role: str
    content: str = Field(min_length=1, max_length=1_000_000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        allowed = {"system", "user", "assistant"}
        if value not in allowed:
            raise ValueError("role must be one of: system, user, assistant")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        # Block null bytes and most control chars in inbound payload.
        for char in value:
            if ord(char) < 32 and char not in "\n\r\t":
                raise ValueError("content contains invalid control characters")
        return value


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""

    id: str
    provider: str
    model: str
    content: str
    finish_reason: str
    usage: dict
    cost_usd: float
    warnings: list[str] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    active_mcp_servers: list[str] = Field(default_factory=list)


class ProviderInfo(BaseModel):
    """Provider information model."""

    name: str
    models: list[str]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str
    error_type: str


def _get_spa_index() -> str | None:
    """Get path to SPA index.html if it exists."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    # Check for SPA build first
    spa_index = os.path.join(static_dir, "dist", "index.html")
    if os.path.exists(spa_index):
        return spa_index
    # Fall back to legacy index.html
    legacy_index = os.path.join(static_dir, "index.html")
    if os.path.exists(legacy_index):
        return legacy_index
    return None


def _check_token_limits(
    messages: list,
    provider: str,
    model: str,
) -> None:
    """Validate assembled messages against model token limits.

    Raises :class:`~fastapi.HTTPException` with status 413 when the estimated
    token count exceeds either the hard system limit or the effective model/API
    limit.  Shared between the REST endpoint and the WebSocket streaming handler
    so both paths enforce identical rules.
    """
    from stratifyai.utils.token_counter import (
        count_tokens_for_messages,
        get_context_window,
    )

    estimated_tokens = count_tokens_for_messages(messages, provider, model)

    context_window = get_context_window(provider, model)
    model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
    api_max_input = model_info.get("api_max_input")
    effective_limit = (
        api_max_input
        if api_max_input and api_max_input < context_window
        else context_window
    )

    MAX_SYSTEM_LIMIT = 1_000_000
    if estimated_tokens > MAX_SYSTEM_LIMIT:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "content_too_large",
                "message": (
                    f"File is too large to process. The content has approximately "
                    f"{estimated_tokens:,} tokens, which exceeds the system's maximum "
                    f"limit of {MAX_SYSTEM_LIMIT:,} tokens."
                ),
                "estimated_tokens": estimated_tokens,
                "system_limit": MAX_SYSTEM_LIMIT,
                "provider": provider,
                "model": model,
                "suggestion": "Please split your file into smaller chunks or use a different processing approach.",
            },
        )

    if estimated_tokens > effective_limit:
        if api_max_input and context_window > api_max_input:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "input_too_long",
                    "message": (
                        f"Input is too long for {model}. The content has approximately "
                        f"{estimated_tokens:,} tokens, but the API restricts input to "
                        f"{api_max_input:,} tokens (despite the model's {context_window:,} "
                        f"token context window)."
                    ),
                    "estimated_tokens": estimated_tokens,
                    "api_limit": api_max_input,
                    "context_window": context_window,
                    "provider": provider,
                    "model": model,
                    "suggestion": (
                        "✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n"
                        "✓ Switch to Google Gemini models (no API input limits): "
                        "gemini-2.5-pro, gemini-2.5-flash\n"
                        "✓ Switch to OpenRouter with google/gemini-2.5-pro or "
                        "google/gemini-2.5-flash"
                    ),
                },
            )
        else:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "input_too_long",
                    "message": (
                        f"Input is too long for {model}. The content has approximately "
                        f"{estimated_tokens:,} tokens, which exceeds the model's maximum "
                        f"of {effective_limit:,} tokens."
                    ),
                    "estimated_tokens": estimated_tokens,
                    "model_limit": effective_limit,
                    "provider": provider,
                    "model": model,
                    "suggestion": (
                        "✓ Switch to a model with larger context window:\n"
                        "  - Google Gemini 2.5 Pro (1M tokens, no API limits)\n"
                        "  - Google Gemini 2.5 Flash (1M tokens, cheaper)\n"
                        "  - Claude Opus 4.5 (1M context, 200k API limit)\n"
                        "✓ Enable 'Smart Chunking' to reduce token usage"
                    ),
                },
            )


@app.get("/")
async def root():
    """Serve the frontend interface (SPA or legacy)."""
    index_path = _get_spa_index()
    if index_path:
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    return {
        "name": "StratifyAI API",
        "version": API_VERSION,
        "message": "Frontend not found. API endpoints available at /docs",
    }


@app.get("/models")
async def models_page():
    """Serve the models catalog page (SPA catch-all or legacy)."""
    # For SPA, return index.html for client-side routing
    index_path = _get_spa_index()
    if index_path and "dist" in index_path:
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    # Legacy: serve models.html
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    models_path = os.path.join(static_dir, "models.html")
    if os.path.exists(models_path):
        return FileResponse(models_path)
    return {"error": "Models page not found"}


@app.get("/mcp")
async def mcp_page():
    """Serve the MCP management SPA route."""
    index_path = _get_spa_index()
    if index_path:
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    return {"error": "MCP page not found"}


@app.get("/api/providers", response_model=list[str])
async def list_providers(_: None = Depends(verify_api_key)):
    """List all available providers."""
    return [
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "groq",
        "grok",
        "ollama",
        "openrouter",
        "bedrock",
    ]


class ModelInfo(BaseModel):
    """Model information."""

    id: str  # Model ID (e.g., 'gpt-4o')
    display_name: str  # Display name (e.g., 'GPT-4o')
    description: str = ""  # Description with labels
    category: str = ""  # Category for grouping
    reasoning_model: bool = False
    supports_vision: bool = False


class ModelListResponse(BaseModel):
    """Model list response with validation metadata."""

    models: list[ModelInfo]
    validation: dict


@app.get("/api/models/{provider}", response_model=ModelListResponse)
async def list_models(provider: str, _: None = Depends(verify_api_key)):
    """List validated models for a specific provider."""
    from stratifyai.utils.provider_validator import get_validated_interactive_models

    if provider not in MODEL_CATALOG:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    # Run validation in background thread to avoid blocking (BUG-007: use get_running_loop)
    loop = asyncio.get_running_loop()
    validation_data = await loop.run_in_executor(
        _executor, get_validated_interactive_models, provider
    )

    validated_models = validation_data["models"]
    validation_result = validation_data["validation_result"]

    # Determine api_key_set based on error message
    error_msg = validation_result.get("error", "")
    api_key_set = not (
        error_msg
        and (
            "not configured" in error_msg.lower()
            or "api key" in error_msg.lower()
            or "api_key" in error_msg.lower()
        )
    )

    # Add api_key_set and validated to validation result for frontend
    validation_result["api_key_set"] = api_key_set
    validation_result["validated"] = validation_result["error"] is None

    # Log validation result
    if validation_result["error"]:
        logger.warning(
            "Model validation for %s: %s",
            provider,
            sanitize_error(str(validation_result["error"])),
        )
    else:
        logger.info(
            f"Model validation for {provider}: {len(validated_models)} models in {validation_result['validation_time_ms']}ms"
        )

    # If validation succeeded: return only validated models with metadata
    # If validation failed with error: fall back to catalog
    if validation_result["error"]:
        # Fallback to catalog when validation fails
        model_ids = list(MODEL_CATALOG[provider].keys())
        model_metadata = MODEL_CATALOG[provider]
    else:
        # Show only validated models on success
        model_ids = list(validated_models.keys())
        model_metadata = validated_models

    # Build model info list with rich metadata
    models_info = []
    for model_id in model_ids:
        meta = model_metadata.get(model_id, {})
        models_info.append(
            ModelInfo(
                id=model_id,
                display_name=meta.get("display_name", model_id),
                description=meta.get("description", ""),
                category=meta.get("category", ""),
                reasoning_model=meta.get("reasoning_model", False),
                supports_vision=meta.get("supports_vision", False),
            )
        )

    return ModelListResponse(models=models_info, validation=validation_result)


@app.get("/api/model-info/{provider}/{model}")
async def get_model_info(provider: str, model: str, _: None = Depends(verify_api_key)):
    """Get detailed information about a specific model."""
    if provider not in MODEL_CATALOG:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    if model not in MODEL_CATALOG[provider]:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model}' not found for provider '{provider}'",
        )

    model_info = MODEL_CATALOG[provider][model]

    return {
        "provider": provider,
        "model": model,
        "fixed_temperature": model_info.get("fixed_temperature"),
        "reasoning_model": model_info.get("reasoning_model", False),
        "supports_vision": model_info.get("supports_vision", False),
        "supports_tools": model_info.get("supports_tools", False),
        "supports_caching": model_info.get("supports_caching", False),
        "context": model_info.get("context", 0),
    }


@app.get("/api/provider-info", response_model=list[ProviderInfo])
async def get_provider_info(_: None = Depends(verify_api_key)):
    """Get information about all providers and their models."""
    providers = []
    for provider_name, models in MODEL_CATALOG.items():
        providers.append(ProviderInfo(name=provider_name, models=list(models.keys())))
    return providers


@app.post("/api/chat", response_model=ChatCompletionResponse)
@limiter.limit("30/minute")
async def chat_completion(
    request: Request, payload: ChatCompletionRequest, _: None = Depends(verify_api_key)
):
    """
    Execute a chat completion request.

    Args:
        request: Chat completion request

    Returns:
        Chat completion response with cost tracking
    """
    try:
        logger.info(
            "Chat completion requested: provider=%s model=%s",
            payload.provider,
            payload.model,
            extra=build_log_extra(
                provider=payload.provider,
                model=payload.model,
                route="/api/chat",
            ),
        )
        # Validate and convert messages to Message objects
        messages = [
            Message(role=msg.role, content=msg.content)
            for msg in (StreamMessage.model_validate(msg) for msg in payload.messages)
        ]
        _enforce_budget()

        # Process file if provided (text files only - images are handled in message content by frontend)
        safe_file_name = _sanitize_file_name(payload.file_name)
        _ensure_file_payload_size(payload.file_content, safe_file_name)
        if payload.file_content and safe_file_name:
            logger.info(
                f"Processing file attachment: {safe_file_name} (content length: {len(payload.file_content)} chars)"
            )
            import base64
            import tempfile
            from pathlib import Path

            from stratifyai.summarization import summarize_file_async
            from stratifyai.utils.file_analyzer import analyze_file

            # Handle text files (images are now formatted in message content by frontend)
            # Detect if content is base64 encoded or plain text
            try:
                # Try to decode as base64
                file_bytes = base64.b64decode(payload.file_content)
                file_text = file_bytes.decode("utf-8")
            except Exception:
                # If decoding fails, assume it's plain text
                file_text = payload.file_content

            # Apply chunking if enabled
            if payload.chunked:
                logger.info(
                    f"Chunking file {safe_file_name} (size: {len(file_text)} chars, chunk_size: {payload.chunk_size})"
                )

                # Create temporary file for analysis
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=Path(safe_file_name).suffix, delete=False
                ) as tmp_file:
                    tmp_file.write(file_text)
                    tmp_path = Path(tmp_file.name)  # Convert to Path object

                try:
                    # Analyze file to determine if chunking is beneficial
                    analysis = analyze_file(tmp_path, payload.provider, payload.model)
                    logger.info(
                        f"File analysis: type={analysis.file_type.value}, tokens={analysis.estimated_tokens}"
                    )

                    # Perform chunking and summarization using the provider's
                    # configured low-cost summarization model.
                    summarization_model = _get_summarization_model(payload.provider)

                    client = get_client(payload.provider)  # BUG-003: Use cached client

                    # Get context from last user message if available
                    context = None
                    if messages and messages[-1].role == "user":
                        context = messages[-1].content

                    # Run async summarization with cheap model
                    result = await summarize_file_async(
                        file_text,
                        client,
                        payload.chunk_size,
                        summarization_model,
                        context,
                        False,  # show_progress=False for API
                    )

                    # Use summarized content
                    file_content_to_use = result["summary"]
                    logger.info(
                        f"Chunking complete: {result['reduction_percentage']}% reduction ({result['original_length']} -> {result['summary_length']} chars)"
                    )
                finally:
                    # Clean up temp file
                    import os

                    os.unlink(tmp_path)
            else:
                # Use file content as-is
                file_content_to_use = file_text

            # Append file content to last user message or create new message
            if messages and messages[-1].role == "user":
                # Combine with existing user message
                messages[
                    -1
                ].content = f"{messages[-1].content}\n\n[File: {safe_file_name}]\n\n{file_content_to_use}"
            else:
                # Create new user message with file content
                messages.append(
                    Message(
                        role="user",
                        content=f"[File: {safe_file_name}]\n\n{file_content_to_use}",
                    )
                )

        # Validate token count before making request
        _check_token_limits(messages, payload.provider, payload.model)

        # Determine temperature using shared reasoning model detector (BUG-002)
        reasoning = is_reasoning_model(payload.provider, payload.model, MODEL_CATALOG)
        temperature = get_temperature_for_model(
            payload.provider, payload.model, payload.temperature, MODEL_CATALOG
        )

        if reasoning and payload.temperature is not None and payload.temperature != 1.0:
            logger.warning(
                f"Overriding temperature={payload.temperature} to 1.0 for reasoning model {payload.provider}/{payload.model}"
            )
        else:
            logger.info(
                f"Using temperature={temperature} for model {payload.provider}/{payload.model}"
            )

        # Create chat request
        chat_request = ChatRequest(
            model=payload.model,
            messages=messages,
            temperature=temperature,
            max_tokens=payload.max_tokens,
        )

        # Initialize tracked client (middleware handles latency + cost tracking)
        tracked = get_tracked_client(payload.provider)
        if payload.active_mcp_servers:
            engine = await get_mcp_chat_engine()
            response = await tracked.chat_with_mcp(
                model=payload.model,
                messages=messages,
                mcp_engine=engine,
                active_servers=payload.active_mcp_servers,
                temperature=temperature,
                max_tokens=payload.max_tokens,
            )
        else:
            response = await tracked.chat_completion(chat_request)

        raw_response = (
            response.raw_response if isinstance(response.raw_response, dict) else {}
        )

        return ChatCompletionResponse(
            id=response.id,
            provider=response.provider,
            model=response.model,
            content=response.content,
            finish_reason=response.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cost_usd": response.usage.cost_usd,
                "latency_ms": round(response.latency_ms or 0, 2),
            },
            cost_usd=response.usage.cost_usd,
            warnings=list(raw_response.get("mcp_warnings", [])),
            tool_results=list(raw_response.get("mcp_tool_results", [])),
            active_mcp_servers=list(
                raw_response.get("mcp_active_servers", payload.active_mcp_servers)
            ),
        )
    except HTTPException:
        # Re-raise our custom HTTP exceptions (token limits, etc.)
        raise
    except Exception as e:
        error_msg = str(e)
        sanitized_error = sanitize_error(error_msg)
        logger.error("Chat completion error: %s", sanitized_error)

        # Determine error type and status code
        status_code = 500
        error_type = "internal_error"
        suggestion = None

        if "insufficient balance" in error_msg.lower():
            status_code = 402
            error_type = "insufficient_balance_error"
        elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            status_code = 401
            error_type = "authentication_error"
        elif "rate limit" in error_msg.lower():
            status_code = 429
            error_type = "rate_limit_error"
        elif "not found" in error_msg.lower():
            status_code = 404
            error_type = "not_found_error"
        elif "invalid model" in error_msg.lower():
            status_code = 400
            error_type = "invalid_model_error"
        elif "temperature" in error_msg.lower() and "not support" in error_msg.lower():
            status_code = 400
            error_type = "invalid_parameter_error"
        # Catch provider API token limit errors that slip through
        elif "too long" in error_msg.lower() or "maximum" in error_msg.lower():
            status_code = 413
            error_type = "input_too_long"

            # Extract token count from error if available
            import re

            token_match = re.search(r"(\d+)\s+tokens?\s+>\s+(\d+)", error_msg)
            if token_match:
                actual_tokens = int(token_match.group(1))
                limit_tokens = int(token_match.group(2))

                # Get model info to provide smart suggestions
                model_info = MODEL_CATALOG.get(payload.provider, {}).get(
                    payload.model, {}
                )
                context_window = model_info.get("context", 0)
                api_max_input = model_info.get("api_max_input")

                if api_max_input and context_window > api_max_input:
                    suggestion = f"✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, gemini-2.5-flash\n✓ Your input: {actual_tokens:,} tokens | API limit: {limit_tokens:,} tokens | Model context: {context_window:,} tokens"
                else:
                    suggestion = f"✓ Switch to a model with larger context window (Google Gemini 2.5: 1M tokens)\n✓ Enable 'Smart Chunking' to reduce token usage\n✓ Your input: {actual_tokens:,} tokens | Model limit: {limit_tokens:,} tokens"

        detail = {
            "error": error_type,
            "detail": sanitized_error,
            "provider": payload.provider,
            "model": payload.model,
        }

        if suggestion:
            detail["suggestion"] = suggestion

        raise HTTPException(status_code=status_code, detail=detail) from e


@app.websocket("/api/chat/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat completions.

    Protocol:
        Client sends JSON: {"provider": "openai", "model": "gpt-4", "messages": [...]}
        Server streams JSON chunks: {"content": "...", "done": false}
        Final message: {"content": "", "done": true, "usage": {...}}
    """
    correlation_id, token = bind_correlation_id(
        websocket.headers.get("x-correlation-id")
    )
    accepted = False

    try:
        # --- Authentication before accept (timing-safe close on failure) ----
        auth_header = websocket.headers.get("authorization")
        verify_api_key(auth_header)

        await websocket.accept()
        accepted = True

        # Receive request
        data = await websocket.receive_text()
        if len(data) > _WS_MAX_PAYLOAD_CHARS:
            await websocket.send_json(
                {
                    "error": "request_too_large",
                    "detail": "WebSocket payload exceeds maximum allowed size",
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        # --- Rate limiting with TTL eviction --------------------------------
        auth_token = _extract_bearer_token(auth_header)
        client_ip = websocket.client.host if websocket.client else "unknown"
        ws_key = f"key:{_hash_token(auth_token)}" if auth_token else f"ip:{client_ip}"
        now = time.time()
        with _ws_rate_limit_lock:
            _evict_stale_ws_entries()
            window = _ws_rate_limit[ws_key]
            # Per-IP window cleanup (fast path — global eviction already ran)
            while window and now - window[0] > _WS_RATE_LIMIT_WINDOW_SECS:
                window.popleft()
            exceeded_rate_limit = len(window) >= 30
            if not exceeded_rate_limit:
                window.append(now)
        if exceeded_rate_limit:
            await websocket.send_json(
                {
                    "error": "rate_limit_exceeded",
                    "retry_after": _WS_RATE_LIMIT_WINDOW_SECS,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        # --- Pydantic validation --------------------------------------------
        request_obj = ChatCompletionRequest.model_validate_json(data)

        provider = request_obj.provider
        model = request_obj.model
        messages_data = request_obj.messages
        requested_temperature = request_obj.temperature
        max_tokens = request_obj.max_tokens
        file_content = request_obj.file_content
        file_name = _sanitize_file_name(request_obj.file_name)
        _ensure_file_payload_size(file_content, file_name)
        active_mcp_servers = request_obj.active_mcp_servers

        # --- Provider/model validation (WebSocket-safe) ---------------------
        if provider not in MODEL_CATALOG:
            await websocket.send_json(
                {
                    "error": "invalid_provider",
                    "detail": f"Unknown provider: {provider}",
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return
        if model not in MODEL_CATALOG[provider]:
            await websocket.send_json(
                {
                    "error": "invalid_model",
                    "detail": f"Unknown model '{model}' for provider '{provider}'",
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        # --- Temperature bounds check (WebSocket-safe) ----------------------
        if requested_temperature is not None and not (
            0.0 <= requested_temperature <= 2.0
        ):
            await websocket.send_json(
                {
                    "error": "invalid_temperature",
                    "detail": f"Temperature must be between 0.0 and 2.0, got {requested_temperature}",
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        metrics_registry.record_stream_request(provider, model)

        # Debug logging
        logger.info(
            f"[WebSocket] Request keys: {list(request_obj.model_dump().keys())}"
        )
        logger.info(
            f"[WebSocket] Has file: file_content={bool(file_content)}, file_name={file_name}"
        )
        chunked = request_obj.chunked
        chunk_size = request_obj.chunk_size

        # --- Budget enforcement (WebSocket-safe) ----------------------------
        try:
            _enforce_budget()
        except HTTPException as budget_exc:
            detail = budget_exc.detail
            await websocket.send_json(
                {
                    "error": (
                        detail.get("error", "budget_exceeded")
                        if isinstance(detail, dict)
                        else "budget_exceeded"
                    ),
                    "detail": (
                        detail.get("message", str(detail))
                        if isinstance(detail, dict)
                        else str(detail)
                    ),
                    "done": True,
                }
            )
            return

        # Convert messages
        messages = [
            Message(role=msg.role, content=msg.content)
            for msg in (StreamMessage.model_validate(msg) for msg in messages_data)
        ]

        # Process file if provided (text files only - images are handled in message content by frontend)
        if file_content and file_name:
            logger.info(
                f"[WebSocket] Processing file attachment: {file_name} (content length: {len(file_content)} chars)"
            )
            import base64
            import tempfile
            from pathlib import Path

            from stratifyai.summarization import summarize_file_async
            from stratifyai.utils.file_analyzer import analyze_file

            # Handle text files (images are now formatted in message content by frontend)
            # Detect if content is base64 encoded or plain text
            try:
                # Try to decode as base64
                file_bytes = base64.b64decode(file_content)
                file_text = file_bytes.decode("utf-8")
            except Exception:
                # If decoding fails, assume it's plain text
                file_text = file_content

            # Apply chunking if enabled
            if chunked:
                logger.info(
                    f"[WebSocket] Chunking file {file_name} (size: {len(file_text)} chars, chunk_size: {chunk_size})"
                )

                # Create temporary file for analysis
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=Path(file_name).suffix, delete=False
                ) as tmp_file:
                    tmp_file.write(file_text)
                    tmp_path = Path(tmp_file.name)

                try:
                    # Analyze file
                    analysis = analyze_file(tmp_path, provider, model)
                    logger.info(
                        f"[WebSocket] File analysis: type={analysis.file_type.value}, tokens={analysis.estimated_tokens}"
                    )

                    # Perform chunking and summarization using the provider's
                    # configured low-cost summarization model.
                    summarization_model = _get_summarization_model(provider)

                    client = get_client(provider)

                    # Get context from last user message if available
                    context = None
                    if messages and messages[-1].role == "user":
                        context = messages[-1].content

                    # Run async summarization
                    result = await summarize_file_async(
                        file_text,
                        client,
                        chunk_size,
                        summarization_model,
                        context,
                        False,
                    )

                    file_content_to_use = result["summary"]
                    logger.info(
                        f"[WebSocket] Chunking complete: {result['reduction_percentage']}% reduction"
                    )
                finally:
                    import os

                    os.unlink(tmp_path)
            else:
                file_content_to_use = file_text

            # Append file content to last user message or create new message
            if messages and messages[-1].role == "user":
                messages[
                    -1
                ].content = f"{messages[-1].content}\n\n[File: {file_name}]\n\n{file_content_to_use}"
            else:
                messages.append(
                    Message(
                        role="user",
                        content=f"[File: {file_name}]\n\n{file_content_to_use}",
                    )
                )

        # Validate token count before making request (parity with REST path)
        try:
            _check_token_limits(messages, provider, model)
        except HTTPException as exc:
            detail = exc.detail
            await websocket.send_json(
                {
                    "error": (
                        detail.get("error", "content_too_large")
                        if isinstance(detail, dict)
                        else "content_too_large"
                    ),
                    "detail": (
                        detail.get("message", str(detail))
                        if isinstance(detail, dict)
                        else str(detail)
                    ),
                    "estimated_tokens": (
                        detail.get("estimated_tokens")
                        if isinstance(detail, dict)
                        else None
                    ),
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        # Determine temperature using shared reasoning model detector (BUG-002)
        reasoning = is_reasoning_model(provider, model, MODEL_CATALOG)
        temperature = get_temperature_for_model(
            provider, model, requested_temperature, MODEL_CATALOG
        )

        if (
            reasoning
            and requested_temperature is not None
            and requested_temperature != 1.0
        ):
            logger.warning(
                f"Overriding temperature={requested_temperature} to 1.0 for reasoning model {provider}/{model}"
            )
        else:
            logger.info(f"Using temperature={temperature} for model {provider}/{model}")

        # Create request
        chat_request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Initialize tracked client for budget enforcement + pre-request logging
        tracked = get_tracked_client(provider)

        if active_mcp_servers:
            engine = await get_mcp_chat_engine()
            response = await tracked.chat_with_mcp(
                model=model,
                messages=messages,
                mcp_engine=engine,
                active_servers=active_mcp_servers,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            await websocket.send_json(
                {
                    "content": response.content,
                    "correlation_id": correlation_id,
                    "done": False,
                    "warnings": response.raw_response.get("mcp_warnings", []),
                    "tool_results": response.raw_response.get("mcp_tool_results", []),
                }
            )
            await websocket.send_json(
                {
                    "content": "",
                    "done": True,
                    "correlation_id": correlation_id,
                    "full_content": response.content,
                    "warnings": response.raw_response.get("mcp_warnings", []),
                    "tool_results": response.raw_response.get("mcp_tool_results", []),
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "cost_usd": response.usage.cost_usd,
                        "latency_ms": round(response.latency_ms or 0, 2),
                    },
                }
            )
            return

        # Track latency
        start_time = time.perf_counter()
        first_token_latency_ms: float | None = None

        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        stream = tracked.chat_completion_stream(chat_request)
        async for chunk in stream:
            full_content += chunk.content
            # Accumulate token usage from chunks if available
            if hasattr(chunk, "usage") and chunk.usage:
                if chunk.usage.prompt_tokens:
                    prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens += chunk.usage.completion_tokens or 0
            await websocket.send_json(
                {
                    "content": chunk.content,
                    "correlation_id": correlation_id,
                    "done": False,
                }
            )

        # Estimate tokens if not available from stream (BUG-001: WebSocket cost tracking)
        if prompt_tokens == 0:
            from stratifyai.utils.token_counter import estimate_tokens

            prompt_text = "\n".join(msg.content for msg in messages)
            prompt_tokens = estimate_tokens(prompt_text, provider, model)
        if completion_tokens == 0:
            completion_tokens = estimate_tokens(full_content, provider, model)
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost and track (BUG-001)
        model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
        cost_input = model_info.get("cost_input", 0.0)
        cost_output = model_info.get("cost_output", 0.0)
        cost_usd = (prompt_tokens / 1_000_000 * cost_input) + (
            completion_tokens / 1_000_000 * cost_output
        )

        cost_tracker.add_entry(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            request_id=correlation_id,
        )

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        tracked_metrics = tracked.get_last_stream_metrics()
        tracked_first_token = tracked_metrics.get("first_token_latency_ms")
        if isinstance(tracked_first_token, int | float):
            first_token_latency_ms = float(tracked_first_token)
        total_latency_value = tracked_metrics.get("total_latency_ms")
        if isinstance(total_latency_value, int | float):
            latency_ms = float(total_latency_value)
        metrics_registry.record_stream_completion(first_token_latency_ms, latency_ms)

        logger.info(
            "WebSocket stream completed: provider=%s model=%s latency=%.0fms first_token=%s",
            provider,
            model,
            latency_ms,
            (
                f"{first_token_latency_ms:.0f}ms"
                if first_token_latency_ms is not None
                else "n/a"
            ),
            extra=build_log_extra(
                provider=provider,
                model=model,
                total_latency_ms=latency_ms,
                first_token_latency_ms=first_token_latency_ms,
            ),
        )

        # Send final message with usage info
        await websocket.send_json(
            {
                "content": "",
                "done": True,
                "correlation_id": correlation_id,
                "full_content": full_content,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost_usd,
                    "first_token_latency_ms": (
                        round(first_token_latency_ms, 2)
                        if first_token_latency_ms is not None
                        else None
                    ),
                    "latency_ms": round(latency_ms, 2),
                },
            }
        )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except ValidationError as e:
        metrics_registry.record_stream_error()
        try:
            safe_error = _sanitize_error_payload(e.errors())
            await websocket.send_json(
                {
                    "error": "validation_error",
                    "detail": safe_error,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
        except Exception:
            pass
    except HTTPException as http_exc:
        metrics_registry.record_stream_error()
        # Catch any remaining HTTPException raised inside the handler
        # (e.g. from _sanitize_file_name) and surface as clean JSON.
        safe_detail = _sanitize_error_payload(http_exc.detail)
        logger.warning(
            "WebSocket HTTPException: %s %s", http_exc.status_code, safe_detail
        )
        if not accepted:
            try:
                await websocket.close(code=1008)
            except Exception:
                pass
            return
        try:
            await websocket.send_json(
                {
                    "error": "request_error",
                    "detail": safe_detail,
                    "status_code": http_exc.status_code,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
        except Exception:
            pass
    except Exception as e:
        metrics_registry.record_stream_error()
        safe_error = sanitize_error(str(e))
        logger.error("WebSocket error: %s", safe_error)
        try:
            await websocket.send_json(
                {
                    "error": safe_error,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
        except Exception:
            pass  # Connection may already be closed
    finally:
        reset_correlation_id(token)
        # BUG-005: Avoid double-close RuntimeError
        try:
            await websocket.close()
        except RuntimeError:
            pass  # Already closed


@app.get("/api/cost")
async def get_cost_summary(_: None = Depends(verify_api_key)):
    """Get cost tracking summary."""
    return cost_tracker.get_summary()


@app.post("/api/cost/reset")
async def reset_cost_tracker(_: None = Depends(verify_api_key)):
    """Reset cost tracker."""
    cost_tracker.reset()
    return {"message": "Cost tracker reset successfully"}


class ProviderModelsInfo(BaseModel):
    """Models info for a single provider."""

    models: list[dict]
    active: bool
    validation_error: str | None = None
    validation_time_ms: int = 0


class AllModelsResponse(BaseModel):
    """Response model for all validated models."""

    providers: dict[str, ProviderModelsInfo]
    summary: dict


class MCPClientInfo(BaseModel):
    """Supported MCP client metadata for the Web UI."""

    id: str
    label: str
    config_path: str | None = None
    supports_apply: bool = True
    exists: bool = False


class MCPStatusResponse(BaseModel):
    """Current MCP configuration state for one client."""

    client: str
    path: str | None = None
    configured: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    count: int = 0


class MCPConfigureRequest(BaseModel):
    """Request model for MCP config preview/apply actions."""

    client: str
    server_ids: list[str] = Field(default_factory=list)
    env_values: dict[str, str] = Field(default_factory=dict)
    arg_values: dict[str, str] = Field(default_factory=dict)
    project_root: str | None = None
    output_path: str | None = None
    apply: bool = False

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value


# Shell metacharacter pattern for custom MCP command validation (Phase 3).
_SHELL_METACHAR_RE = _re_module.compile(r"[;|&`]|\$\(")


class MCPCustomServerRequest(BaseModel):
    """Request model for adding a non-catalog (custom) MCP server."""

    server_id: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    client: str
    enabled: bool = True
    auto_start: bool = True
    overwrite: bool = False
    project_root: str | None = None
    output_path: str | None = None
    apply: bool = False

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        """Validate the target client identifier."""
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value

    @field_validator("server_id")
    @classmethod
    def validate_server_id(cls, value: str) -> str:
        """Validate that server_id is non-empty and has no path separators."""
        if not value or not value.strip():
            raise ValueError("server_id must be non-empty")
        if "/" in value or "\\" in value:
            raise ValueError("server_id must not contain path separators")
        return value.strip()

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        """Validate command is non-empty and free of shell metacharacters."""
        if not value or not value.strip():
            raise ValueError("command must be non-empty")
        stripped = value.strip()
        if _SHELL_METACHAR_RE.search(stripped):
            raise ValueError(
                "command must not contain shell metacharacters "
                "(;, |, &, $(), or backticks)"
            )
        return stripped

    @field_validator("env")
    @classmethod
    def validate_env(cls, value: dict[str, str]) -> dict[str, str]:
        """Reject env var names containing '=' or whitespace."""
        for key in value:
            if "=" in key:
                raise ValueError(f"env var name '{key}' must not contain '='")
            if _re_module.search(r"\s", key):
                raise ValueError(f"env var name '{key}' must not contain whitespace")
        return value


class MCPResetRequest(BaseModel):
    """Request model for MCP config reset/remove actions."""

    client: str
    server_ids: list[str] = Field(default_factory=list)
    project_root: str | None = None
    output_path: str | None = None

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value


class MCPResetResponse(BaseModel):
    """Response model for MCP config reset/remove actions."""

    client: str
    path: str | None = None
    removed_server_ids: list[str] = Field(default_factory=list)
    count: int = 0


class MCPToolInfo(BaseModel):
    """Inline tester metadata for a registered MCP tool."""

    name: str
    category: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    example_payload: dict[str, Any] = Field(default_factory=dict)


class MCPClientServerInfo(BaseModel):
    """Live MCP client engine server state for the Web UI dashboard."""

    server_id: str
    status: str
    error: str | None = None
    enabled: bool = True
    auto_start: bool = True
    tool_count: int = 0
    tools: list[str] = Field(default_factory=list)
    transport: str = "stdio"
    source_client: str | None = None
    latency_ms: float | None = None
    last_checked_at: str | None = None
    last_connected_at: str | None = None


class MCPClientToolInfo(BaseModel):
    """Discovered MCP tool metadata for the CE-5 tool discovery panel."""

    server_id: str
    name: str
    namespace: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    permission: str = "allow"


class MCPClientToolExecutionResponse(BaseModel):
    """Structured response for a direct external MCP tool execution."""

    server_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class MCPClientResourceResponse(BaseModel):
    """Structured response for reading an external MCP resource."""

    server_id: str
    uri: str
    content: str


class MCPClientHealthResponse(BaseModel):
    """Health and diagnostics summary for the MCP client engine."""

    status: str
    checked_at: str | None = None
    summary: dict[str, int] = Field(default_factory=dict)
    servers: list[MCPClientServerInfo] = Field(default_factory=list)


class MCPClientPermissionsResponse(BaseModel):
    """Config-backed MCP permission settings for one client."""

    client: str
    path: str | None = None
    servers: dict[str, Any] = Field(default_factory=dict)


class MCPClientPermissionsUpdateRequest(BaseModel):
    """Update MCP permission settings for one client config file."""

    client: str = "cursor"
    project_root: str | None = None
    output_path: str | None = None
    servers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value


class MCPToolTestRequest(BaseModel):
    """Execute one MCP tool from the inline tester."""

    tool_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


_MCP_TOOL_DEFINITIONS: dict[str, MCPToolInfo] = {
    "chat_completion": MCPToolInfo(
        name="chat_completion",
        category="core",
        description="Send a direct chat completion request to a provider/model.",
        input_schema={
            "type": "object",
            "required": ["provider", "model", "messages"],
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "messages": {"type": "array"},
                "temperature": {"type": "number"},
                "max_tokens": {"type": "integer"},
            },
        },
        example_payload={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Say hello from the tool tester."}
            ],
            "temperature": 0.2,
        },
    ),
    "chat_with_routing": MCPToolInfo(
        name="chat_with_routing",
        category="core",
        description="Route a chat request automatically using the configured strategy.",
        input_schema={
            "type": "object",
            "required": ["messages"],
            "properties": {
                "messages": {"type": "array"},
                "strategy": {"type": "string"},
                "capabilities": {"type": "array"},
                "preferred_providers": {"type": "array"},
                "excluded_providers": {"type": "array"},
                "max_cost_usd": {"type": "number"},
                "max_latency_ms": {"type": "number"},
            },
        },
        example_payload={
            "messages": [
                {
                    "role": "user",
                    "content": "Recommend a cheap model for summarizing markdown.",
                }
            ],
            "strategy": "hybrid",
            "capabilities": [],
        },
    ),
    "list_providers": MCPToolInfo(
        name="list_providers",
        category="core",
        description="List all available providers and whether they are configured.",
        input_schema={"type": "object", "properties": {}, "required": []},
        example_payload={},
    ),
    "list_models": MCPToolInfo(
        name="list_models",
        category="core",
        description="List all catalog models for a provider with costs and capabilities.",
        input_schema={
            "type": "object",
            "required": ["provider"],
            "properties": {"provider": {"type": "string"}},
        },
        example_payload={"provider": "openai"},
    ),
    "get_model_info": MCPToolInfo(
        name="get_model_info",
        category="core",
        description="Return full metadata for a specific provider/model pair.",
        input_schema={
            "type": "object",
            "required": ["provider", "model"],
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
        },
        example_payload={"provider": "openai", "model": "gpt-4o-mini"},
    ),
    "get_cost_summary": MCPToolInfo(
        name="get_cost_summary",
        category="cost",
        description="Summarize MCP session cost totals, optionally filtered by provider/model.",
        input_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": [],
        },
        example_payload={},
    ),
    "validate_provider": MCPToolInfo(
        name="validate_provider",
        category="validation",
        description="Check whether a provider is configured and has catalog models available.",
        input_schema={
            "type": "object",
            "required": ["provider"],
            "properties": {"provider": {"type": "string"}},
        },
        example_payload={"provider": "openai"},
    ),
    "estimate_cost": MCPToolInfo(
        name="estimate_cost",
        category="cost",
        description="Estimate token usage and input cost for a prompt before sending it.",
        input_schema={
            "type": "object",
            "required": ["provider", "model", "message_text"],
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "message_text": {"type": "string"},
            },
        },
        example_payload={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "message_text": "Estimate the cost of this request.",
        },
    ),
}


def _mcp_tool_capabilities(model_data: dict[str, Any]) -> list[str]:
    """Extract the capability list used by the inline tester."""
    capabilities: list[str] = []
    if model_data.get("supports_vision"):
        capabilities.append("vision")
    if model_data.get("supports_tools"):
        capabilities.append("tools")
    if model_data.get("supports_streaming"):
        capabilities.append("streaming")
    if model_data.get("supports_reasoning") or model_data.get("reasoning_model"):
        capabilities.append("reasoning")
    return capabilities


async def _execute_mcp_tool_test(tool_name: str, payload: dict[str, Any]) -> Any:
    """Execute a supported MCP tool for the inline tester."""
    if tool_name not in _MCP_TOOL_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: {tool_name}")

    if tool_name == "list_providers":
        providers = load_catalog().get("providers", {})
        result: list[dict[str, Any]] = []
        for name, models in providers.items():
            env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(name)
            configured = bool(env_key and os.environ.get(env_key)) or name in {
                "ollama",
                "bedrock",
            }
            result.append(
                {
                    "provider": name,
                    "model_count": len(models),
                    "configured": configured,
                }
            )
        return result

    if tool_name == "list_models":
        provider = str(payload.get("provider", ""))
        if provider not in MODEL_CATALOG:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        return [
            {
                "model_id": model_id,
                "context_window": int(model_data.get("context", 0)),
                "cost_input_per_1m": float(model_data.get("cost_input", 0.0)),
                "cost_output_per_1m": float(model_data.get("cost_output", 0.0)),
                "capabilities": _mcp_tool_capabilities(model_data),
            }
            for model_id, model_data in MODEL_CATALOG[provider].items()
        ]

    if tool_name == "get_model_info":
        provider = str(payload.get("provider", ""))
        model = str(payload.get("model", ""))
        if provider not in MODEL_CATALOG:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        if model not in MODEL_CATALOG[provider]:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model '{model}' for provider '{provider}'",
            )
        return {
            "provider": provider,
            "model": model,
            "metadata": dict(MODEL_CATALOG[provider][model]),
        }

    if tool_name == "get_cost_summary":
        summary = cost_tracker.get_summary()
        filter_provider: str | None = payload.get("provider")
        filter_model: str | None = payload.get("model")
        if filter_provider or filter_model:
            summary = {
                **summary,
                "filter_provider": filter_provider,
                "filter_model": filter_model,
            }
        return summary

    if tool_name == "validate_provider":
        provider = str(payload.get("provider", ""))
        if provider not in MODEL_CATALOG:
            return {
                "provider": provider,
                "configured": False,
                "models_available": [],
                "validation_errors": [f"Unknown provider: {provider}"],
            }
        env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider, "UNKNOWN")
        configured = bool(os.environ.get(env_key)) or provider in {"ollama", "bedrock"}
        validation_errors = (
            [] if configured else [f"API key not set (expected env var: {env_key})"]
        )
        return {
            "provider": provider,
            "configured": configured,
            "models_available": list(MODEL_CATALOG.get(provider, {}).keys()),
            "validation_errors": validation_errors,
        }

    if tool_name == "estimate_cost":
        from stratifyai.utils.token_counter import estimate_tokens

        provider = str(payload.get("provider", ""))
        model = str(payload.get("model", ""))
        message_text = str(payload.get("message_text", ""))
        if provider not in MODEL_CATALOG:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        if model not in MODEL_CATALOG[provider]:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model '{model}' for provider '{provider}'",
            )
        tokens = estimate_tokens(message_text)
        estimated_cost = (tokens / 1_000_000) * float(
            MODEL_CATALOG[provider][model].get("cost_input", 0.0)
        )
        return {
            "estimated_input_tokens": tokens,
            "estimated_cost_usd": estimated_cost,
            "provider": provider,
            "model": model,
        }

    if tool_name == "chat_completion":
        provider = str(payload.get("provider", ""))
        model = str(payload.get("model", ""))
        messages = payload.get("messages", [])
        if provider not in MODEL_CATALOG:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(
                status_code=400, detail="messages must be a non-empty list"
            )
        request_messages = []
        for item in messages:
            raw_role = str(item.get("role", "user"))
            if raw_role not in _VALID_MESSAGE_ROLES:
                raise HTTPException(
                    status_code=400, detail=f"Invalid message role: {raw_role!r}"
                )
            request_messages.append(
                Message(role=raw_role, content=str(item.get("content", "")))
            )
        client = get_tracked_client(provider)
        response = await client.chat_completion(
            ChatRequest(
                model=model,
                messages=request_messages,
                temperature=float(payload["temperature"])
                if payload.get("temperature") is not None
                else 0.7,
                max_tokens=int(payload["max_tokens"])
                if payload.get("max_tokens") is not None
                else None,
            )
        )
        return response.to_dict()

    if tool_name == "chat_with_routing":
        messages = payload.get("messages", [])
        if not isinstance(messages, list) or not messages:
            raise HTTPException(
                status_code=400, detail="messages must be a non-empty list"
            )
        router = Router(
            strategy=RoutingStrategy(str(payload.get("strategy", "hybrid"))),
            preferred_providers=payload.get("preferred_providers"),
            excluded_providers=payload.get("excluded_providers"),
        )
        request_messages = []
        for item in messages:
            raw_role = str(item.get("role", "user"))
            if raw_role not in _VALID_MESSAGE_ROLES:
                raise HTTPException(
                    status_code=400, detail=f"Invalid message role: {raw_role!r}"
                )
            request_messages.append(
                Message(role=raw_role, content=str(item.get("content", "")))
            )
        provider, model = router.route(
            request_messages,
            required_capabilities=payload.get("capabilities"),
            max_cost_per_1k_tokens=payload.get("max_cost_usd"),
            max_latency_ms=payload.get("max_latency_ms"),
        )
        client = get_tracked_client(provider)
        response = await client.chat_completion(
            ChatRequest(
                model=model,
                messages=request_messages,
                temperature=0.7,
            )
        )
        return {
            "selected_provider": provider,
            "selected_model": model,
            "routing_strategy": str(payload.get("strategy", "hybrid")),
            "response": response.to_dict(),
        }

    raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' is not executable")


def _normalize_mcp_permission_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize permission settings for API responses and config updates."""
    if not isinstance(payload, dict):
        payload = {}

    return {
        "default_mode": payload.get("default_mode") or payload.get("default"),
        "allow": [
            str(item).strip() for item in payload.get("allow", []) if str(item).strip()
        ],
        "deny": [
            str(item).strip() for item in payload.get("deny", []) if str(item).strip()
        ],
        "confirm": [
            str(item).strip()
            for item in payload.get("confirm", [])
            if str(item).strip()
        ],
    }


def _build_mcp_permission_servers(
    client: str,
    project_root: str | None = None,
    output_path: str | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    """Merge configured MCP servers with StratifyAI-specific permission settings."""
    path, configured = get_configured_servers(
        client=client,
        project_root=project_root,
        output_path=output_path,
    )
    _settings_path, settings = get_mcp_client_settings(
        client=client,
        project_root=project_root,
        output_path=output_path,
    )

    settings_by_server = (
        settings.get("servers", {}) if isinstance(settings, dict) else {}
    )
    if not isinstance(settings_by_server, dict):
        settings_by_server = {}

    merged: dict[str, Any] = {}
    for server_id in sorted(set(configured.keys()) | set(settings_by_server.keys())):
        server_settings = settings_by_server.get(server_id, {})
        if not isinstance(server_settings, dict):
            server_settings = {}
        merged[server_id] = {
            "enabled": bool(server_settings.get("enabled", True)),
            "auto_start": bool(server_settings.get("auto_start", True)),
            "permissions": _normalize_mcp_permission_payload(
                server_settings.get("permissions")
            ),
        }

    return path, merged


def _serialize_mcp_client_servers(engine: MCPClientEngine) -> list[dict[str, Any]]:
    """Serialize live server state for the CE-5 dashboard."""
    tools_by_server: dict[str, list[str]] = {}
    for descriptor in engine.list_tools():
        tools_by_server.setdefault(descriptor.server_id, []).append(
            descriptor.namespace
        )

    server_index = getattr(engine, "_server_index", {})
    serialized: list[dict[str, Any]] = []
    for status in engine.list_servers():
        config = server_index.get(status.server_id)
        tool_names = sorted(tools_by_server.get(status.server_id, []))
        serialized.append(
            MCPClientServerInfo(
                server_id=status.server_id,
                status=status.status,
                error=status.error,
                enabled=bool(getattr(config, "enabled", True)),
                auto_start=bool(getattr(config, "auto_start", True)),
                tool_count=len(tool_names),
                tools=tool_names,
                transport=getattr(status, "transport", "stdio"),
                source_client=getattr(config, "source_client", None),
                latency_ms=getattr(status, "latency_ms", None),
                last_checked_at=_format_timestamp(
                    getattr(status, "last_checked_at", None)
                ),
                last_connected_at=_format_timestamp(
                    getattr(status, "last_connected_at", None)
                ),
            ).model_dump()
        )
    return serialized


def _serialize_mcp_client_tools(engine: MCPClientEngine) -> list[dict[str, Any]]:
    """Serialize discovered external MCP tools with their current permission mode."""
    permission_manager = getattr(engine, "_permission_manager", None)
    serialized: list[dict[str, Any]] = []

    for descriptor in engine.list_tools():
        tool = engine.find_tool(descriptor.server_id, descriptor.tool_name)
        permission = "allow"
        if permission_manager is not None:
            permission = permission_manager.evaluate(
                descriptor.server_id,
                descriptor.tool_name,
                tool,
            ).mode.value

        serialized.append(
            MCPClientToolInfo(
                server_id=descriptor.server_id,
                name=descriptor.tool_name,
                namespace=descriptor.namespace,
                description=descriptor.description,
                input_schema=descriptor.input_schema,
                permission=permission,
            ).model_dump()
        )

    return sorted(serialized, key=lambda item: (item["server_id"], item["namespace"]))


async def _apply_mcp_client_settings_to_engine(
    engine: MCPClientEngine,
    server_settings: dict[str, Any],
) -> None:
    """Update the in-memory MCP engine after permission changes are saved."""
    if not isinstance(server_settings, dict):
        return

    for server_id, settings in server_settings.items():
        if not isinstance(settings, dict):
            continue
        config = getattr(engine, "_server_index", {}).get(server_id)
        if config is None:
            continue

        config.enabled = bool(settings.get("enabled", config.enabled))
        config.auto_start = bool(settings.get("auto_start", config.auto_start))

        policy = ServerPermissionConfig.from_dict(settings.get("permissions"))
        config.permissions = policy
        permission_manager = getattr(engine, "_permission_manager", None)
        if permission_manager is not None:
            permission_manager.set_policy(server_id, policy)

        if not config.enabled and getattr(
            engine._server_manager, "is_running", lambda _: False
        )(server_id):
            await engine.stop_server(server_id)


@app.get("/api/all-models")
async def get_all_validated_models(_: None = Depends(verify_api_key)):
    """
    Get all validated models across all providers with detailed metadata.

    Returns models with: provider, cost (input/output), context window,
    capabilities (vision, reasoning, tools, caching), and active status.

    Results are cached for 5 minutes to avoid live API calls on every request.
    """
    global _all_models_cache, _all_models_cache_ts

    # Return cached result if still valid
    if (
        _all_models_cache is not None
        and (time.time() - _all_models_cache_ts) < _CATALOG_CACHE_TTL
    ):
        return cast(AllModelsResponse, _all_models_cache)

    from stratifyai.api_key_helper import APIKeyHelper
    from stratifyai.utils.provider_validator import validate_provider_models

    providers_list = [
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "groq",
        "grok",
        "ollama",
        "openrouter",
        "bedrock",
    ]

    # Get API key availability
    api_key_status = APIKeyHelper.check_available_providers()

    result = {}
    total_models = 0
    active_providers = 0

    # Run validation for each provider in parallel (BUG-007, BUG-008: use shared executor)
    loop = asyncio.get_running_loop()
    validation_tasks = []
    for provider in providers_list:
        model_ids = list(MODEL_CATALOG.get(provider, {}).keys())
        task = loop.run_in_executor(
            _executor, validate_provider_models, provider, model_ids
        )
        validation_tasks.append((provider, task))

    # Gather results
    for provider, task in validation_tasks:
        validation_result = await task

        # Check if provider is active (has API key configured)
        is_active = api_key_status.get(provider, False)
        if is_active:
            active_providers += 1

        models_list = []
        catalog = MODEL_CATALOG.get(provider, {})

        # Use valid models if available, otherwise use catalog
        model_ids = (
            validation_result["valid_models"]
            if not validation_result["error"]
            else list(catalog.keys())
        )

        for model_id in model_ids:
            model_info = catalog.get(model_id, {})

            models_list.append(
                {
                    "id": model_id,
                    "provider": provider,
                    "context_window": model_info.get("context", 0),
                    "cost_input": model_info.get("cost_input", 0),
                    "cost_output": model_info.get("cost_output", 0),
                    "supports_vision": model_info.get("supports_vision", False),
                    "supports_tools": model_info.get("supports_tools", False),
                    "supports_caching": model_info.get("supports_caching", False),
                    "reasoning_model": model_info.get("reasoning_model", False),
                    "validated": model_id in validation_result["valid_models"],
                }
            )

        result[provider] = ProviderModelsInfo(
            models=models_list,
            active=is_active,
            validation_error=validation_result.get("error"),
            validation_time_ms=validation_result.get("validation_time_ms", 0),
        )
        total_models += len(models_list)

    response = AllModelsResponse(
        providers=result,
        summary={
            "total_models": total_models,
            "total_providers": len(providers_list),
            "active_providers": active_providers,
        },
    )

    # Cache the result
    _all_models_cache = response
    _all_models_cache_ts = time.time()

    return response


@app.get("/api/catalog")
async def get_catalog(_: None = Depends(verify_api_key)):
    """Get the full model catalog with metadata and validation status.

    Returns data in frontend-compatible format:
    { [provider]: { [modelId]: CatalogModel } }

    Only returns models that are API-validated when API key is set.
    Falls back to full catalog when no API key is configured.

    Results are cached for 5 minutes to avoid live API calls on every request.
    """
    global _catalog_cache, _catalog_cache_ts

    # Return cached result if still valid
    if (
        _catalog_cache is not None
        and (time.time() - _catalog_cache_ts) < _CATALOG_CACHE_TTL
    ):
        return _catalog_cache

    from stratifyai.utils.provider_validator import validate_provider_models

    catalog = load_catalog()
    providers = catalog.get("providers", {})

    # Run validation for all providers in parallel (BUG-007, BUG-008: use shared executor)
    loop = asyncio.get_running_loop()
    validation_tasks = []
    for provider in providers.keys():
        model_ids = list(providers[provider].keys())
        task = loop.run_in_executor(
            _executor, validate_provider_models, provider, model_ids
        )
        validation_tasks.append((provider, task))

    # Gather validation results
    validation_results = {}
    for provider, task in validation_tasks:
        validation_result = await task
        validation_results[provider] = validation_result

    # Transform to frontend-expected format (only include validated models)
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for provider, models in providers.items():
        result[provider] = {}
        validation = validation_results.get(provider, {})
        valid_models = set(validation.get("valid_models", []))
        has_error = validation.get("error") is not None

        for model_id, model_data in models.items():
            # Only include model if it's validated OR if validation failed (fallback to catalog)
            if model_id in valid_models or has_error:
                result[provider][model_id] = {
                    "model_id": model_id,
                    "display_name": model_data.get("display_name", model_id),
                    "input_cost_per_1m": model_data.get("cost_input", 0),
                    "output_cost_per_1m": model_data.get("cost_output", 0),
                    "context_window": model_data.get("context", 0),
                    "max_output_tokens": model_data.get(
                        "max_output", model_data.get("context", 0) // 4
                    ),
                    "supports_vision": model_data.get("supports_vision", False),
                    "supports_tools": model_data.get("supports_tools", False),
                    "is_reasoning_model": model_data.get("reasoning_model", False),
                    "category": model_data.get("category", ""),
                    "description": model_data.get("description", ""),
                    "deprecated": model_data.get("deprecated", False),
                    "deprecated_date": model_data.get("deprecated_date"),
                    "replacement_model": model_data.get("replacement_model"),
                    # Only mark as truly validated when validation succeeded (P1: fix false validated status)
                    "validated": (model_id in valid_models) and not has_error,
                }

    # Cache the result
    _catalog_cache = result
    _catalog_cache_ts = time.time()

    return cast(dict[str, Any], result)


@app.get("/api/mcp/catalog")
async def get_mcp_catalog(_: None = Depends(verify_api_key)):
    """Return the curated MCP server catalog for the Web UI."""
    catalog = load_mcp_server_catalog()
    return catalog.model_dump()


@app.get("/api/mcp/tools")
async def get_mcp_tools(_: None = Depends(verify_api_key)):
    """Return inline tester metadata for the registered StratifyAI MCP tools."""
    return {
        "tools": [
            tool.model_dump()
            for tool in sorted(
                _MCP_TOOL_DEFINITIONS.values(),
                key=lambda item: (item.category, item.name),
            )
        ]
    }


@app.post("/api/mcp/test-tool")
async def test_mcp_tool(
    payload: MCPToolTestRequest,
    _: None = Depends(verify_api_key),
):
    """Execute one StratifyAI MCP tool using JSON input from the Web UI tester."""
    try:
        result = await _execute_mcp_tool_test(payload.tool_name, payload.payload)
        return {
            "tool_name": payload.tool_name,
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=sanitize_error(str(exc))) from exc


@app.get("/api/mcp/clients")
async def get_mcp_clients(
    project_root: str | None = None,
    _: None = Depends(verify_api_key),
):
    """Return supported MCP client targets and their resolved config paths."""
    client_labels = {
        "claude-desktop": "Claude Desktop",
        "claude-code": "Claude Code",
        "cursor": "Cursor",
        "vscode": "VS Code (Copilot Chat)",
    }
    clients: list[MCPClientInfo] = []

    for client_id, label in client_labels.items():
        path = detect_client_config_path(client_id, project_root)
        clients.append(
            MCPClientInfo(
                id=client_id,
                label=label,
                config_path=str(path) if path is not None else None,
                supports_apply=client_id != "claude-code",
                exists=path.exists() if path is not None else False,
            )
        )

    return {"clients": [client.model_dump() for client in clients]}


_VALID_MCP_CLIENTS = {"claude-desktop", "claude-code", "cursor", "vscode"}


@app.get("/api/mcp/status", response_model=MCPStatusResponse)
async def get_mcp_status(
    client: str,
    project_root: str | None = None,
    output_path: str | None = None,
    _: None = Depends(verify_api_key),
):
    """Inspect the currently configured MCP servers for a target client."""
    if client not in _VALID_MCP_CLIENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid client '{client}'. Must be one of: {', '.join(sorted(_VALID_MCP_CLIENTS))}",
        )
    try:
        path, configured = get_configured_servers(
            client=client,
            project_root=project_root,
            output_path=output_path,
        )
        _settings_path, merged_settings = _build_mcp_permission_servers(
            client=client,
            project_root=project_root,
            output_path=output_path,
        )
        return MCPStatusResponse(
            client=client,
            path=str(path) if path is not None else None,
            configured=configured,
            settings=merged_settings,
            count=len(configured),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.get("/api/mcp-client/servers")
async def get_mcp_client_servers(
    refresh: bool = False,
    _: None = Depends(verify_api_key),
):
    """Return live MCP client engine status for the server dashboard."""
    try:
        engine = await get_mcp_chat_engine(refresh=refresh)
        return {"servers": _serialize_mcp_client_servers(engine)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=sanitize_error(str(exc))) from exc


@app.get("/api/mcp-client/tools")
async def get_mcp_client_tools(
    refresh: bool = False,
    _: None = Depends(verify_api_key),
):
    """Return discovered external MCP tools for the CE-5 tool browser."""
    try:
        engine = await get_mcp_chat_engine(refresh=refresh)
        return {"tools": _serialize_mcp_client_tools(engine)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=sanitize_error(str(exc))) from exc


@app.post(
    "/api/mcp-client/tools/{server_id}/{tool_name}",
    response_model=MCPClientToolExecutionResponse,
)
async def execute_mcp_client_tool(
    server_id: str,
    tool_name: str,
    tool_args: dict[str, Any] = Body(default_factory=dict),
    _: None = Depends(verify_api_key),
):
    """Execute one tool on an external MCP server using the shared client engine."""
    try:
        engine = await get_mcp_chat_engine()
        result = await engine.call_tool(server_id, tool_name, tool_args)
        return MCPClientToolExecutionResponse(
            server_id=server_id,
            tool_name=tool_name,
            arguments=tool_args,
            result=result,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=sanitize_error(str(exc))) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=sanitize_error(str(exc))) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.delete("/api/mcp-client/tools/{server_id}/{tool_name}")
async def remove_mcp_client_tool(
    server_id: str,
    tool_name: str,
    _: None = Depends(verify_api_key),
):
    """Remove a single tool from a running MCP server.

    The server stays running — only the selected tool is unregistered.
    To restore removed tools, restart the server.
    """
    try:
        engine = await get_mcp_chat_engine()
        removed = engine.remove_tool(server_id, tool_name)
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found on server '{server_id}'",
            )
        return {
            "server_id": server_id,
            "tool_name": tool_name,
            "removed": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.get(
    "/api/mcp-client/resources/{server_id}/{resource_uri:path}",
    response_model=MCPClientResourceResponse,
)
async def get_mcp_client_resource(
    server_id: str,
    resource_uri: str,
    _: None = Depends(verify_api_key),
):
    """Read one external MCP resource through the shared client engine."""
    try:
        engine = await get_mcp_chat_engine()
        content = await engine.get_resource(server_id, resource_uri)
        return MCPClientResourceResponse(
            server_id=server_id,
            uri=resource_uri,
            content=content,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=sanitize_error(str(exc))) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=sanitize_error(str(exc))) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.get("/api/mcp-client/health", response_model=MCPClientHealthResponse)
async def get_mcp_client_health(_: None = Depends(verify_api_key)):
    """Return a live MCP client engine health and diagnostics summary."""
    try:
        engine = await get_mcp_chat_engine()
        snapshot = await engine.get_health_snapshot()
        return MCPClientHealthResponse(**snapshot)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=sanitize_error(str(exc))) from exc


def _mcp_runtime_error_status(exc: Exception) -> int:
    """Map MCP start/restart failures to a more useful HTTP status code."""
    if isinstance(exc, KeyError):
        return 404
    if isinstance(exc, PermissionError):
        return 403
    if isinstance(exc, FileNotFoundError | OSError):
        return 503

    message = str(exc).lower()
    if "cannot find the file specified" in message or "not found" in message:
        return 503
    return 400


@app.post("/api/mcp-client/servers/{server_id}/start")
async def start_mcp_client_server(
    server_id: str,
    _: None = Depends(verify_api_key),
):
    """Start one configured MCP client engine server."""
    try:
        engine = await get_mcp_chat_engine()
        status = await engine.start_server(server_id)
        return {
            "server_id": status.server_id,
            "status": status.status,
            "error": status.error,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=_mcp_runtime_error_status(exc),
            detail=sanitize_error(str(exc)),
        ) from exc


@app.post("/api/mcp-client/servers/{server_id}/stop")
async def stop_mcp_client_server(
    server_id: str,
    _: None = Depends(verify_api_key),
):
    """Stop one running MCP client engine server."""
    try:
        engine = await get_mcp_chat_engine()
        status = await engine.stop_server(server_id)
        return {
            "server_id": status.server_id,
            "status": status.status,
            "error": status.error,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.post("/api/mcp-client/servers/{server_id}/restart")
async def restart_mcp_client_server(
    server_id: str,
    _: None = Depends(verify_api_key),
):
    """Restart one configured MCP client engine server."""
    try:
        engine = await get_mcp_chat_engine()
        status = await engine.restart_server(server_id)
        return {
            "server_id": status.server_id,
            "status": status.status,
            "error": status.error,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=_mcp_runtime_error_status(exc),
            detail=sanitize_error(str(exc)),
        ) from exc


@app.get("/api/mcp-client/permissions", response_model=MCPClientPermissionsResponse)
async def get_mcp_client_permissions(
    client: str = "cursor",
    project_root: str | None = None,
    output_path: str | None = None,
    _: None = Depends(verify_api_key),
):
    """Return config-backed MCP permission settings for the permission manager."""
    if client not in _VALID_MCP_CLIENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid client '{client}'. Must be one of: {', '.join(sorted(_VALID_MCP_CLIENTS))}",
        )
    try:
        path, servers = _build_mcp_permission_servers(
            client=client,
            project_root=project_root,
            output_path=output_path,
        )
        return MCPClientPermissionsResponse(
            client=client,
            path=str(path) if path is not None else None,
            servers=servers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.put("/api/mcp-client/permissions", response_model=MCPClientPermissionsResponse)
async def update_mcp_client_permissions(
    payload: MCPClientPermissionsUpdateRequest,
    _: None = Depends(verify_api_key),
):
    """Persist MCP permission settings from the CE-5 permission manager."""
    try:
        write_mcp_client_settings(
            client=payload.client,
            settings={"servers": payload.servers},
            project_root=payload.project_root,
            output_path=payload.output_path,
        )

        global _mcp_chat_engine
        if _mcp_chat_engine is not None:
            await _apply_mcp_client_settings_to_engine(
                _mcp_chat_engine, payload.servers
            )

        path, servers = _build_mcp_permission_servers(
            client=payload.client,
            project_root=payload.project_root,
            output_path=payload.output_path,
        )
        return MCPClientPermissionsResponse(
            client=payload.client,
            path=str(path) if path is not None else None,
            servers=servers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.post("/api/mcp/configure")
async def configure_mcp(
    payload: MCPConfigureRequest,
    _: None = Depends(verify_api_key),
):
    """Preview or apply MCP client configuration for selected servers."""
    if not payload.server_ids:
        raise HTTPException(
            status_code=400, detail="At least one server_id is required"
        )

    try:
        warnings = validate_prerequisites(payload.server_ids)

        if payload.client == "claude-code":
            commands = build_claude_code_commands(
                payload.server_ids,
                payload.env_values,
                payload.arg_values,
                project_root=payload.project_root,
            )
            target_path = payload.output_path
            applied = False
            if payload.apply:
                if not payload.output_path:
                    warnings.append(
                        "claude-code: apply requested but no output_path provided. "
                        "Use 'claude mcp add' commands directly instead."
                    )
                else:
                    output_path = Path(payload.output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
                    applied = True
            return {
                "applied": applied,
                "config": None,
                "commands": commands,
                "path": target_path,
                "warnings": warnings,
            }

        config = build_client_config(
            client=payload.client,
            server_ids=payload.server_ids,
            env_values=payload.env_values,
            arg_values=payload.arg_values,
            project_root=payload.project_root,
        )

        path = detect_client_config_path(payload.client, payload.project_root)
        applied = False
        if payload.apply:
            written = write_client_config(
                client=payload.client,
                config=config,
                project_root=payload.project_root,
                output_path=payload.output_path,
            )
            path = written
            applied = True

            global _mcp_chat_engine
            if _mcp_chat_engine is not None and payload.client != "claude-code":
                await get_mcp_chat_engine(refresh=True)

        return {
            "applied": applied,
            "config": config,
            "commands": [],
            "path": str(path) if path is not None else payload.output_path,
            "warnings": warnings,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=sanitize_error(str(exc))) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.post("/api/mcp/add-custom")
async def add_custom_mcp_server(
    payload: MCPCustomServerRequest,
    _: None = Depends(verify_api_key),
):
    """Add a non-catalog (custom) MCP server to a client config file."""
    try:
        warnings: list[str] = []

        # --- Phase 3.1: Warn if command is not found on the host ---------------
        if not shutil.which(payload.command):
            warnings.append(
                f"Command '{payload.command}' was not found on the host PATH. "
                "The server may fail to start if the path is incorrect."
            )

        # --- Phase 3.3: Warn on empty env var values --------------------------
        for env_key, env_val in payload.env.items():
            if env_val == "":
                warnings.append(f"Environment variable '{env_key}' has an empty value.")

        # --- Phase 3.2: Server ID conflict detection --------------------------
        if payload.client != "claude-code":
            _, existing_servers = get_configured_servers(
                client=payload.client,
                project_root=payload.project_root,
                output_path=payload.output_path,
            )
            if payload.server_id in existing_servers and not payload.overwrite:
                warnings.append(
                    f"Server '{payload.server_id}' already exists in the "
                    f"{payload.client} config. Set overwrite=true to replace it."
                )
                # Build a preview config so the caller can inspect it.
                server_config_preview: dict[str, Any] = {
                    "command": payload.command,
                }
                if payload.args:
                    server_config_preview["args"] = payload.args
                if payload.env:
                    server_config_preview["env"] = dict.fromkeys(payload.env, "***")
                if payload.client == "vscode":
                    preview_cfg = {
                        "mcp": {"servers": {payload.server_id: server_config_preview}}
                    }
                else:
                    preview_cfg = {
                        "mcpServers": {payload.server_id: server_config_preview}
                    }
                path = detect_client_config_path(payload.client, payload.project_root)
                return {
                    "applied": False,
                    "config": preview_cfg,
                    "commands": [],
                    "path": str(path) if path is not None else payload.output_path,
                    "warnings": warnings,
                }
        else:
            warnings.append(
                "claude-code: duplicate server_id check skipped "
                "(no local config file to inspect)."
            )

        server_config: dict[str, Any] = {"command": payload.command}
        if payload.args:
            server_config["args"] = payload.args
        if payload.env:
            server_config["env"] = payload.env

        if payload.client == "claude-code":
            cmd_parts = ["claude", "mcp", "add", payload.server_id, payload.command]
            for arg in payload.args:
                cmd_parts.append(arg)
            for key, value in payload.env.items():
                cmd_parts.extend(["-e", f"{key}={value}"])
            commands = [" ".join(shlex.quote(p) for p in cmd_parts)]
            applied = False
            if payload.apply:
                if not payload.output_path:
                    warnings.append(
                        "claude-code: apply requested but no output_path provided. "
                        "Use 'claude mcp add' commands directly instead."
                    )
                else:
                    output_path = Path(payload.output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
                    applied = True
            return {
                "applied": applied,
                "config": None,
                "commands": commands,
                "path": payload.output_path,
                "warnings": warnings,
            }

        # Build the config dict in the format write_client_config expects.
        config: dict[str, Any]
        if payload.client == "vscode":
            config = {"mcp": {"servers": {payload.server_id: server_config}}}
        else:
            config = {"mcpServers": {payload.server_id: server_config}}

        # --- Phase 3.3: Mask env values in preview responses ------------------
        if not payload.apply and payload.env:
            preview_config = _mask_env_in_config(config, payload.client)
        else:
            preview_config = config

        path = detect_client_config_path(payload.client, payload.project_root)
        applied = False

        if payload.apply:
            written = write_client_config(
                client=payload.client,
                config=config,
                project_root=payload.project_root,
                output_path=payload.output_path,
            )
            path = written
            applied = True

            # --- Phase 3.4: Write permission defaults for custom servers ------
            write_mcp_client_settings(
                client=payload.client,
                settings={
                    "servers": {
                        payload.server_id: {
                            "enabled": payload.enabled,
                            "auto_start": payload.auto_start,
                            "permissions": {
                                "default_mode": "confirm",
                                "allow": [],
                                "deny": [],
                                "confirm": [],
                            },
                        }
                    }
                },
                project_root=payload.project_root,
                output_path=payload.output_path,
            )

            global _mcp_chat_engine
            if _mcp_chat_engine is not None:
                await get_mcp_chat_engine(refresh=True)

        return {
            "applied": applied,
            "config": preview_config,
            "commands": [],
            "path": str(path) if path is not None else payload.output_path,
            "warnings": warnings,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


class MCPCustomServerUpdateRequest(BaseModel):
    """Request model for editing an existing custom MCP server."""

    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    client: str
    enabled: bool | None = None
    auto_start: bool | None = None
    project_root: str | None = None
    output_path: str | None = None

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        """Validate the target client identifier."""
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str | None) -> str | None:
        """Validate command is free of shell metacharacters when provided."""
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must be non-empty when provided")
        if _SHELL_METACHAR_RE.search(stripped):
            raise ValueError(
                "command must not contain shell metacharacters "
                "(;, |, &, $(), or backticks)"
            )
        return stripped

    @field_validator("env")
    @classmethod
    def validate_env(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        """Reject env var names containing '=' or whitespace."""
        if value is None:
            return value
        for key in value:
            if "=" in key:
                raise ValueError(f"env var name '{key}' must not contain '='")
            if _re_module.search(r"\s", key):
                raise ValueError(f"env var name '{key}' must not contain whitespace")
        return value


def _mask_env_in_config(config: dict[str, Any], client: str) -> dict[str, Any]:
    """Return a deep copy of the config with env values replaced by '***'."""
    import copy

    masked = copy.deepcopy(config)
    if client == "vscode":
        servers = masked.get("mcp", {}).get("servers", {})
    else:
        servers = masked.get("mcpServers", {})
    for server_cfg in servers.values():
        env = server_cfg.get("env")
        if isinstance(env, dict):
            for key in env:
                env[key] = "***"
    return masked


@app.put("/api/mcp/custom/{server_id}")
async def update_custom_mcp_server(
    server_id: str,
    payload: MCPCustomServerUpdateRequest,
    _: None = Depends(verify_api_key),
):
    """Edit an existing custom MCP server in a client config file."""
    try:
        if payload.client == "claude-code":
            raise ValueError(
                "Claude Code servers cannot be edited via config file. "
                "Use `claude mcp remove` then `claude mcp add` instead."
            )

        _, existing_servers = get_configured_servers(
            client=payload.client,
            project_root=payload.project_root,
            output_path=payload.output_path,
        )

        if server_id not in existing_servers:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_id}' not found in {payload.client} config.",
            )

        current = existing_servers[server_id]
        if not isinstance(current, dict):
            current = {}

        # Merge only the fields that were explicitly provided.
        import copy

        updated: dict[str, Any] = copy.deepcopy(current)
        if payload.command is not None:
            updated["command"] = payload.command
        if payload.args is not None:
            updated["args"] = payload.args
        if payload.env is not None:
            updated["env"] = payload.env

        # Build the config dict in the client-expected format.
        config: dict[str, Any]
        if payload.client == "vscode":
            config = {"mcp": {"servers": {server_id: updated}}}
        else:
            config = {"mcpServers": {server_id: updated}}

        written = write_client_config(
            client=payload.client,
            config=config,
            project_root=payload.project_root,
            output_path=payload.output_path,
        )

        # Update permission metadata if enabled/auto_start changed.
        settings_updates: dict[str, Any] = {}
        if payload.enabled is not None:
            settings_updates["enabled"] = payload.enabled
        if payload.auto_start is not None:
            settings_updates["auto_start"] = payload.auto_start
        if settings_updates:
            write_mcp_client_settings(
                client=payload.client,
                settings={"servers": {server_id: settings_updates}},
                project_root=payload.project_root,
                output_path=payload.output_path,
            )

        global _mcp_chat_engine
        if _mcp_chat_engine is not None:
            await get_mcp_chat_engine(refresh=True)

        return {
            "server_id": server_id,
            "config": updated,
            "path": str(written),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.delete("/api/mcp/custom/{server_id}")
async def delete_custom_mcp_server(
    server_id: str,
    client: str,
    project_root: str | None = None,
    output_path: str | None = None,
    _: None = Depends(verify_api_key),
):
    """Remove a custom MCP server from a client config file."""
    try:
        # Validate client value.
        allowed_clients = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if client not in allowed_clients:
            raise ValueError(
                f"client must be one of: {', '.join(sorted(allowed_clients))}"
            )

        if client == "claude-code":
            raise ValueError(
                "Claude Code servers cannot be removed via config file. "
                "Use `claude mcp remove <server-id>` instead."
            )

        path, removed = remove_server_from_config(
            client=client,
            server_id=server_id,
            project_root=project_root,
            output_path=output_path,
        )

        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_id}' not found in {client} config.",
            )

        global _mcp_chat_engine
        if _mcp_chat_engine is not None:
            await get_mcp_chat_engine(refresh=True)

        return {
            "server_id": server_id,
            "removed": True,
            "path": str(path),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


class MCPCustomExportEntry(BaseModel):
    """A single custom server entry for import/export."""

    server_id: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class MCPCustomImportRequest(BaseModel):
    """Request model for bulk importing custom MCP servers."""

    client: str
    servers: list[MCPCustomExportEntry]
    overwrite: bool = False
    project_root: str | None = None
    output_path: str | None = None

    @field_validator("client")
    @classmethod
    def validate_client(cls, value: str) -> str:
        """Validate the target client identifier."""
        allowed = {"claude-desktop", "claude-code", "cursor", "vscode"}
        if value not in allowed:
            raise ValueError(f"client must be one of: {', '.join(sorted(allowed))}")
        return value


class MCPCustomImportResponse(BaseModel):
    """Response model for bulk import results."""

    added: int = 0
    skipped: int = 0
    errors: int = 0
    details: list[dict[str, str]] = Field(default_factory=list)
    path: str | None = None


@app.get("/api/mcp/custom/export")
async def export_custom_mcp_servers(
    client: str,
    project_root: str | None = None,
    output_path: str | None = None,
    _: None = Depends(verify_api_key),
):
    """Export all non-catalog (custom) MCP servers as a JSON array."""
    allowed_clients = {"claude-desktop", "claude-code", "cursor", "vscode"}
    if client not in allowed_clients:
        raise HTTPException(
            status_code=400,
            detail=f"client must be one of: {', '.join(sorted(allowed_clients))}",
        )

    if client == "claude-code":
        raise HTTPException(
            status_code=400,
            detail="Claude Code does not use a local config file. Export is not supported.",
        )

    _, configured = get_configured_servers(
        client=client,
        project_root=project_root,
        output_path=output_path,
    )

    catalog = load_mcp_server_catalog()
    catalog_ids = {s.id for s in catalog.servers}

    custom_servers: list[dict[str, Any]] = []
    for server_id, config in sorted(configured.items()):
        if server_id in catalog_ids:
            continue
        if not isinstance(config, dict):
            continue
        custom_servers.append(
            {
                "server_id": server_id,
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "env": config.get("env", {}),
            }
        )

    return {"client": client, "servers": custom_servers, "count": len(custom_servers)}


@app.post("/api/mcp/custom/import", response_model=MCPCustomImportResponse)
async def import_custom_mcp_servers(
    payload: MCPCustomImportRequest,
    _: None = Depends(verify_api_key),
):
    """Bulk import custom MCP server definitions into a client config."""
    if payload.client == "claude-code":
        raise HTTPException(
            status_code=400,
            detail="Claude Code does not use a local config file. Import is not supported.",
        )

    _, existing_servers = get_configured_servers(
        client=payload.client,
        project_root=payload.project_root,
        output_path=payload.output_path,
    )

    added = 0
    skipped = 0
    errors = 0
    details: list[dict[str, str]] = []
    path: Path | None = None

    for entry in payload.servers:
        sid = entry.server_id.strip()
        if not sid:
            errors += 1
            details.append(
                {"server_id": sid, "status": "error", "reason": "empty server_id"}
            )
            continue

        if "/" in sid or "\\" in sid:
            errors += 1
            details.append(
                {
                    "server_id": sid,
                    "status": "error",
                    "reason": "server_id contains path separators",
                }
            )
            continue

        cmd = entry.command.strip()
        if not cmd:
            errors += 1
            details.append(
                {"server_id": sid, "status": "error", "reason": "empty command"}
            )
            continue

        if _SHELL_METACHAR_RE.search(cmd):
            errors += 1
            details.append(
                {
                    "server_id": sid,
                    "status": "error",
                    "reason": "command contains shell metacharacters",
                }
            )
            continue

        if sid in existing_servers and not payload.overwrite:
            skipped += 1
            details.append(
                {"server_id": sid, "status": "skipped", "reason": "already exists"}
            )
            continue

        server_config: dict[str, Any] = {"command": cmd}
        if entry.args:
            server_config["args"] = entry.args
        if entry.env:
            server_config["env"] = entry.env

        config: dict[str, Any]
        if payload.client == "vscode":
            config = {"mcp": {"servers": {sid: server_config}}}
        else:
            config = {"mcpServers": {sid: server_config}}

        # Each server is written individually; if a later write fails the
        # earlier ones remain (intentional partial-success — no rollback).
        try:
            path = write_client_config(
                client=payload.client,
                config=config,
                project_root=payload.project_root,
                output_path=payload.output_path,
            )
            write_mcp_client_settings(
                client=payload.client,
                settings={
                    "servers": {
                        sid: {
                            "enabled": True,
                            "auto_start": True,
                            "permissions": {
                                "default_mode": "confirm",
                                "allow": [],
                                "deny": [],
                                "confirm": [],
                            },
                        }
                    }
                },
                project_root=payload.project_root,
                output_path=payload.output_path,
            )
            existing_servers[sid] = server_config
            added += 1
            details.append({"server_id": sid, "status": "added"})
        except Exception as exc:
            errors += 1
            details.append(
                {
                    "server_id": sid,
                    "status": "error",
                    "reason": sanitize_error(str(exc)),
                }
            )

    if added > 0:
        global _mcp_chat_engine
        if _mcp_chat_engine is not None:
            await get_mcp_chat_engine(refresh=True)

    return MCPCustomImportResponse(
        added=added,
        skipped=skipped,
        errors=errors,
        details=details,
        path=str(path) if path is not None else None,
    )


@app.post("/api/mcp/reset", response_model=MCPResetResponse)
async def reset_mcp_config(
    payload: MCPResetRequest,
    _: None = Depends(verify_api_key),
):
    """Remove selected or all configured MCP servers from a client config file."""
    try:
        path, configured = get_configured_servers(
            client=payload.client,
            project_root=payload.project_root,
            output_path=payload.output_path,
        )
        target_ids = payload.server_ids or list(configured.keys())

        if payload.client == "claude-code":
            raise ValueError(
                "Claude Code uses `claude mcp remove <server-id>` commands instead of a local config file."
            )

        written_path, removed_server_ids = remove_servers_from_config(
            client=payload.client,
            server_ids=target_ids,
            project_root=payload.project_root,
            output_path=payload.output_path,
        )

        global _mcp_chat_engine
        if _mcp_chat_engine is not None and payload.client != "claude-code":
            await get_mcp_chat_engine(refresh=True)

        return MCPResetResponse(
            client=payload.client,
            path=str(written_path if written_path is not None else path)
            if (written_path is not None or path is not None)
            else None,
            removed_server_ids=removed_server_ids,
            count=len(removed_server_ids),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_error(str(exc))) from exc


@app.get("/api/templates")
async def list_templates(
    tag: str | None = None,
    source: str | None = None,
    _: None = Depends(verify_api_key),
):
    """List all available prompt templates.

    Args:
        tag: Filter templates by tag (e.g., "code", "writing")
        source: Filter by source ("builtin" or "user")

    Returns:
        List of template metadata
    """
    from stratifyai.prompts import registry

    templates = registry.list(tag=tag, source=source)
    return [t.to_dict() for t in templates]


@app.get("/api/templates/{name}")
async def get_template(
    name: str,
    _: None = Depends(verify_api_key),
):
    """Get a specific template by name.

    Args:
        name: Template name

    Returns:
        Template metadata

    Raises:
        HTTPException: 404 if template not found
    """
    from stratifyai.prompts import registry

    try:
        template = registry.get(name)
        return template.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=sanitize_error(str(e))) from e


class TemplateRenderRequest(BaseModel):
    """Request model for template rendering."""

    params: dict[str, Any]


@app.post("/api/templates/{name}/render")
async def render_template(
    name: str,
    request: TemplateRenderRequest,
    _: None = Depends(verify_api_key),
):
    """Render a template with parameters.

    Args:
        name: Template name
        request: Template parameters

    Returns:
        List of rendered messages

    Raises:
        HTTPException: 404 if template not found, 422 for invalid parameters
    """
    from stratifyai.prompts import registry

    try:
        template = registry.get(name)
        messages = template.render(**request.params)
        return [{"role": m.role, "content": m.content} for m in messages]
    except KeyError as e:
        raise HTTPException(status_code=404, detail=sanitize_error(str(e))) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=sanitize_error(str(e))) from e


@app.get("/api/health")
async def health_check():
    """Minimal unauthenticated health check endpoint."""
    return {"status": "healthy"}


def _provider_health_snapshot() -> dict[str, Any]:
    """Collect lightweight provider health information."""
    providers = [
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "groq",
        "grok",
        "ollama",
        "openrouter",
        "bedrock",
    ]
    availability = APIKeyHelper.check_available_providers()

    results: dict[str, Any] = {}
    ready_count = 0
    degraded_count = 0
    for provider in providers:
        configured = availability.get(provider, False)
        if provider not in {"ollama", "bedrock"} and not configured:
            results[provider] = {
                "status": "missing_credentials",
                "configured": False,
                "client_initialized": False,
                "models_known": len(MODEL_CATALOG.get(provider, {})),
                "error": "API key not configured",
            }
            degraded_count += 1
            continue

        try:
            client = LLMClient(provider=provider)
            client.close()
            results[provider] = {
                "status": "ready",
                "configured": configured,
                "client_initialized": True,
                "models_known": len(MODEL_CATALOG.get(provider, {})),
                "error": None,
            }
            ready_count += 1
        except AuthenticationError:
            results[provider] = {
                "status": "missing_credentials",
                "configured": configured,
                "client_initialized": False,
                "models_known": len(MODEL_CATALOG.get(provider, {})),
                "error": "authentication error",
            }
            degraded_count += 1
        except Exception as exc:
            logger.warning(
                "Provider health initialization error for provider=%s: %s",
                provider,
                str(exc),
                extra=build_log_extra(provider=provider, event="provider_health_error"),
            )
            results[provider] = {
                "status": "degraded",
                "configured": configured,
                "client_initialized": False,
                "models_known": len(MODEL_CATALOG.get(provider, {})),
                "error": "initialization error",
            }
            degraded_count += 1

    overall_status = "healthy" if degraded_count == 0 else "degraded"
    return {
        "status": overall_status,
        "providers": results,
        "summary": {
            "total": len(providers),
            "ready": ready_count,
            "degraded": degraded_count,
        },
    }


@app.get("/health/providers")
@app.get("/api/health/providers")
async def provider_health_check(_: None = Depends(verify_api_key)):
    """Return lightweight provider health information."""
    return await asyncio.to_thread(_provider_health_snapshot)


@app.get("/api/metrics")
async def get_metrics(_: None = Depends(verify_api_key)):
    """Export structured application metrics."""
    return {
        "uptime_seconds": int(time.time() - APP_START_TIME),
        **metrics_registry.export(
            api_version=API_VERSION,
            cache_stats=get_cache_stats(),
            cost_summary=cost_tracker.get_summary(),
        ),
    }


def _register_v1_api_aliases() -> None:
    """Register `/v1/*` aliases for all REST endpoints currently under `/api/*`."""
    existing_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    for route in list(app.routes):
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue

        v1_path = "/v1" + route.path[4:]
        if v1_path in existing_paths:
            continue

        app.add_api_route(
            v1_path,
            route.endpoint,
            methods=list(route.methods or {"GET"}),
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            name=f"v1_{route.name}" if route.name else None,
            include_in_schema=route.include_in_schema,
        )
        existing_paths.add(v1_path)


_register_v1_api_aliases()


if __name__ == "__main__":
    import uvicorn

    # BUG-014: Port configurable via env var, default to 8080 (matches docs)
    port = int(os.getenv("STRATIFYAI_PORT", "8080"))
    # Increase body size limit to 100MB for large file uploads
    uvicorn.run(
        app, host="0.0.0.0", port=port, limit_concurrency=1000, timeout_keep_alive=5
    )
