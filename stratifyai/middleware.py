"""Centralized request/response middleware for LLM calls.

Provides ``TrackedLLMClient`` — a wrapper around ``LLMClient`` that
transparently handles:

* Pre-request logging (provider, model, estimated tokens)
* Budget enforcement (raises ``BudgetExceededError`` before the call)
* Latency tracking via ``time.perf_counter``
* Post-response cost tracking via ``CostTracker``
* Post-response logging (tokens, cost, latency)
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import cast

from .client import LLMClient
from .cost_tracker import CostTracker
from .exceptions import BudgetExceededError
from .models import ChatRequest, ChatResponse, Message
from .observability import build_log_extra

logger = logging.getLogger(__name__)


class TrackedLLMClient:
    """Wrapper around :class:`LLMClient` with automatic observability.

    Args:
        client: An existing ``LLMClient`` instance.
        cost_tracker: ``CostTracker`` for recording costs.
    """

    def __init__(
        self,
        client: LLMClient,
        cost_tracker: CostTracker,
    ) -> None:
        self.client = client
        self.cost_tracker = cost_tracker
        self._last_stream_metrics: dict[str, float | int | None] = {}

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Execute a tracked chat completion request."""
        self._pre_request(model, messages)

        start = time.perf_counter()
        response = cast(
            ChatResponse,
            await self.client.chat(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            ),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        response.latency_ms = latency_ms

        self._post_response(response, latency_ms)
        return response

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute a tracked chat completion from a ``ChatRequest``."""
        self._pre_request(request.model, request.messages)

        start = time.perf_counter()
        response = await self.client.chat_completion(request)
        latency_ms = (time.perf_counter() - start) * 1000
        response.latency_ms = latency_ms

        self._post_response(response, latency_ms)
        return response

    async def chat_with_mcp(
        self,
        model: str,
        messages: list[Message],
        mcp_engine,
        active_servers: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Execute a tracked chat completion through the MCP client engine."""
        self._pre_request(model, messages)

        start = time.perf_counter()
        response = await self.client.chat_with_mcp(
            model=model,
            messages=messages,
            mcp_engine=mcp_engine,
            active_servers=active_servers,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        response.latency_ms = latency_ms

        self._post_response(response, latency_ms)
        return response

    async def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """Track streaming latency while proxying streamed chunks."""
        self._pre_request(request.model, request.messages)

        start = time.perf_counter()
        first_token_latency_ms: float | None = None
        chunk_count = 0

        try:
            async for chunk in self.client.chat_completion_stream(request):
                if first_token_latency_ms is None:
                    first_token_latency_ms = (time.perf_counter() - start) * 1000
                chunk_count += 1
                yield chunk
        finally:
            total_latency_ms = (time.perf_counter() - start) * 1000
            self._last_stream_metrics = {
                "first_token_latency_ms": first_token_latency_ms,
                "total_latency_ms": total_latency_ms,
                "chunk_count": chunk_count,
            }
            logger.info(
                "LLM stream response: model=%s chunks=%d first_token_latency=%s total_latency=%.0fms",
                request.model,
                chunk_count,
                (
                    f"{first_token_latency_ms:.0f}ms"
                    if first_token_latency_ms is not None
                    else "n/a"
                ),
                total_latency_ms,
                extra=build_log_extra(
                    model=request.model,
                    chunk_count=chunk_count,
                    first_token_latency_ms=first_token_latency_ms,
                    total_latency_ms=total_latency_ms,
                ),
            )

    def get_last_stream_metrics(self) -> dict[str, float | int | None]:
        """Return telemetry from the most recent streaming request."""
        return dict(self._last_stream_metrics)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _pre_request(self, model: str, messages: list[Message]) -> None:
        """Log request metadata and enforce budget."""
        provider = self.client.provider_name or "auto"
        logger.info(
            "LLM request: provider=%s model=%s messages=%d",
            provider,
            model,
            len(messages),
            extra=build_log_extra(
                provider=provider, model=model, message_count=len(messages)
            ),
        )

        if self.cost_tracker.is_over_budget():
            status = self.cost_tracker.get_budget_status()
            raise BudgetExceededError(
                current_cost=status["total_cost"],
                budget_limit=status["budget_limit"],
            )

    def _post_response(self, response: ChatResponse, latency_ms: float) -> None:
        """Record cost entry and log response metadata."""
        usage = response.usage
        self.cost_tracker.add_entry(
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

        logger.info(
            "LLM response: model=%s tokens=%d cost=$%.6f latency=%.0fms",
            response.model,
            usage.total_tokens,
            usage.cost_usd,
            latency_ms,
            extra=build_log_extra(
                model=response.model,
                total_tokens=usage.total_tokens,
                cost_usd=usage.cost_usd,
                latency_ms=latency_ms,
            ),
        )
