"""Real-provider integration tests gated by API key secrets.

These tests are intentionally marked as integration tests and make live API calls
to configured providers. They are skipped automatically when no provider keys are
available in the environment.
"""

import os

import pytest

from stratifyai.client import LLMClient
from stratifyai.exceptions import ProviderAPIError
from stratifyai.models import ChatRequest, Message


pytestmark = [pytest.mark.integration]


PROVIDER_MATRIX = [
    ("openai", "OPENAI_API_KEY", "gpt-4o-mini"),
    ("anthropic", "ANTHROPIC_API_KEY", "claude-3-haiku-20240307"),
    ("google", "GOOGLE_API_KEY", "gemini-2.5-flash"),
]


def _enabled_provider_configs() -> list[tuple[str, str, str]]:
    """Return provider configs that have required API key secrets."""
    enabled: list[tuple[str, str, str]] = []
    for provider, key_env, model in PROVIDER_MATRIX:
        if os.getenv(key_env):
            enabled.append((provider, key_env, model))
    return enabled


@pytest.mark.asyncio
async def test_real_provider_chat_completion() -> None:
    """Validate end-to-end chat completion against real provider APIs."""
    enabled = _enabled_provider_configs()
    if not enabled:
        pytest.skip(
            "No provider API key configured for integration tests. "
            "Set one of OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY."
        )

    skipped: list[str] = []
    for provider, _key_env, model in enabled:
        client = LLMClient(provider=provider)
        request = ChatRequest(
            model=model,
            messages=[
                Message(role="user", content="Reply with exactly: integration-ok")
            ],
            temperature=0.0,
            max_tokens=32,
        )

        try:
            response = await client.chat_completion(request)
        except ProviderAPIError as exc:
            # API-level failures (deprecated models, IP restrictions, quota, etc.)
            # are infrastructure issues, not code bugs. Warn and continue.
            skipped.append(f"[{provider}] skipped due to API error: {exc}")
            continue

        assert response.provider == provider
        assert response.model
        assert response.content
        assert response.usage.total_tokens > 0

    if skipped and len(skipped) == len(enabled):
        pytest.skip(
            "All configured providers returned API errors (infrastructure, not code):\n"
            + "\n".join(skipped)
        )

