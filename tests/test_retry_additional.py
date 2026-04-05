"""Additional retry and fallback coverage tests."""

import pytest

from stratifyai.exceptions import ProviderAPIError
from stratifyai.retry import RetryConfig, exponential_backoff, with_retry


def test_exponential_backoff_caps_without_jitter():
    assert exponential_backoff(0, initial_delay=1.0, jitter=False) == 1.0
    assert exponential_backoff(3, initial_delay=1.0, jitter=False) == 8.0
    assert (
        exponential_backoff(10, initial_delay=1.0, max_delay=5.0, jitter=False) == 5.0
    )


@pytest.mark.asyncio
async def test_retry_does_not_repeat_permanent_400_errors():
    calls = 0

    @with_retry(config=RetryConfig(max_retries=3, initial_delay=0, jitter=False))
    async def fail_once():
        nonlocal calls
        calls += 1
        raise ProviderAPIError("bad request", "openai", status_code=400)

    with pytest.raises(ProviderAPIError):
        await fail_once()

    assert calls == 1


@pytest.mark.asyncio
async def test_retry_uses_fallback_model_when_configured():
    seen_models = []

    class Request:
        def __init__(self):
            self.model = "primary-model"

    @with_retry(config=RetryConfig(max_retries=0), fallback_models=["backup-model"])
    async def maybe_succeed(*, request):
        seen_models.append(request.model)
        if request.model == "primary-model":
            raise ProviderAPIError("temporary failure", "openai", status_code=500)
        return request.model

    request = Request()
    result = await maybe_succeed(request=request)

    assert result == "backup-model"
    assert seen_models == ["primary-model", "backup-model"]


@pytest.mark.asyncio
async def test_retry_uses_fallback_provider_when_configured():
    seen_providers = []

    @with_retry(config=RetryConfig(max_retries=0), fallback_provider="anthropic")
    async def maybe_switch_provider(*, provider):
        seen_providers.append(provider)
        if provider != "anthropic":
            raise ProviderAPIError("temporary failure", provider, status_code=500)
        return provider

    result = await maybe_switch_provider(provider="openai")

    assert result == "anthropic"
    assert seen_providers == ["openai", "anthropic"]
