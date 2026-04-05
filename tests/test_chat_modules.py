"""Coverage tests for provider-specific chat helper modules."""

import importlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.models import ChatResponse, Message, Usage

MODULE_CASES = [
    ("stratifyai.chat.stratifyai_openai", "openai", "gpt-4o-mini"),
    (
        "stratifyai.chat.stratifyai_anthropic",
        "anthropic",
        "claude-3-5-sonnet-20241022",
    ),
    ("stratifyai.chat.stratifyai_google", "google", "gemini-2.5-flash"),
    ("stratifyai.chat.stratifyai_deepseek", "deepseek", "deepseek-chat"),
    ("stratifyai.chat.stratifyai_groq", "groq", "llama-3.1-8b-instant"),
    ("stratifyai.chat.stratifyai_grok", "grok", "grok-beta"),
    ("stratifyai.chat.stratifyai_ollama", "ollama", "llama3.2"),
    (
        "stratifyai.chat.stratifyai_openrouter",
        "openrouter",
        "anthropic/claude-3-5-sonnet",
    ),
    (
        "stratifyai.chat.stratifyai_bedrock",
        "bedrock",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
    ),
]


def _make_response(provider: str, content: str = "ok") -> ChatResponse:
    return ChatResponse(
        id=f"{provider}-1",
        model="test-model",
        content=content,
        finish_reason="stop",
        usage=Usage(prompt_tokens=5, completion_tokens=2, total_tokens=7),
        provider=provider,
        created_at=datetime.now(),
        raw_response={},
    )


@pytest.mark.parametrize(("module_name", "provider", "model"), MODULE_CASES)
@pytest.mark.asyncio
async def test_chat_modules_delegate_to_llm_client(module_name, provider, model):
    module = importlib.import_module(module_name)
    module._client = None

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(
        side_effect=[_make_response(provider), "stream-result"]
    )

    with patch.object(module, "LLMClient", return_value=mock_client):
        response = await module.chat(
            "Hello",
            model=model,
            system="Be concise",
            temperature=0.2,
            max_tokens=42,
            extra_option=True,
        )
        stream_result = await module.chat_stream(
            [Message(role="user", content="Hi")],
            model=model,
            temperature=0.4,
        )

    assert response.provider == provider
    assert stream_result == "stream-result"

    first_call = mock_client.chat.await_args_list[0].kwargs
    assert first_call["model"] == model
    assert first_call["temperature"] == 0.2
    assert first_call["max_tokens"] == 42
    assert first_call["stream"] is False
    assert first_call["messages"][0].role == "system"
    assert first_call["messages"][1].content == "Hello"

    second_call = mock_client.chat.await_args_list[1].kwargs
    assert second_call["stream"] is True
    assert second_call["messages"][0].content == "Hi"


@pytest.mark.parametrize(("module_name", "provider", "model"), MODULE_CASES)
def test_chat_module_sync_and_builder_helpers(module_name, provider, model):
    module = importlib.import_module(module_name)
    module._client = None

    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=_make_response(provider, "sync-ok"))

    with patch.object(module, "LLMClient", return_value=mock_client):
        response = module.chat_sync("Sync hello", model=model, system="Sync system")

    assert response.content == "sync-ok"

    builder = MagicMock()
    builder.with_model.return_value = "model-builder"
    builder.with_system.return_value = "system-builder"
    builder.with_developer.return_value = "developer-builder"
    builder.with_temperature.return_value = "temperature-builder"
    builder.with_max_tokens.return_value = "max-builder"
    builder.with_options.return_value = "options-builder"

    with patch.object(module, "_builder", builder):
        assert module.with_model(model) == "model-builder"
        assert module.with_system("sys") == "system-builder"
        assert module.with_developer("dev") == "developer-builder"
        assert module.with_temperature(0.3) == "temperature-builder"
        assert module.with_max_tokens(64) == "max-builder"
        assert module.with_options(trace=True) == "options-builder"
