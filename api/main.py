"""FastAPI application for StratifyAI."""

import json
import logging
import tomllib
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv()

from stratifyai import LLMClient, ChatRequest, Message, ProviderType
from stratifyai.cost_tracker import CostTracker
from stratifyai.config import MODEL_CATALOG
from stratifyai.utils.reasoning_detector import is_reasoning_model, get_temperature_for_model

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
                return data.get("project", {}).get("version", "0.1.0")
    except Exception:
        pass
    return "0.1.0"

API_VERSION = _get_version()

# Shared ThreadPoolExecutor for async validation tasks (BUG-008)
_executor = ThreadPoolExecutor(max_workers=4)

# Client cache for connection pooling (BUG-003)
_client_cache: Dict[str, LLMClient] = {}

def get_client(provider: str) -> LLMClient:
    """Get or create a cached LLMClient for connection pooling."""
    if provider not in _client_cache:
        _client_cache[provider] = LLMClient(provider=provider)
    return _client_cache[provider]

# Initialize FastAPI app
app = FastAPI(
    title="StratifyAI API",
    description="Unified API for multiple LLM providers",
    version=API_VERSION,
)

# Configure CORS (BUG-004: Wildcard + credentials is invalid per CORS spec)
# Read allowed origins from env var or use permissive defaults for development
_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if _cors_origins == "*":
    # Wildcard mode: don't allow credentials (spec compliant)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Specific origins: credentials allowed
    _allowed_origins = [origin.strip() for origin in _cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Global cost tracker
cost_tracker = CostTracker()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Request/Response models
class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""
    provider: str
    model: str
    messages: List[dict]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    file_content: Optional[str] = None  # Base64 encoded file content or plain text
    file_name: Optional[str] = None  # Original filename for type detection
    chunked: bool = False  # Enable smart chunking and summarization
    chunk_size: int = 50000  # Chunk size in characters


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
    models: List[str]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    error_type: str


@app.get("/")
async def root():
    """Serve the frontend interface."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": "StratifyAI API",
        "version": API_VERSION,
        "message": "Frontend not found. API endpoints available at /docs"
    }


@app.get("/models")
async def models_page():
    """Serve the models catalog page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    models_path = os.path.join(static_dir, "models.html")
    if os.path.exists(models_path):
        return FileResponse(models_path)
    return {"error": "Models page not found"}


@app.get("/api/providers", response_model=List[str])
async def list_providers():
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
    models: List[ModelInfo]
    validation: dict


@app.get("/api/models/{provider}", response_model=ModelListResponse)
async def list_models(provider: str):
    """List validated models for a specific provider."""
    from stratifyai.utils.provider_validator import get_validated_interactive_models
    
    if provider not in MODEL_CATALOG:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
    
    # Run validation in background thread to avoid blocking (BUG-007: use get_running_loop)
    loop = asyncio.get_running_loop()
    validation_data = await loop.run_in_executor(
        _executor, 
        get_validated_interactive_models, 
        provider
    )
    
    validated_models = validation_data["models"]
    validation_result = validation_data["validation_result"]
    
    # Log validation result
    if validation_result["error"]:
        logger.warning(f"Model validation for {provider}: {validation_result['error']}")
    else:
        logger.info(f"Model validation for {provider}: {len(validated_models)} models in {validation_result['validation_time_ms']}ms")
    
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
        models_info.append(ModelInfo(
            id=model_id,
            display_name=meta.get("display_name", model_id),
            description=meta.get("description", ""),
            category=meta.get("category", ""),
            reasoning_model=meta.get("reasoning_model", False),
            supports_vision=meta.get("supports_vision", False),
        ))
    
    return ModelListResponse(
        models=models_info,
        validation=validation_result
    )


@app.get("/api/model-info/{provider}/{model}")
async def get_model_info(provider: str, model: str):
    """Get detailed information about a specific model."""
    if provider not in MODEL_CATALOG:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
    
    if model not in MODEL_CATALOG[provider]:
        raise HTTPException(status_code=404, detail=f"Model '{model}' not found for provider '{provider}'")
    
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


@app.get("/api/provider-info", response_model=List[ProviderInfo])
async def get_provider_info():
    """Get information about all providers and their models."""
    providers = []
    for provider_name, models in MODEL_CATALOG.items():
        providers.append(ProviderInfo(
            name=provider_name,
            models=list(models.keys())
        ))
    return providers


@app.post("/api/chat", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    """
    Execute a chat completion request.
    
    Args:
        request: Chat completion request
        
    Returns:
        Chat completion response with cost tracking
    """
    try:
        # Convert messages to Message objects
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in request.messages
        ]
        
        # Process file if provided
        if request.file_content and request.file_name:
            from stratifyai.summarization import summarize_file_async
            from stratifyai.utils.file_analyzer import analyze_file
            from pathlib import Path
            import tempfile
            import base64
            
            # Detect if content is base64 encoded or plain text
            try:
                # Try to decode as base64
                file_bytes = base64.b64decode(request.file_content)
                file_text = file_bytes.decode('utf-8')
            except Exception:
                # If decoding fails, assume it's plain text
                file_text = request.file_content
            
            # Apply chunking if enabled
            if request.chunked:
                logger.info(f"Chunking file {request.file_name} (size: {len(file_text)} chars, chunk_size: {request.chunk_size})")
                
                # Create temporary file for analysis
                with tempfile.NamedTemporaryFile(mode='w', suffix=Path(request.file_name).suffix, delete=False) as tmp_file:
                    tmp_file.write(file_text)
                    tmp_path = Path(tmp_file.name)  # Convert to Path object
                
                try:
                    # Analyze file to determine if chunking is beneficial
                    analysis = analyze_file(tmp_path, request.provider, request.model)
                    logger.info(f"File analysis: type={analysis.file_type.value}, tokens={analysis.estimated_tokens}")
                    
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
                    summarization_model = summarization_models.get(request.provider, "gpt-4o-mini")
                    
                    client = get_client(request.provider)  # BUG-003: Use cached client
                    
                    # Get context from last user message if available
                    context = None
                    if messages and messages[-1].role == "user":
                        context = messages[-1].content
                    
                    # Run async summarization with cheap model
                    result = await summarize_file_async(
                        file_text,
                        client,
                        request.chunk_size,
                        summarization_model,
                        context,
                        False  # show_progress=False for API
                    )
                    
                    # Use summarized content
                    file_content_to_use = result['summary']
                    logger.info(f"Chunking complete: {result['reduction_percentage']}% reduction ({result['original_length']} -> {result['summary_length']} chars)")
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
                messages[-1].content = f"{messages[-1].content}\n\n[File: {request.file_name}]\n\n{file_content_to_use}"
            else:
                # Create new user message with file content
                messages.append(Message(
                    role="user",
                    content=f"[File: {request.file_name}]\n\n{file_content_to_use}"
                ))
        
        # Validate token count before making request
        from stratifyai.utils.token_counter import count_tokens_for_messages, get_context_window
        estimated_tokens = count_tokens_for_messages(messages, request.provider, request.model)
        
        # Get context window and API limits
        context_window = get_context_window(request.provider, request.model)
        model_info = MODEL_CATALOG.get(request.provider, {}).get(request.model, {})
        api_max_input = model_info.get("api_max_input")
        effective_limit = api_max_input if api_max_input and api_max_input < context_window else context_window
        
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
                    "provider": request.provider,
                    "model": request.model,
                    "suggestion": "Please split your file into smaller chunks or use a different processing approach."
                }
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
                        "provider": request.provider,
                        "model": request.model,
                        "suggestion": "✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, gemini-2.5-flash\n✓ Switch to OpenRouter with google/gemini-2.5-pro or google/gemini-2.5-flash",
                        "chunking_enabled": request.chunked
                    }
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
                        "chunking_enabled": request.chunked
                    }
                )
        
        # Determine temperature using shared reasoning model detector (BUG-002)
        reasoning = is_reasoning_model(request.provider, request.model, MODEL_CATALOG)
        temperature = get_temperature_for_model(
            request.provider, request.model, request.temperature, MODEL_CATALOG
        )
        
        if reasoning and request.temperature is not None and request.temperature != 1.0:
            logger.warning(f"Overriding temperature={request.temperature} to 1.0 for reasoning model {request.provider}/{request.model}")
        else:
            logger.info(f"Using temperature={temperature} for model {request.provider}/{request.model}")
        
        # Create chat request
        chat_request = ChatRequest(
            model=request.model,
            messages=messages,
            temperature=temperature,
            max_tokens=request.max_tokens,
        )
        
        # Initialize client and make request (BUG-003: use cached client)
        client = get_client(request.provider)
        response = await client.chat_completion(chat_request)
        
        # Track cost
        cost_tracker.add_entry(
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            cost_usd=response.usage.cost_usd,
            request_id=response.id,
            cached_tokens=response.usage.cached_tokens,
            cache_creation_tokens=response.usage.cache_creation_tokens,
            cache_read_tokens=response.usage.cache_read_tokens,
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
            },
            cost_usd=response.usage.cost_usd,
        )
    except HTTPException:
        # Re-raise our custom HTTP exceptions (token limits, etc.)
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat completion error: {error_msg}")
        
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
            token_match = re.search(r'(\d+)\s+tokens?\s+>\s+(\d+)', error_msg)
            if token_match:
                actual_tokens = int(token_match.group(1))
                limit_tokens = int(token_match.group(2))
                
                # Get model info to provide smart suggestions
                model_info = MODEL_CATALOG.get(request.provider, {}).get(request.model, {})
                context_window = model_info.get("context", 0)
                api_max_input = model_info.get("api_max_input")
                
                if api_max_input and context_window > api_max_input:
                    suggestion = f"✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, gemini-2.5-flash\n✓ Your input: {actual_tokens:,} tokens | API limit: {limit_tokens:,} tokens | Model context: {context_window:,} tokens"
                else:
                    suggestion = f"✓ Switch to a model with larger context window (Google Gemini 2.5: 1M tokens)\n✓ Enable 'Smart Chunking' to reduce token usage\n✓ Your input: {actual_tokens:,} tokens | Model limit: {limit_tokens:,} tokens"
        
        detail = {
            "error": error_type,
            "detail": error_msg,
            "provider": request.provider,
            "model": request.model
        }
        
        if suggestion:
            detail["suggestion"] = suggestion
        
        raise HTTPException(
            status_code=status_code,
            detail=detail
        )


