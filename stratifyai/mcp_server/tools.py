"""MCP tool registrations — thin wrappers around StratifyAI core."""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from stratifyai.api_key_helper import APIKeyHelper
from stratifyai.catalog_manager import load_catalog
from stratifyai.client import LLMClient
from stratifyai.config import MODEL_CATALOG
from stratifyai.cost_tracker import CostTracker
from stratifyai.models import ChatRequest, Message
from stratifyai.router import Router, RoutingStrategy
from stratifyai.utils.token_counter import estimate_tokens

from .errors import raise_tool_error
from .schemas import (
    ChatCompletionOutput,
    ChatWithRoutingOutput,
    CostSummaryOutput,
    EstimateCostOutput,
    ModelInfoOutput,
    ModelSummary,
    ProviderInfo,
    ValidateProviderOutput,
)

# Module-level cost tracker shared across tool calls in a session
_mcp_cost_tracker = CostTracker()


def _track_response_cost(response: Any) -> None:
    """Record response usage in the shared MCP session tracker."""
    usage = response.usage
    _mcp_cost_tracker.add_entry(
        provider=response.provider,
        model=response.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        cost_usd=usage.cost_usd,
        request_id=response.id,
        cached_tokens=usage.cached_tokens,
        cache_creation_tokens=usage.cache_creation_tokens,
        cache_read_tokens=usage.cache_read_tokens,
    )


def _build_cost_summary(
    provider: str | None = None,
    model: str | None = None,
) -> CostSummaryOutput:
    """Build a filtered cost summary from tracked MCP session entries."""
    entries = _mcp_cost_tracker.get_entries(provider=provider, model=model)

    total_cost_usd = sum(entry.cost_usd for entry in entries)
    total_tokens = sum(entry.total_tokens for entry in entries)
    total_calls = len(entries)

    by_provider: dict[str, float] = {}
    by_model: dict[str, float] = {}
    for entry in entries:
        by_provider[entry.provider] = (
            by_provider.get(entry.provider, 0.0) + entry.cost_usd
        )
        by_model[entry.model] = by_model.get(entry.model, 0.0) + entry.cost_usd

    return CostSummaryOutput(
        total_cost_usd=total_cost_usd,
        total_calls=total_calls,
        total_tokens=total_tokens,
        by_provider=by_provider,
        by_model=by_model,
    )


def _is_configured(provider: str) -> bool:
    """Check if a provider has an API key configured."""
    env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider)
    if env_key is None:
        return False
    return bool(os.environ.get(env_key))


def _build_capabilities(model_data: dict[str, Any]) -> list[str]:
    """Extract capability list from model metadata."""
    caps: list[str] = []
    if model_data.get("supports_vision"):
        caps.append("vision")
    if model_data.get("supports_tools"):
        caps.append("tools")
    if model_data.get("supports_streaming"):
        caps.append("streaming")
    if model_data.get("supports_reasoning"):
        caps.append("reasoning")
    return caps


