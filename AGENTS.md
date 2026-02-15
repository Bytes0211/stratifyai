# AGENTS.md

This file provides guidance to AI agents (Warp, Cursor, Windsurf, etc.) when working with code in this repository.

## Project Overview

StratifyAI is a production-ready Python module that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock) through a consistent API. The project demonstrates advanced API abstraction, design patterns (strategy, factory), multi-provider integration, production engineering (error handling, retry logic, cost tracking), and Python best practices (type hints, abstract base classes, decorators).

## Development Environment Setup

### Initial Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Using uv (Alternative)
```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r requirements.txt
```

### AWS Bedrock Setup

For using AWS Bedrock models, you need to configure AWS credentials:

**Option 1: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"  # Optional, defaults to us-east-1
```

**Option 2: AWS Credentials File**
```bash
# Configure AWS CLI (creates ~/.aws/credentials)
aws configure

# Or manually create ~/.aws/credentials:
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = your-access-key-id
aws_secret_access_key = your-secret-access-key
EOF
```

**Option 3: IAM Roles** (when running on AWS EC2/ECS/Lambda)
- No explicit credentials needed
- boto3 automatically uses the instance's IAM role

**Supported Bedrock Models:**
- Anthropic Claude: `anthropic.claude-3-5-sonnet-20241022-v2:0`, `anthropic.claude-3-5-haiku-20241022-v1:0`
- Meta Llama: `meta.llama3-3-70b-instruct-v1:0`, `meta.llama3-2-90b-instruct-v1:0`
- Mistral AI: `mistral.mistral-large-2402-v1:0`, `mistral.mistral-small-2402-v1:0`
- Amazon Nova: `amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-micro-v1:0`
- Cohere: `cohere.command-r-plus-v1:0`, `cohere.command-r-v1:0`

**Permissions Required:**
Your AWS IAM user/role must have the `bedrock:InvokeModel` permission:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": "*"
  }]
}
```

## Project Structure

```txt
stratifyai/                             # Project root: /home/scotton/dev/projects/stratifyai
├── README.md
├── AGENTS.md                           # This file (AI agent guidance)
├── pyproject.toml                      # Package configuration and dependencies
├── requirements.txt                    # Python dependencies
├── .venv/                              # Virtual environment
├── .github/workflows/                  # GitHub Actions CI/CD
│   └── validate-catalog.yml            # Catalog validation on PRs
├── api/                                # FastAPI REST API
│   ├── main.py                         # API endpoints
│   └── static/index.html               # Web frontend
├── catalog/                            # Model catalog (community-editable)
│   ├── models.json                     # Provider model metadata (JSON)
│   ├── schema.json                     # JSON schema for validation
│   └── README.md                       # Contribution guidelines
├── cli/                                # CLI package
│   └── stratifyai_cli.py               # Typer CLI implementation
├── docs/                               # Documentation
│   ├── API-REFERENCE.md
│   ├── cli-usage.md
│   ├── GETTING-STARTED.md
│   ├── StratifyAI-Router-Logic.md
│   └── ...                             # Additional docs
├── examples/                           # Example applications
│   ├── chatbot.py
│   ├── code_reviewer.py
│   ├── rag_example.py
│   └── ...                             # Additional examples
├── scripts/                            # Utility scripts
│   └── validate_catalog.py             # Catalog validation tool
├── tests/                              # Test suite (297+ tests)
└── stratifyai/                         # Main package
    ├── __init__.py                     # Package exports
    ├── catalog_manager.py              # Loads models from catalog/models.json
    ├── client.py                       # Unified LLMClient
    ├── config.py                       # Loads catalog via catalog_manager
    ├── models.py                       # Data models (Message, ChatRequest, ChatResponse)
    ├── exceptions.py                   # Custom exceptions
    ├── router.py                       # Intelligent routing
    ├── caching.py                      # Response caching
    ├── cost_tracker.py                 # Cost tracking module
    ├── retry.py                        # Retry logic with backoff
    ├── embeddings.py                   # Embeddings module
    ├── vectordb.py                     # ChromaDB vector store
    ├── rag.py                          # RAG pipeline
    ├── chat/                           # Provider-specific chat modules
    │   ├── __init__.py                 # Package exports
    │   ├── builder.py                  # ChatBuilder for fluent configuration
    │   ├── stratifyai_openai.py        # OpenAI (model required)
    │   ├── stratifyai_anthropic.py     # Anthropic (model required)
    │   ├── stratifyai_google.py        # Google Gemini (model required)
    │   ├── stratifyai_deepseek.py      # DeepSeek (model required)
    │   ├── stratifyai_groq.py          # Groq (model required)
    │   ├── stratifyai_grok.py          # Grok (model required)
    │   ├── stratifyai_openrouter.py    # OpenRouter (model required)
    │   ├── stratifyai_ollama.py        # Ollama (model required)
    │   └── stratifyai_bedrock.py       # AWS Bedrock (model required)
    ├── providers/                      # Provider implementations
    │   ├── base.py                     # BaseProvider abstract class
    │   ├── openai.py                   # OpenAI implementation
    │   ├── anthropic.py                # Anthropic implementation
    │   ├── google.py                   # Google Gemini implementation
    │   ├── deepseek.py                 # DeepSeek implementation
    │   ├── groq.py                     # Groq implementation
    │   ├── grok.py                     # Grok (X.AI) implementation
    │   ├── openrouter.py               # OpenRouter implementation
    │   ├── ollama.py                   # Ollama local models
    │   └── bedrock.py                  # AWS Bedrock implementation
    └── utils/                          # Utility modules
        ├── provider_validator.py       # Provider model validation
        ├── token_counter.py            # Token counting
        ├── file_analyzer.py            # File type analysis
        ├── chunking.py                 # Smart text chunking
        └── extractors/                 # Schema extractors
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_example.py

# Run specific test
pytest tests/test_example.py::test_function_name
```

