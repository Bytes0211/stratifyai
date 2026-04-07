# Changelog

All notable changes to StratifyAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.3] - 2026-04-07

### Fixed
- Pinned `fastapi` below `1.0` in release metadata so TestPyPI and future installs do not resolve an unvalidated major version during dependency installation
- Confirmed the `2.0.2` TestPyPI failure was caused by a broken third-party `FASTAPI-1.0` source distribution on TestPyPI rather than missing StratifyAI package files

## [2.0.2] - 2026-04-07

### Fixed
- Cleaned the release artifacts so local editor/MCP config folders like `.cursor/` and `.vscode/` are not bundled in published distributions
- Stopped auto-enabling newly discovered MCP servers in the Web UI, keeping fresh installs isolated until the user explicitly opts in
- Added clearer install-time and runtime guidance that MCP integrations using `npx` require Node.js 18+ on `PATH`

## [2.0.1] - 2026-04-07

### Fixed
- Promoted `mcp[cli]` to a core runtime dependency so clean installs no longer fail with `ModuleNotFoundError: No module named 'mcp'`
- Added smoother MCP setup heuristics by defaulting filesystem server paths to the project root/current directory when omitted
- Improved MCP startup diagnostics and API error mapping for missing executables like `npx`/Node.js

## [2.0.0] - 2026-04-06

### Added
- Complete MCP ecosystem: server, client engine, abstraction layer, and permission controls
- Prompt templates, profile system, and Svelte 5 SPA for interactive usage
- O(1) cache improvements, concurrency limits, and observability/metrics endpoints
- AWS Bedrock maturity improvements, RAG workflows, and large-file processing enhancements
- `stratifyai doctor` CLI command and `route --dry-run` for release diagnostics

### Changed
- Version metadata aligned for the 2.0.0 release across package and API surfaces
- Deployment documentation refreshed for **local distro first**, then TestPyPI/PyPI release flow
- Security and error handling hardening expanded across HTTP, WebSocket, and provider paths

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
- Ruff formatting/linting and Mypy type checking
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

[Unreleased]: https://github.com/Bytes0211/stratifyai/compare/v2.0.3...HEAD
[2.0.3]: https://github.com/Bytes0211/stratifyai/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/Bytes0211/stratifyai/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/Bytes0211/stratifyai/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Bytes0211/stratifyai/compare/v0.1.0...v2.0.0
[0.1.0]: https://github.com/Bytes0211/stratifyai/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/Bytes0211/stratifyai/releases/tag/v0.0.1
