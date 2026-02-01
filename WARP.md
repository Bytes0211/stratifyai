# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

StratumAI is a production-ready Python module that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama) through a consistent API. The project demonstrates advanced API abstraction, design patterns (strategy, factory), multi-provider integration, production engineering (error handling, retry logic, cost tracking), and Python best practices (type hints, abstract base classes, decorators).

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

## Project Structure

```txt
stratumai/
├── README.md
├── WARP.md                # This file (development guidance)
├── requirements.txt       # Python dependencies
├── .venv/                 # Virtual environment
├── docs/
│   ├── project-status.md              # 5-week timeline with detailed phases
│   └── stratumai-technical-approach.md # Comprehensive technical design (1,232 lines)
└── llm_abstraction/                    # Main package (to be implemented)
    ├── __init__.py
    ├── client.py                       # Unified LLMClient
    ├── models.py                       # Data models (Message, ChatRequest, ChatResponse)
    ├── config.py                       # Model catalogs and cost tables
    ├── exceptions.py                   # Custom exceptions
    ├── utils.py                        # Helper functions
    ├── router.py                       # Intelligent routing
    └── providers/
        ├── base.py                     # BaseProvider abstract class
        ├── openai.py                   # OpenAI implementation
        ├── anthropic.py                # Anthropic implementation
        ├── google.py                   # Google Gemini implementation
        ├── deepseek.py                 # DeepSeek implementation
        ├── groq.py                     # Groq implementation
        ├── grok.py                     # Grok (X.AI) implementation
        ├── openrouter.py               # OpenRouter implementation
        └── ollama.py                   # Ollama local models
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
1. **Provider Strategy Pattern**: All providers inherit from BaseProvider abstract class, ensuring consistent interface
2. **OpenAI-Compatible Pattern**: Providers with OpenAI-compatible APIs (Gemini, DeepSeek, Groq, Grok, Ollama) share common base class
3. **Unified Message Format**: All providers use OpenAI-compatible message format internally
4. **Cost Tracking**: Every request calculates cost based on provider-specific pricing tables
5. **Type Safety**: Full type hints and dataclasses for all requests/responses
6. **Lazy Provider Loading**: Providers are instantiated on-demand, not at client initialization
7. **Router Independence**: Router is optional - core functionality works without it

## Project Status

**Current Phase:** Phase 4 - Complete ✅  
**Progress:** 76% Complete (26 of 34 tasks)  
**Latest Updates:** Phase 4 complete - Router operational (Feb 1, 2026)

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
  - All 8 providers operational
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
  - 33 router unit tests passing

### Current Focus (Week 4: Feb 1 - Feb 5)
**Phase 5: CLI Interface (Rich/Typer)**
- 📝 Typer CLI framework setup
- 📝 Core commands (chat, models, providers, route)
- 📝 Interactive mode with conversation history
- 📝 Rich formatting (tables, colors, streaming)

### Implementation Phases
1. **Week 1 (Phase 1):** ✅ Core Implementation - BaseProvider, OpenAI, unified client
2. **Week 2 (Phase 2):** ✅ Provider Expansion - All 8 providers operational
3. **Week 3 (Phase 3):** ✅ Advanced Features - Streaming, cost tracking, retry logic
4. **Week 4 (Phase 3.5):** ✅ Web GUI - FastAPI REST API, WebSocket streaming, frontend interface
5. **Week 5 (Phase 4):** ✅ Router and Optimization - Intelligent model selection
6. **Week 6 (Phase 5):** 📝 CLI Interface - Rich/Typer terminal interface
7. **Week 7 (Phase 6):** 📝 Production Readiness - Documentation, examples, PyPI package

### Next Steps (Immediate)
- 📝 Install typer[all] dependency
- 📝 Create cli/stratumai_cli.py with Typer framework
- 📝 Implement core commands: chat, models, providers
- 📝 Add router integration with route command
- 📝 Build interactive mode with conversation loop
- 📝 Apply Rich formatting for tables and output
- 📝 Test streaming output without flicker
- 📝 Document CLI usage and examples

## Documentation

### Core Documentation
- **README.md** - Project overview, setup instructions, and usage examples
- **docs/project-status.md** - Detailed 5-week timeline with phase breakdowns (25 working days)
- **docs/stratumai-technical-approach.md** - Comprehensive technical design (1,232 lines)
- **WARP.md** - This file (development environment guidance for Warp AI)

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