## Common Workflows

### Starting Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# [Additional setup steps]
```

### Adding Dependencies
```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

## Architecture Principles

**Design Principles:**
- **Abstraction First**: Hide provider-specific differences behind unified interface
- **Strategy Pattern**: Each provider implements common BaseProvider interface
- **Configuration-Driven**: Model catalogs, cost tables, capability matrices externalized
- **Fail-Safe**: Automatic retry with exponential backoff and fallback models
- **Cost-Aware**: Track every token and enforce budget limits

### Key Design Decisions
1. **Async-First Architecture**: All provider methods are async using native SDK async clients (AsyncOpenAI, AsyncAnthropic, aioboto3)
2. **Provider Strategy Pattern**: All providers inherit from BaseProvider abstract class, ensuring consistent interface
3. **OpenAI-Compatible Pattern**: Providers with OpenAI-compatible APIs (Gemini, DeepSeek, Groq, Grok, Ollama) share common base class
4. **Unified Message Format**: All providers use OpenAI-compatible message format internally
5. **Cost Tracking**: Every request calculates cost based on provider-specific pricing tables
6. **Type Safety**: Full type hints and dataclasses for all requests/responses
7. **Lazy Provider Loading**: Providers are instantiated on-demand, not at client initialization
8. **Router Independence**: Router is optional - core functionality works without it
9. **Sync Wrappers**: Convenience sync methods (`chat_sync()`, `chat_completion_sync()`) for CLI and simple scripts

## Project Status

**Current Phase:** Phase 7.10 - Catalog Modernization ✅  
**Progress:** Phases 1-6 + Phase 7.1-7.10 Complete  
**Latest Updates:** Phase 7.10 complete - JSON catalog, automated validation, enhanced validator, documentation (Feb 6, 2026)

### Completed Phases
- ✅ Phase 1: Core Implementation (100%)
  - BaseProvider abstract class
  - OpenAI provider with cost tracking
  - Unified LLMClient
  - Custom exception hierarchy
  - 32 unit tests passing
