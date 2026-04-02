# Changelog

All notable changes to StratifyAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Documentation improvements with badges and type hints

## [0.1.0] - 2026-02-04

### Added
- Unified interface for 9 LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock)
- Async-first architecture with native SDK clients
- Sync wrappers for convenience (`chat_sync()`, `chat_completion_sync()`)
- Builder pattern for fluent configuration
- Required model parameter across all chat providers
- Intelligent routing with cost/quality/latency/hybrid strategies
- Cost tracking and budget enforcement
- Latency tracking on all responses
- Response caching with hit/miss analytics
- Provider prompt caching support
- Retry logic with exponential backoff
- Fallback model chains
- Streaming support for all providers
- Large file handling with chunking and progressive summarization
- File extraction (CSV schema, JSON schema, logs, code structure)
- Auto model selection for extraction tasks
- RAG pipeline with embeddings and ChromaDB vector storage
- Semantic search and citation tracking
- Rich/Typer CLI with interactive mode
- Optional FastAPI web interface with WebSocket streaming
- Cache inspection and management commands
- Comprehensive test suite (300+ tests)

### Technical
- Python 3.10+ support
- Type hints on all functions and methods
- Abstract base classes for provider abstraction
- Dataclasses for data models
- Google-style docstrings
- Black formatting, Ruff linting, Mypy type checking
- pytest with async support (pytest-asyncio)

## [0.0.1] - 2025-12-01

### Added
- Initial project structure
- BaseProvider abstract class
- OpenAI provider implementation
- Basic LLMClient with provider detection
- Core data models (Message, ChatRequest, ChatResponse)
- Custom exception hierarchy

---

[Unreleased]: https://github.com/Bytes0211/stratifyai/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Bytes0211/stratifyai/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/Bytes0211/stratifyai/releases/tag/v0.0.1
