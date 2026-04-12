"""Micro-tests targeting specific uncovered lines to meet the 80% coverage threshold."""

from __future__ import annotations

from stratifyai.chunking import chunk_content, get_chunk_metadata
from stratifyai.exceptions import RateLimitError
from stratifyai.mcp_client.tool_registry import ToolRegistry
from stratifyai.models import Message


class TestExceptionsMissingLines:
    """Cover the retry_after branch of RateLimitError (line 73)."""

    def test_rate_limit_error_with_retry_after(self) -> None:
        """retry_after appends a 'Retry after N seconds' suffix."""
        err = RateLimitError("openai", retry_after=30)
        assert "30 seconds" in str(err)
        assert err.retry_after == 30

    def test_rate_limit_error_without_retry_after(self) -> None:
        """retry_after=None omits the suffix."""
        err = RateLimitError("openai")
        assert "seconds" not in str(err)


class TestModelsMissingLines:
    """Cover parse_vision_content return when no image (line 30)."""

    def test_parse_vision_content_no_image(self) -> None:
        """A plain-text message returns (content, None)."""
        msg = Message(role="user", content="Hello world")
        text, img = msg.parse_vision_content()
        assert text == "Hello world"
        assert img is None


class TestToolRegistryMissingLines:
    """Cover find_by_namespace with no-dot input (line 46)."""

    def test_find_by_namespace_no_dot(self) -> None:
        """A namespace without a '.' separator returns None."""
        registry = ToolRegistry()
        result = registry.find_by_namespace("nodothere")
        assert result is None

    def test_find_by_namespace_empty(self) -> None:
        """An empty namespace string returns None."""
        registry = ToolRegistry()
        result = registry.find_by_namespace("")
        assert result is None


class TestChunkingMissingLines:
    """Cover the fixed-position chunking and empty-input branches."""

    def test_chunk_content_empty_returns_empty_list(self) -> None:
        """Empty content returns an empty list (line 34)."""
        assert chunk_content("") == []

    def test_chunk_content_fixed_position_chunking(self) -> None:
        """preserve_boundaries=False uses fixed-position chunking (lines 79-84)."""
        content = "A" * 200
        chunks = chunk_content(
            content, chunk_size=50, overlap=10, preserve_boundaries=False
        )
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_chunk_content_no_overlap_on_boundary(self) -> None:
        """When overlap=0 and chunk overflows, current_chunk is set to '' (line 57)."""
        # Build content that forces the overlap=0 branch
        para1 = "X" * 80
        para2 = "Y" * 80
        content = para1 + "\n\n" + para2
        chunks = chunk_content(content, chunk_size=90, overlap=0)
        assert len(chunks) >= 2

    def test_get_chunk_metadata_empty_list(self) -> None:
        """Empty chunk list returns zeroed-out metadata (line 141)."""
        meta = get_chunk_metadata([])
        assert meta["num_chunks"] == 0
        assert meta["total_chars"] == 0
        assert meta["avg_chunk_size"] == 0