- ✅ Phase 2: Provider Expansion (100%)
  - Anthropic provider with Messages API
  - OpenAICompatibleProvider base class
  - Google, DeepSeek, Groq, Grok, Ollama, OpenRouter providers
  - 77 total tests passing
  - All 9 providers operational (added AWS Bedrock)
- ✅ Phase 3: Advanced Features (100%)
  - Enhanced streaming support
  - Cost tracking module with history
  - Retry logic with exponential backoff
  - Caching and logging decorators
  - Budget management system
- ✅ Phase 3.5: Web GUI (100%)
  - FastAPI REST API with endpoints
  - WebSocket streaming support
  - Interactive frontend interface
  - API documentation and tests
- ✅ Phase 4: Router and Optimization (100%)
  - Router with intelligent model selection
  - Complexity analysis algorithm
  - Cost/quality/latency/hybrid strategies
  - Fallback chain routing for resilient applications
  - Capability-based filtering (vision, tools, reasoning)
  - 33 router unit tests passing
- ✅ Phase 5: CLI Interface (100%)
  - Typer CLI framework with 5 commands
  - Rich formatting (tables, colors, progress)
  - Environment variable support
  - Interactive mode with conversation history
  - Router integration with --capability flag
  - Streaming without flicker
  - CLI usage documentation (445 lines)
- ✅ Phase 6: Production Readiness (100%)
  - Complete API documentation
  - 6 example applications
  - Performance optimization
  - Prompt caching system
  - PyPI package preparation
- ✅ Phase 7.1: Large File Handling - Token Estimation & Chunking (100%)
  - Token counting utility with tiktoken (186 lines)
  - File type analyzer with warnings (192 lines)
  - Smart chunking at natural boundaries (158 lines)
  - Progressive summarization (179 lines)
  - CLI integration (--chunked, --chunk-size flags)
  - 19 unit tests passing (16 passing, 3 skipped)
- ✅ Phase 7.2: Intelligent Extraction (100%)
  - CSV schema extractor (197 lines, 26-99% reduction)
  - JSON schema extractor (219 lines, 78-95% reduction)
  - Log error extractor (267 lines, 90% reduction)
  - Code structure extractor (327 lines, 33-80% reduction)
  - `analyze` CLI command
  - pandas dependency
  - 35 unit tests passing (100%)
- ✅ Phase 7.3: Model Auto-Selection (100%)
  - ModelSelector class for file-based selection (324 lines)
  - Router.route_for_extraction() method with quality prioritization
  - --auto-select flag in chat command
  - Auto-selection in analyze command (provider/model flags)
  - ExtractionMode enum (schema/errors/structure/summary)
  - 32 unit tests passing (100%)
  - CSV → Claude Sonnet, JSON → Claude Sonnet, Logs → DeepSeek Reasoner, Code → DeepSeek
- ✅ Phase 7.4: Enhanced Caching UI (100%)
  - Enhanced ResponseCache with hit/miss tracking and cost analytics
  - cache-stats command with --detailed flag for entry inspection
  - cache-clear command with confirmation prompt
  - Visual hit rate indicators (🎯 ≥75%, ⚠️ ≥50%, 📉 <50%)
  - Cost savings analysis showing total saved and average per hit
  - Top 10 cache entries table when --detailed flag used
  - 11 unit tests passing (100%)
- ✅ Interactive Mode Enhancements (100%)
  - Intelligent file extraction integrated into /file and /attach commands
  - Automatic schema extraction for large files (>500KB) with user prompt
  - /save command to export assistant responses with metadata
  - Smart default filenames with timestamps (response_provider_model_timestamp.md)
  - Full metadata in saved files (provider, model, tokens, cost, timestamp)
- ✅ Phase 7.5: RAG/Vector DB Integration (100%)
  - Embeddings module with OpenAI provider (236 lines)
  - Vector database module with ChromaDB (344 lines)
  - RAG pipeline with document indexing and querying (378 lines)
  - Semantic search with configurable top-k retrieval
  - Citation tracking for source attribution
  - Example script with 4 demonstrations (287 lines)
  - ChromaDB dependency integration
