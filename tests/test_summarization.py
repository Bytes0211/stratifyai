"""Coverage tests for progressive summarization helpers."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.models import ChatResponse, Usage
from stratifyai.summarization import (
    summarize_chunk,
    summarize_chunk_async,
    summarize_chunks_progressive,
    summarize_chunks_progressive_async,
    summarize_file,
    summarize_file_async,
)


def _make_response(content: str) -> ChatResponse:
    return ChatResponse(
        id="summary-1",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        provider="openai",
        created_at=datetime.now(),
        raw_response={},
    )


def test_summarize_chunk_builds_contextual_prompt():
    client = MagicMock()
    client.chat_completion_sync.return_value = _make_response("Short summary")

    result = summarize_chunk(
        "Important section text",
        client,
        model="gpt-4o-mini",
        max_tokens=123,
        context="Quarterly report",
    )

    assert result == "Short summary"
    request = client.chat_completion_sync.call_args.args[0]
    assert request.model == "gpt-4o-mini"
    assert request.max_tokens == 123
    assert "Quarterly report" in request.messages[0].content
    assert "Important section text" in request.messages[0].content


def test_summarize_chunks_progressive_combines_part_summaries():
    client = MagicMock()

    with patch(
        "stratifyai.summarization.summarize_chunk",
        side_effect=["First summary", "Second summary"],
    ) as mock_summarize:
        result = summarize_chunks_progressive(
            ["chunk one", "chunk two"],
            client,
            model="gpt-4o-mini",
            context="Project doc",
            show_progress=False,
        )

    assert "**Part 1/2:**\nFirst summary" in result
    assert "**Part 2/2:**\nSecond summary" in result
    first_call = mock_summarize.call_args_list[0]
    second_call = mock_summarize.call_args_list[1]
    assert first_call.kwargs["context"] == "Project doc (Part 1/2)"
    assert second_call.kwargs["context"] == "Project doc (Part 2/2)"


def test_summarize_chunks_progressive_recursively_summarizes_long_output():
    client = MagicMock()

    with patch(
        "stratifyai.summarization.summarize_chunk",
        side_effect=["A" * 6000, "B" * 6000, "Overall rollup"],
    ) as mock_summarize:
        result = summarize_chunks_progressive(
            ["chunk one", "chunk two"],
            client,
            show_progress=False,
        )

    assert result.startswith("**Overall Summary:**\nOverall rollup")
    assert mock_summarize.call_args_list[-1].kwargs["context"] == (
        "Combined summaries of document sections"
    )


@pytest.mark.asyncio
async def test_summarize_chunk_async_uses_async_client():
    client = MagicMock()
    client.chat_completion = AsyncMock(return_value=_make_response("Async summary"))

    result = await summarize_chunk_async(
        "Async content",
        client,
        model="gpt-4o-mini",
        max_tokens=77,
        context="Async context",
    )

    assert result == "Async summary"
    request = client.chat_completion.await_args.args[0]
    assert request.max_tokens == 77
    assert "Async context" in request.messages[0].content


@pytest.mark.asyncio
async def test_summarize_chunks_progressive_async_combines_part_summaries():
    client = MagicMock()

    with patch(
        "stratifyai.summarization.summarize_chunk_async",
        AsyncMock(side_effect=["Async first", "Async second"]),
    ) as mock_summarize:
        result = await summarize_chunks_progressive_async(
            ["chunk one", "chunk two"],
            client,
            context="Async doc",
        )

    assert "**Part 1/2:**\nAsync first" in result
    assert "**Part 2/2:**\nAsync second" in result
    assert mock_summarize.await_count == 2


@pytest.mark.asyncio
async def test_summarize_file_async_returns_summary_metadata():
    client = MagicMock()

    with patch(
        "stratifyai.summarization.summarize_chunks_progressive_async",
        AsyncMock(return_value="Compressed summary"),
    ) as mock_progressive:
        result = await summarize_file_async(
            ("Alpha beta gamma delta epsilon zeta eta theta.\n" * 6),
            client,
            chunk_size=40,
            model="gpt-4o-mini",
            context="Dataset notes",
        )

    assert result["summary"] == "Compressed summary"
    assert result["original_length"] > result["summary_length"]
    assert result["num_chunks"] >= 2
    assert result["chunk_metadata"]["num_chunks"] == result["num_chunks"]
    assert mock_progressive.await_count == 1


def test_summarize_file_returns_summary_metadata_without_progress():
    client = MagicMock()

    with patch(
        "stratifyai.summarization.summarize_chunks_progressive",
        return_value="Sync compressed summary",
    ) as mock_progressive:
        result = summarize_file(
            ("One two three four five six seven eight nine ten.\n" * 6),
            client,
            chunk_size=40,
            show_progress=False,
        )

    assert result["summary"] == "Sync compressed summary"
    assert result["num_chunks"] >= 2
    assert result["summary_length"] == len("Sync compressed summary")
    mock_progressive.assert_called_once()
