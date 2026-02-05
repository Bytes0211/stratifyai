"""Unit tests for Phase 7.1: Token Estimation & Chunking."""

import pytest
from pathlib import Path
from stratifyai.utils.token_counter import estimate_tokens, count_tokens_for_messages, get_context_window, check_token_limit
from stratifyai.utils.file_analyzer import detect_file_type, analyze_file, FileType
from stratifyai.chunking import chunk_content, get_chunk_metadata


class TestTokenCounter:
    """Test token counting utilities."""
    
    def test_estimate_tokens_openai(self):
        """Test token estimation for OpenAI models."""
        text = "Hello, world! This is a test."
        tokens = estimate_tokens(text, "openai")
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_estimate_tokens_anthropic(self):
        """Test token estimation for Anthropic models (character-based)."""
        text = "Hello, world! This is a test."
        tokens = estimate_tokens(text, "anthropic")
        assert tokens > 0
        # Character-based estimate: ~4 chars per token
        expected_range = (len(text) // 4 - 2, len(text) // 4 + 2)
        assert expected_range[0] <= tokens <= expected_range[1]
    
    def test_count_tokens_for_messages(self):
        """Test token counting for message lists with formatting overhead."""
        from stratifyai.models import Message
        
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        
        tokens = count_tokens_for_messages(messages, "openai", "gpt-4o")
        assert tokens > 0
        # Should be more than just the content tokens due to formatting
        content_only = estimate_tokens("HelloHi there!", "openai")
        assert tokens > content_only
    
    def test_get_context_window(self):
        """Test context window retrieval."""
        # Known models
        assert get_context_window("openai", "gpt-4o") == 128000
        assert get_context_window("anthropic", "claude-3-5-sonnet-20241022") == 200000
        
        # Unknown model should return default
        assert get_context_window("unknown", "unknown") == 128000
    
    def test_check_token_limit_within_limit(self):
        """Test token limit check when within limit."""
        exceeds, context, pct = check_token_limit(1000, "openai", "gpt-4o", threshold=0.8)
        assert not exceeds
        assert context == 128000
        assert pct < 0.8
    
    def test_check_token_limit_exceeds_threshold(self):
        """Test token limit check when approaching limit."""
        exceeds, context, pct = check_token_limit(110000, "openai", "gpt-4o", threshold=0.8)
        assert exceeds
        assert pct > 0.8
    
    def test_check_token_limit_exceeds_limit(self):
        """Test token limit check when over limit."""
        exceeds, context, pct = check_token_limit(150000, "openai", "gpt-4o")
        assert exceeds
        assert pct > 1.0


class TestFileAnalyzer:
    """Test file analysis utilities."""
    
    def test_detect_file_type_csv(self):
        """Test CSV file detection."""
        assert detect_file_type(Path("data.csv")) == FileType.CSV
    
    def test_detect_file_type_json(self):
        """Test JSON file detection."""
        assert detect_file_type(Path("config.json")) == FileType.JSON
    
    def test_detect_file_type_python(self):
        """Test Python file detection."""
        assert detect_file_type(Path("script.py")) == FileType.PYTHON
    
    def test_detect_file_type_markdown(self):
        """Test Markdown file detection."""
        assert detect_file_type(Path("README.md")) == FileType.MARKDOWN
    
    def test_detect_file_type_unknown(self):
        """Test unknown file detection."""
        assert detect_file_type(Path("file.xyz")) == FileType.UNKNOWN
    
    def test_analyze_file(self, tmp_path):
        """Test complete file analysis."""
        # Create a test file
        test_file = tmp_path / "test.py"
        content = "def hello():\n    print('Hello, world!')\n" * 100
        test_file.write_text(content)
        
        # Analyze it
        analysis = analyze_file(test_file, "openai", "gpt-4o")
        
        assert analysis.file_type == FileType.PYTHON
        assert analysis.file_size_bytes > 0
        assert analysis.estimated_tokens > 0
        assert analysis.recommendation is not None
    
    def test_analyze_file_large_warning(self, tmp_path):
        """Test warning for large files."""
        # Create a large test file
        test_file = tmp_path / "large.txt"
        content = "x" * 1000000  # 1MB
        test_file.write_text(content)
        
        # Analyze it
        analysis = analyze_file(test_file, "openai", "gpt-4o")
        
        # Large file should trigger recommendation about chunking
        assert analysis.exceeds_threshold or "chunk" in analysis.recommendation.lower()


class TestChunking:
    """Test smart chunking utilities."""
    
    def test_chunk_content_small(self):
        """Test chunking with content smaller than chunk size."""
        content = "Small content"
        chunks = chunk_content(content, chunk_size=1000)
        
        assert len(chunks) == 1
        assert chunks[0] == content
    
    def test_chunk_content_multiple_paragraphs(self):
        """Test chunking with multiple paragraphs."""
        # Create content with clear paragraph boundaries
        paragraphs = ["Paragraph 1.\n\n", "Paragraph 2.\n\n", "Paragraph 3.\n\n"] * 50
        content = "".join(paragraphs)
        
        chunks = chunk_content(content, chunk_size=500, overlap=50)
        
        assert len(chunks) > 1
        # Check overlap exists
        if len(chunks) > 1:
            # Last part of chunk[0] should appear in chunk[1]
            assert chunks[0][-50:] in chunks[1]
    
    def test_chunk_content_no_paragraphs(self):
        """Test chunking with no paragraph boundaries (falls back to sentences)."""
        # Long sentence without paragraph breaks
        content = "This is a very long sentence. " * 500
        
        chunks = chunk_content(content, chunk_size=1000)
        
        assert len(chunks) > 1
        # Should split at sentence boundaries
        for chunk in chunks:
            assert chunk.strip().endswith(".")
    
    def test_get_chunk_metadata(self):
        """Test chunk metadata generation."""
        chunks = ["chunk1", "chunk2", "chunk3"]
        metadata = get_chunk_metadata(chunks)
        
        assert metadata["num_chunks"] == 3
        assert metadata["total_chars"] == sum(len(c) for c in chunks)
        assert metadata["avg_chunk_size"] == sum(len(c) for c in chunks) / 3
        assert metadata["min_chunk_size"] == min(len(c) for c in chunks)
        assert metadata["max_chunk_size"] == max(len(c) for c in chunks)
    
    def test_chunk_content_preserves_content(self):
        """Test that chunking doesn't lose content (except overlap)."""
        content = "Test content. " * 1000
        chunks = chunk_content(content, chunk_size=1000, overlap=100)
        
        # Reconstruct content from chunks (removing overlap)
        reconstructed = chunks[0]
        for i in range(1, len(chunks)):
            # Find where this chunk starts (after overlap)
            overlap_end = 100
            reconstructed += chunks[i][overlap_end:]
        
        # Should be approximately the same length (allowing for chunking adjustments)
        assert abs(len(reconstructed) - len(content)) < 200


class TestSummarization:
    """Test summarization utilities."""
    
    # Note: Summarization tests would require API mocking or integration tests
    # Skipping for now as they require LLM API calls
    
    @pytest.mark.skip(reason="Requires API mocking")
    def test_summarize_chunk(self):
        """Test single chunk summarization."""
        pass
    
    @pytest.mark.skip(reason="Requires API mocking")
    def test_summarize_chunks_progressive(self):
        """Test progressive multi-chunk summarization."""
        pass
    
    @pytest.mark.skip(reason="Requires API mocking")
    def test_summarize_file(self):
        """Test complete file summarization."""
        pass