- ✅ Phase 7.6: Chat Package (100%)
  - Provider-specific chat modules (9 modules)
  - Simplified API: `chat(prompt)` and `chat_stream(prompt)`
  - Optional system prompt, temperature, max_tokens parameters
  - Lazy client initialization for efficiency
  - Package exports with convenient aliases (openai, anthropic, etc.)
- ✅ Phase 7.7: Async-First Conversion (100%)
  - All providers converted to async using native SDK clients
  - AsyncOpenAI, AsyncAnthropic for primary providers
  - aioboto3 for AWS Bedrock async support
  - AsyncIterator for streaming responses
  - Sync wrappers (chat_sync, chat_completion_sync) for convenience
  - Retry decorator updated for async with asyncio.sleep
  - Cache decorator updated for async functions
  - Embeddings and RAG modules converted to async
  - Chat package modules all async with sync wrappers
  - FastAPI endpoints using native async providers
  - pytest-asyncio configuration added
  - Latency tracking (latency_ms) added to ChatResponse
  - CLI displays latency in response metadata
- ✅ Phase 7.8: Builder Pattern & Required Model (100%)
  - ChatBuilder class for fluent configuration chaining
  - Builder methods: with_model(), with_system(), with_developer(), with_temperature(), with_max_tokens(), with_options()
  - Model parameter now required (no defaults) - explicit over implicit
  - All 9 chat modules updated to require model parameter
  - chat() raises ValueError if model not specified
  - 28 builder unit tests passing (tests/test_chat_builder.py)
  - 13 async operations tests passing (tests/test_async_operations.py)
- ✅ Phase 7.9: Web UI Enhancements (100%)
  - Vision support for image uploads (GPT-4o, Claude, Gemini, Nova)
  - Dynamic file input based on model vision capability
  - Smart chunking with configurable chunk size (10k-100k chars)
  - Markdown rendering with marked.js for assistant responses
  - Syntax highlighting with highlight.js (190+ languages)
  - Model metadata display (context window, validation status)
  - Category-based model grouping in dropdowns
  - Temperature auto-disable for reasoning models
- ✅ Phase 7.10: Catalog Modernization & Auto-Sync (100%)
  - Externalized model catalog to catalog/models.json (JSON format)
  - catalog_manager.py for loading/caching catalog with deprecation tracking
  - JSON schema validation (catalog/schema.json)
  - Community contribution guidelines (catalog/README.md)
  - Enhanced Anthropic validator using models.list() API
  - Automated catalog validation in CI (.github/workflows/validate-catalog.yml)
  - Deprecation fields (deprecated, deprecated_date, replacement_model)
  - All models use dated IDs (e.g., claude-3-haiku-20240307)
  - Fixed bug: Smart chunking 404 error (updated to real model)
  - Validation script (scripts/validate_catalog.py) with schema checks
  - 7 new files, 3 modified files, ~980 lines of infrastructure

### Current Focus (Week 7+: Feb 6+)
**Phase 7.10: Catalog Modernization** ✅ COMPLETE (Feb 6, 2026)
- ✅ JSON catalog infrastructure with community guidelines
- ✅ Automated validation and CI workflows
- ✅ Enhanced provider validator with API integration
- ✅ Fixed Anthropic chunking bug (404 error)
- ✅ Deprecation tracking system ready
- ✅ Documentation complete (AGENTS.md, README.md, developer-journal.md, CATALOG_MANAGEMENT.md)
- ⏳ UI deprecation warnings (optional enhancement)
- ⏳ Weekly auto-sync workflow (optional enhancement)

**Future Phases:**
- 📝 Phase 8: Production Deployment

