"""Regression tests for Phase 8.0 critical bug and security fixes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.exceptions import MaxRetriesExceededError, ProviderAPIError
from stratifyai.models import ChatRequest, Message
from stratifyai.retry import RetryConfig, with_retry
from stratifyai.utils.sanitizer import sanitize_error
from stratifyai.utils.sync_helpers import run_sync


@pytest.mark.asyncio
async def test_retry_raises_max_retries_with_attempts_and_last_error():
    """MaxRetriesExceededError should preserve attempts and last_error."""
    @with_retry(config=RetryConfig(max_retries=1))
    async def fail():
        raise ProviderAPIError("boom", "openai")

    with pytest.raises(MaxRetriesExceededError) as exc:
        await fail()

    assert exc.value.attempts == 1
    assert isinstance(exc.value.last_error, ProviderAPIError)


@pytest.mark.asyncio
async def test_run_sync_works_inside_running_event_loop():
    """run_sync should work even when called from an active event loop."""
    result = run_sync(_sample_coro())
    assert result == "ok"


async def _sample_coro() -> str:
    return "ok"


def test_sanitize_error_scrubs_known_key_patterns():
    key = "sk-proj-abcdef1234567890SECRET"
    msg = f"request failed for key={key}"
    out = sanitize_error(msg, key)
    assert key not in out
    assert "REDACTED" in out


@patch("stratifyai.providers.openai_compatible.AsyncOpenAI")
@pytest.mark.asyncio
async def test_openai_compatible_text_only_message_does_not_unpack_none(
    mock_openai_class,
):
    """Text-only messages should not trigger vision tuple unpack crashes."""
    from stratifyai.providers.google import GoogleProvider

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.model_dump.return_value = {
        "id": "x",
        "model": "gemini-2.5-flash",
        "created": 123,
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    provider = GoogleProvider(api_key="test")
    req = ChatRequest(
        model="gemini-2.5-flash",
        messages=[Message(role="user", content="hello")],
    )
    resp = await provider.chat_completion(req)
    assert resp.content == "ok"