def register(mcp: FastMCP) -> None:  # noqa: C901
    """Register all MCP tools on the server instance."""

    # ------------------------------------------------------------------
    # Phase 2 — Core Tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def chat_completion(
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request to a specific provider and model.

        Returns the response content, token usage, cost, and latency.
        """
        try:
            client = LLMClient(provider=provider)
            msgs = [Message(role=m["role"], content=m["content"]) for m in messages]
            request = ChatRequest(
                model=model,
                messages=msgs,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens,
            )
            response = await client.chat_completion(request)
            _track_response_cost(response)

            cost = 0.0
            if response.usage and response.usage.cost_usd is not None:
                cost = response.usage.cost_usd

            output = ChatCompletionOutput(
                content=response.content,
                provider=provider,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens
                if response.usage
                else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                cost_usd=cost,
                latency_ms=response.latency_ms,
            )
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc, provider, model)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def chat_with_routing(
        messages: list[dict[str, str]],
        strategy: str = "hybrid",
        capabilities: list[str] | None = None,
        preferred_providers: list[str] | None = None,
        excluded_providers: list[str] | None = None,
        max_cost_usd: float | None = None,
        max_latency_ms: float | None = None,
    ) -> dict[str, Any]:
        """Route a chat request to the best provider/model using the specified strategy.

        Strategies: cost, quality, latency, hybrid.
        Returns the selected provider/model, response content, usage, and cost.
        """
        try:
            routing_strategy = RoutingStrategy(strategy)
            router = Router(
                strategy=routing_strategy,
                preferred_providers=preferred_providers,
                excluded_providers=excluded_providers,
            )
            msgs = [Message(role=m["role"], content=m["content"]) for m in messages]
            selected_provider, selected_model = router.route(
                msgs,
                required_capabilities=capabilities,
                max_cost_per_1k_tokens=max_cost_usd,
                max_latency_ms=max_latency_ms,
            )

            client = LLMClient(provider=selected_provider)
            request = ChatRequest(
                model=selected_model,
                messages=msgs,
                temperature=0.7,
            )
            response = await client.chat_completion(request)
            _track_response_cost(response)

            cost = 0.0
            if response.usage and response.usage.cost_usd is not None:
                cost = response.usage.cost_usd

            output = ChatWithRoutingOutput(
                selected_provider=selected_provider,
                selected_model=selected_model,
                routing_strategy=strategy,
                content=response.content,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens
                if response.usage
                else 0,
                cost_usd=cost,
                latency_ms=response.latency_ms,
            )
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def list_providers() -> list[dict[str, Any]]:
        """List all available providers with their model count and configuration status."""
        try:
            catalog = load_catalog()
            providers = catalog.get("providers", {})
            result: list[dict[str, Any]] = []
            for name, models in providers.items():
                info = ProviderInfo(
                    provider=name,
                    model_count=len(models),
                    configured=_is_configured(name),
                )
                result.append(dict(info.model_dump()))
            return result
        except Exception as exc:
            raise_tool_error(exc)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def list_models(provider: str) -> list[dict[str, Any]]:
        """List all models for a given provider with key metadata."""
        try:
            models = MODEL_CATALOG.get(provider)
            if models is None:
                from stratifyai.exceptions import InvalidProviderError

                raise InvalidProviderError(provider)

            result: list[dict[str, Any]] = []
            for model_id, data in models.items():
                summary = ModelSummary(
                    model_id=model_id,
                    context_window=int(data.get("context", 0)),
                    cost_input_per_1m=float(data.get("cost_input", 0.0)),
                    cost_output_per_1m=float(data.get("cost_output", 0.0)),
                    capabilities=_build_capabilities(data),
                )
                result.append(dict(summary.model_dump()))
            return result
        except Exception as exc:
            raise_tool_error(exc, provider)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def get_model_info(provider: str, model: str) -> dict[str, Any]:
        """Get full metadata for a specific model."""
        try:
            provider_models = MODEL_CATALOG.get(provider)
            if provider_models is None:
                from stratifyai.exceptions import InvalidProviderError

                raise InvalidProviderError(provider)

            model_data = provider_models.get(model)
            if model_data is None:
                from stratifyai.exceptions import InvalidModelError

                raise InvalidModelError(model, provider)

            output = ModelInfoOutput(
                provider=provider,
                model=model,
                metadata=dict(model_data),
            )
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc, provider, model)
            raise  # unreachable — satisfies mypy

    # ------------------------------------------------------------------
    # Phase 3 — Cost and Validation Tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_cost_summary(
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Get cost summary for the current MCP session.

        Optionally filter by provider or model.
        """
        try:
            output = _build_cost_summary(provider=provider, model=model)
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc, provider, model)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def validate_provider(provider: str) -> dict[str, Any]:
        """Validate that a provider is configured and accessible."""
        try:
            if provider not in MODEL_CATALOG:
                output = ValidateProviderOutput(
                    provider=provider,
                    configured=False,
                    models_available=[],
                    validation_errors=[
                        f"Unknown provider: {provider}",
                        f"No models found in catalog for provider '{provider}'",
                    ],
                )
                return dict(output.model_dump())

            configured = _is_configured(provider)
            models = list(MODEL_CATALOG.get(provider, {}).keys())
            errors: list[str] = []

            if not configured:
                env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider, "UNKNOWN")
                errors.append(f"API key not set (expected env var: {env_key})")

            if not models:
                errors.append(f"No models found in catalog for provider '{provider}'")

            output = ValidateProviderOutput(
                provider=provider,
                configured=configured,
                models_available=models,
                validation_errors=errors,
            )
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc, provider)
            raise  # unreachable — satisfies mypy

    @mcp.tool()
    async def estimate_cost(
        provider: str,
        model: str,
        message_text: str,
    ) -> dict[str, Any]:
        """Estimate the token count and cost for a message with a given provider/model."""
        try:
            provider_models = MODEL_CATALOG.get(provider)
            if provider_models is None:
                from stratifyai.exceptions import InvalidProviderError

                raise InvalidProviderError(provider)

            model_data = provider_models.get(model)
            if model_data is None:
                from stratifyai.exceptions import InvalidModelError

                raise InvalidModelError(model, provider)

            tokens = estimate_tokens(message_text)
            cost_per_1m = float(model_data.get("cost_input", 0.0))
            estimated_cost = (tokens / 1_000_000) * cost_per_1m

            output = EstimateCostOutput(
                estimated_input_tokens=tokens,
                estimated_cost_usd=estimated_cost,
                provider=provider,
                model=model,
            )
            return dict(output.model_dump())
        except Exception as exc:
            raise_tool_error(exc, provider, model)
            raise  # unreachable — satisfies mypy