### Implementation Phases
1. **Week 1 (Phase 1):** ✅ Core Implementation - BaseProvider, OpenAI, unified client
2. **Week 2 (Phase 2):** ✅ Provider Expansion - All 9 providers operational (added AWS Bedrock)
3. **Week 3 (Phase 3):** ✅ Advanced Features - Streaming, cost tracking, retry logic
4. **Week 4 (Phase 3.5):** ✅ Web GUI - FastAPI REST API, WebSocket streaming, frontend interface
5. **Week 5 (Phase 4):** ✅ Router and Optimization - Intelligent model selection
6. **Week 6 (Phase 5):** ✅ CLI Interface - Rich/Typer terminal interface (COMPLETE)
7. **Week 7 (Phase 6):** 📝 Production Readiness - Documentation, examples, PyPI package

### Next Steps (Immediate - Phase 8)
- 📝 Production deployment preparation
- 📝 PyPI package publishing
- 📝 Documentation finalization

### Future Work
- 📝 Phase 8: Production Deployment

## Documentation

### Core Documentation
- **README.md** - Project overview, setup instructions, and usage examples
- **docs/project-status.md** - Detailed 5-week timeline with phase breakdowns (25 working days)
- **docs/stratifyai-technical-approach.md** - Comprehensive technical design (1,232 lines)
- **docs/StratifyAI-Router-Logic.md** - Router strategies, fallback chains, and complexity analysis
- **docs/CATALOG_MANAGEMENT.md** - Community catalog contribution guide (459 lines)
- **docs/developer-journal.md** - Implementation log and lessons learned
- **AGENTS.md** - This file (AI agent guidance for development)

### Key Documentation Sections
- **Technical Approach**: Complete architecture, component design, provider implementations
- **Usage Examples**: Basic usage, streaming, cost tracking, retry with fallbacks
- **Implementation Roadmap**: 5 phases with detailed task breakdowns
- **Testing Strategy**: Unit tests, integration tests, mocking strategies

## Troubleshooting

### Common Issues

**Virtual Environment Not Found:**
```bash
# Recreate if .venv is missing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependency Issues:**
```bash
# Update pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Development Best Practices

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and single-purpose

### Git Practices
- Never commit `.env` files or credentials
- Use `.gitignore` for environment files
- Write descriptive commit messages
- Include co-author line: `Co-Authored-By: Warp <agent@warp.dev>`

## Git Commit Convention

Use conventional commit format: `type(scope): brief description`

### Commit Types
- **feat**: New feature or functionality
- **fix**: Bug fix
- **docs**: Documentation changes
- **refactor**: Code refactoring without functionality change
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, config, infrastructure)
- **perf**: Performance improvements
- **style**: Code style/formatting changes

### Project Scopes
- **core**: Core functionality
- **api**: API endpoints
- **ui**: User interface
- **data**: Data processing
- **docs**: Documentation
- **tests**: Testing
- **config**: Configuration

### Guidelines
- Keep first line under 72 characters
- Use imperative mood ("add" not "added")
- Always include: `Co-Authored-By: Warp <agent@warp.dev>`
- Scope is optional but recommended
- Reference issues when applicable: `fix(api): resolve connection issue (#123)`

## Technical Constraints

### Must Maintain
- Python 3.10+ compatibility
- Type hints on all functions and methods
- Consistent BaseProvider interface across all providers
- Cost tracking accuracy to $0.0001
- Response time < 2 seconds (p95)
- Test coverage > 80%

### Security Requirements
- Never commit secrets or credentials
- Use environment variables for API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- Validate all inputs to prevent injection attacks
- Sanitize error messages to avoid leaking API keys
- Use secure vaults for production API key management
- Implement rate limiting and budget enforcement

### Performance Targets
- Response time < 2 seconds (p95) for non-streaming requests
- Cold start < 1 second for provider initialization
- Memory usage < 100MB for client instance
- Cache hit rate > 30% with caching decorator enabled
- Cost reduction > 40% with cost-optimized routing

### Code Quality Standards
- Black formatting compliance (line length 88)
- Ruff linting compliance (all rules enabled)
- Mypy type checking passes with strict mode
- Docstrings on all public classes and methods (Google style)
- Unit test coverage > 80%
- Integration test coverage for all providers
