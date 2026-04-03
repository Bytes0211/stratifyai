"""FastAPI application for StratifyAI."""

import asyncio
import hashlib
import hmac
import logging
import os
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import tomllib
from dotenv import load_dotenv
from fastapi import (
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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from stratifyai import ChatRequest, LLMClient, Message
from stratifyai.api_key_helper import APIKeyHelper
from stratifyai.caching import get_cache_stats
from stratifyai.catalog_manager import load_catalog
from stratifyai.config import MODEL_CATALOG
from stratifyai.cost_tracker import CostTracker
from stratifyai.exceptions import AuthenticationError
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
    return "0.1.0"


API_VERSION = _get_version()
APP_START_TIME = time.time()

# Shared ThreadPoolExecutor for async validation tasks (BUG-008)
_executor = ThreadPoolExecutor(max_workers=4)

# Client cache for connection pooling (BUG-003)
_client_cache: dict[str, LLMClient] = {}


def get_client(provider: str) -> LLMClient:
    """Get or create a cached LLMClient for connection pooling."""
    if provider not in _client_cache:
        _client_cache[provider] = LLMClient(provider=provider)
    return _client_cache[provider]


def get_tracked_client(provider: str) -> TrackedLLMClient:
    """Get a TrackedLLMClient wrapping the cached LLMClient."""
    return TrackedLLMClient(client=get_client(provider), cost_tracker=cost_tracker)


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

# WebSocket rate limiting with TTL eviction.
# Each key is a client IP mapping to a deque of request timestamps.
# _WS_RATE_LIMIT_MAX_IPS caps the total number of tracked IPs so that
# a long-running server doesn't leak memory from unique visitors.
_ws_rate_limit: dict[str, deque] = defaultdict(deque)
_WS_RATE_LIMIT_MAX_IPS = 10_000
_WS_RATE_LIMIT_WINDOW_SECS = 60


def _evict_stale_ws_entries() -> None:
    """Remove expired sliding-window entries and prune idle IPs.

    Called once per WebSocket connection before the per-IP check so that
    the dict never grows unboundedly.
    """
    now = time.time()
    stale_ips: list[str] = []
    for ip, window in _ws_rate_limit.items():
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


@app.get("/")
async def root():
    """Serve the frontend interface (SPA or legacy)."""
    index_path = _get_spa_index()
    if index_path:
        return FileResponse(index_path)
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
        return FileResponse(index_path)
    # Legacy: serve models.html
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    models_path = os.path.join(static_dir, "models.html")
    if os.path.exists(models_path):
        return FileResponse(models_path)
    return {"error": "Models page not found"}


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

                    # Perform chunking and summarization
                    # Use a cheap model for summarization (gpt-4o-mini or similar)
                    # Auto-select based on provider
                    summarization_models = {
                        "openai": "gpt-4o-mini",
                        "anthropic": "claude-3-haiku-20240307",
                        "google": "gemini-2.5-flash",
                        "deepseek": "deepseek-chat",
                        "groq": "llama-3.1-8b-instant",
                        "grok": "grok-4-1-fast-non-reasoning",  # BUG-006: Updated from deprecated grok-beta
                        "openrouter": "google/gemini-2.5-flash",
                        "ollama": "llama3.2",
                        "bedrock": "anthropic.claude-3-5-haiku-20241022-v1:0",
                    }
                    summarization_model = summarization_models.get(
                        payload.provider, "gpt-4o-mini"
                    )

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
        from stratifyai.utils.token_counter import (
            count_tokens_for_messages,
            get_context_window,
        )

        estimated_tokens = count_tokens_for_messages(
            messages, payload.provider, payload.model
        )

        # Get context window and API limits
        context_window = get_context_window(payload.provider, payload.model)
        model_info = MODEL_CATALOG.get(payload.provider, {}).get(payload.model, {})
        api_max_input = model_info.get("api_max_input")
        effective_limit = (
            api_max_input
            if api_max_input and api_max_input < context_window
            else context_window
        )

        # Check if exceeds absolute maximum (1M tokens)
        MAX_SYSTEM_LIMIT = 1_000_000
        if estimated_tokens > MAX_SYSTEM_LIMIT:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "content_too_large",
                    "message": f"File is too large to process. The content has approximately {estimated_tokens:,} tokens, which exceeds the system's maximum limit of {MAX_SYSTEM_LIMIT:,} tokens.",
                    "estimated_tokens": estimated_tokens,
                    "system_limit": MAX_SYSTEM_LIMIT,
                    "provider": payload.provider,
                    "model": payload.model,
                    "suggestion": "Please split your file into smaller chunks or use a different processing approach.",
                },
            )

        # Check if exceeds model's effective limit
        if estimated_tokens > effective_limit:
            # Determine if chunking could help
            if api_max_input and context_window > api_max_input:
                # Model has larger context but API restricts input
                # Suggest chunking to reduce tokens OR switching to unrestricted model
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "input_too_long",
                        "message": f"Input is too long for {request.model}. The content has approximately {estimated_tokens:,} tokens, but the API restricts input to {api_max_input:,} tokens (despite the model's {context_window:,} token context window).",
                        "estimated_tokens": estimated_tokens,
                        "api_limit": api_max_input,
                        "context_window": context_window,
                        "provider": payload.provider,
                        "model": payload.model,
                        "suggestion": "✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, gemini-2.5-flash\n✓ Switch to OpenRouter with google/gemini-2.5-pro or google/gemini-2.5-flash",
                        "chunking_enabled": payload.chunked,
                    },
                )
            else:
                # Model simply can't handle this much input
                # Suggest switching to larger context model
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "input_too_long",
                        "message": f"Input is too long for {request.model}. The content has approximately {estimated_tokens:,} tokens, which exceeds the model's maximum of {effective_limit:,} tokens.",
                        "estimated_tokens": estimated_tokens,
                        "model_limit": effective_limit,
                        "provider": request.provider,
                        "model": request.model,
                        "suggestion": "✓ Switch to a model with larger context window:\n  - Google Gemini 2.5 Pro (1M tokens, no API limits)\n  - Google Gemini 2.5 Flash (1M tokens, cheaper)\n  - Claude Opus 4.5 (1M context, 200k API limit)\n✓ Enable 'Smart Chunking' to reduce token usage",
                        "chunking_enabled": request.chunked,
                    },
                )

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
        response = await tracked.chat_completion(chat_request)

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
    await websocket.accept()

    try:
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

        # --- Authentication (WebSocket-safe) --------------------------------
        auth_header = websocket.headers.get("authorization")
        try:
            verify_api_key(auth_header)
        except HTTPException as auth_exc:
            await websocket.send_json(
                {
                    "error": "authentication_failed",
                    "detail": auth_exc.detail,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return

        # --- Rate limiting with TTL eviction --------------------------------
        _evict_stale_ws_entries()
        auth_header = websocket.headers.get("authorization")
        auth_token = _extract_bearer_token(auth_header)
        client_ip = websocket.client.host if websocket.client else "unknown"
        ws_key = f"key:{_hash_token(auth_token)}" if auth_token else f"ip:{client_ip}"
        now = time.time()
        window = _ws_rate_limit[ws_key]
        # Per-IP window cleanup (fast path — global eviction already ran)
        while window and now - window[0] > _WS_RATE_LIMIT_WINDOW_SECS:
            window.popleft()
        if len(window) >= 30:
            await websocket.send_json(
                {
                    "error": "rate_limit_exceeded",
                    "retry_after": _WS_RATE_LIMIT_WINDOW_SECS,
                    "correlation_id": correlation_id,
                    "done": True,
                }
            )
            return
        window.append(now)

        # --- Pydantic validation --------------------------------------------
        request_obj = ChatCompletionRequest.model_validate_json(data)

        provider = request_obj.provider
        model = request_obj.model
        messages_data = request_obj.messages
        requested_temperature = request_obj.temperature
        max_tokens = request_obj.max_tokens
        file_content = request_obj.file_content
        file_name = _sanitize_file_name(request_obj.file_name)

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

                    # Perform chunking and summarization
                    summarization_models = {
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
                    summarization_model = summarization_models.get(
                        provider, "gpt-4o-mini"
                    )

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


@app.get("/api/all-models")
async def get_all_validated_models(_: None = Depends(verify_api_key)):
    """
    Get all validated models across all providers with detailed metadata.

    Returns models with: provider, cost (input/output), context window,
    capabilities (vision, reasoning, tools, caching), and active status.
    """
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

    return AllModelsResponse(
        providers=result,
        summary={
            "total_models": total_models,
            "total_providers": len(providers_list),
            "active_providers": active_providers,
        },
    )


@app.get("/api/catalog")
async def get_catalog(_: None = Depends(verify_api_key)):
    """Get the full model catalog with metadata.

    Returns data in frontend-compatible format:
    { [provider]: { [modelId]: CatalogModel } }
    """
    catalog = load_catalog()
    providers = catalog.get("providers", {})

    # Transform to frontend-expected format
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for provider, models in providers.items():
        result[provider] = {}
        for model_id, model_data in models.items():
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
            }

    return cast(dict[str, Any], result)


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
    """Health check endpoint."""
    return {"status": "healthy", "version": API_VERSION}


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
async def provider_health_check():
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


if __name__ == "__main__":
    import uvicorn

    # BUG-014: Port configurable via env var, default to 8080 (matches docs)
    port = int(os.getenv("STRATIFYAI_PORT", "8080"))
    # Increase body size limit to 100MB for large file uploads
    uvicorn.run(
        app, host="0.0.0.0", port=port, limit_concurrency=1000, timeout_keep_alive=5
    )