@app.websocket("/api/chat/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat completions.
    
    Protocol:
        Client sends JSON: {"provider": "openai", "model": "gpt-4", "messages": [...]}
        Server streams JSON chunks: {"content": "...", "done": false}
        Final message: {"content": "", "done": true, "usage": {...}}
    """
    await websocket.accept()
    
    try:
        # Receive request
        data = await websocket.receive_text()
        request_data = json.loads(data)
        
        provider = request_data.get("provider")
        model = request_data.get("model")
        messages_data = request_data.get("messages", [])
        requested_temperature = request_data.get("temperature")
        max_tokens = request_data.get("max_tokens")
        
        # Convert messages
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]
        
        # Determine temperature using shared reasoning model detector (BUG-002)
        reasoning = is_reasoning_model(provider, model, MODEL_CATALOG)
        temperature = get_temperature_for_model(
            provider, model, requested_temperature, MODEL_CATALOG
        )
        
        if reasoning and requested_temperature is not None and requested_temperature != 1.0:
            logger.warning(f"Overriding temperature={requested_temperature} to 1.0 for reasoning model {provider}/{model}")
        else:
            logger.info(f"Using temperature={temperature} for model {provider}/{model}")
        
        # Create request
        chat_request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Initialize client (BUG-003: use cached client for connection pooling)
        client = get_client(provider)
        
        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        stream = client.chat_completion_stream(chat_request)
        async for chunk in stream:
            full_content += chunk.content
            # Accumulate token usage from chunks if available
            if hasattr(chunk, 'usage') and chunk.usage:
                if chunk.usage.prompt_tokens:
                    prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens += chunk.usage.completion_tokens or 0
            await websocket.send_json({
                "content": chunk.content,
                "done": False,
            })
        
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
        cost_usd = (prompt_tokens / 1_000_000 * cost_input) + (completion_tokens / 1_000_000 * cost_output)
        
        cost_tracker.add_entry(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            request_id=f"ws-{id(websocket)}-{int(asyncio.get_running_loop().time())}",
        )
        
        # Send final message with usage info
        await websocket.send_json({
            "content": "",
            "done": True,
            "full_content": full_content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
        })
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "error": str(e),
                "done": True,
            })
        except Exception:
            pass  # Connection may already be closed
    finally:
        # BUG-005: Avoid double-close RuntimeError
        try:
            await websocket.close()
        except RuntimeError:
            pass  # Already closed


@app.get("/api/cost")
async def get_cost_summary():
    """Get cost tracking summary."""
    return cost_tracker.get_summary()


@app.post("/api/cost/reset")
async def reset_cost_tracker():
    """Reset cost tracker."""
    cost_tracker.reset()
    return {"message": "Cost tracker reset successfully"}


class ProviderModelsInfo(BaseModel):
    """Models info for a single provider."""
    models: List[dict]
    active: bool
    validation_error: Optional[str] = None
    validation_time_ms: int = 0


class AllModelsResponse(BaseModel):
    """Response model for all validated models."""
    providers: Dict[str, ProviderModelsInfo]
    summary: dict


@app.get("/api/all-models")
async def get_all_validated_models():
    """
    Get all validated models across all providers with detailed metadata.
    
    Returns models with: provider, cost (input/output), context window,
    capabilities (vision, reasoning, tools, caching), and active status.
    """
    from stratifyai.utils.provider_validator import validate_provider_models
    from stratifyai.api_key_helper import APIKeyHelper
    
    providers_list = [
        "openai", "anthropic", "google", "deepseek",
        "groq", "grok", "ollama", "openrouter", "bedrock"
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
            _executor,
            validate_provider_models,
            provider,
            model_ids
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
        model_ids = validation_result["valid_models"] if not validation_result["error"] else list(catalog.keys())
        
        for model_id in model_ids:
            model_info = catalog.get(model_id, {})
            
            models_list.append({
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
            })
        
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
        }
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": API_VERSION}


if __name__ == "__main__":
    import uvicorn
    # BUG-014: Port configurable via env var, default to 8080 (matches docs)
    port = int(os.getenv("STRATIFYAI_PORT", "8080"))
    # Increase body size limit to 100MB for large file uploads
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        limit_concurrency=1000,
        timeout_keep_alive=5
    )
