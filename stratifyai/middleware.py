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
from typing import AsyncIterator, Optional, Union

from .client import LLMClient
from .cost_tracker import CostTracker
from .exceptions import BudgetExceededError
from .models import ChatRequest, ChatResponse, Message

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

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """Execute a tracked chat completion request."""
        self._pre_request(model, messages)

        start = time.perf_counter()
        response = await self.client.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs,
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

    async def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """Proxy streaming — budget check only (no post-response tracking)."""
        self._pre_request(request.model, request.messages)
        async for chunk in self.client.chat_completion_stream(request):
            yield chunk

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
        )
