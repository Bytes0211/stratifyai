# Contributing to StratifyAI

Thank you for your interest in contributing to StratifyAI! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Adding New Providers](#adding-new-providers)
- [Documentation](#documentation)
- [Questions and Support](#questions-and-support)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- Be respectful and considerate in all interactions
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences
- Accept responsibility and apologize for mistakes

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- API keys for at least one LLM provider (OpenAI, Anthropic, etc.)

### First Time Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/stratifyai.git
   cd stratifyai
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Or using `uv`:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e ".[dev,cli,web,rag]"
   ```

   Or with `uv`:
   ```bash
   uv pip install -e ".[dev,cli,web,rag]"
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

5. **Verify Setup**
   ```bash
   stratifyai check-keys
   pytest
   ```

---

## Development Setup

### Environment Variables

Add your API keys to `.env`:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=gsk_...
XAI_API_KEY=xai-...
OPENROUTER_API_KEY=sk-or-...
DEEPSEEK_API_KEY=sk-...
```

For AWS Bedrock, see the [AWS Bedrock Setup](#aws-bedrock-setup) section below.

### AWS Bedrock Setup

**Option 1: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

**Option 2: AWS Credentials File**
```bash
aws configure
# Or manually create ~/.aws/credentials
```

**Required Permissions:**
Your IAM user/role needs `bedrock:InvokeModel` permission.

### Development Tools

Install pre-commit hooks (optional but recommended):
```bash
pip install pre-commit
pre-commit install
```

---

## Project Structure

```
stratifyai/
├── stratifyai/              # Main package
│   ├── providers/          # Provider implementations
│   ├── chat/               # Simplified chat modules
│   ├── utils/              # Utilities (token counting, extraction)
│   ├── client.py           # Unified LLMClient
│   ├── models.py           # Data models
│   ├── config.py           # Model catalogs and cost tables
│   ├── router.py           # Intelligent routing
│   └── exceptions.py       # Custom exceptions
├── cli/                    # Typer CLI
├── api/                    # Optional FastAPI server
├── tests/                  # Test suite
├── examples/               # Usage examples
└── docs/                   # Documentation
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, well-documented code
- Follow the coding standards below
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=stratifyai --cov-report=html

# Run specific tests
pytest tests/test_specific.py -v
```

### 4. Code Quality Checks

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy stratifyai
```

### 5. Commit Changes

Follow the [Commit Message Guidelines](#commit-message-guidelines) below.

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Coding Standards

### Python Style

- **PEP 8 Compliance**: Follow PEP 8 guidelines
- **Line Length**: 88 characters (Black default)
- **Type Hints**: Required on all functions and methods
- **Docstrings**: Required on all public classes and methods (Google style)

### Type Hints Example

```python
from typing import Optional
from stratifyai.models import ChatRequest, ChatResponse

async def chat_completion(
    self,
    request: ChatRequest,
    timeout: Optional[int] = None
) -> ChatResponse:
    """
    Execute a chat completion request.
    
    Args:
        request: The chat completion request
        timeout: Optional timeout in seconds
        
    Returns:
        ChatResponse with content and metadata
        
    Raises:
        ProviderError: If the provider API call fails
    """
    pass
```

### Code Organization

- **Single Responsibility**: Each function/class should have one clear purpose
- **DRY Principle**: Don't repeat yourself - extract common logic
- **Abstract Base Classes**: Use for provider interfaces
- **Dataclasses**: Use for data models
- **Decorators**: Use for cross-cutting concerns (caching, retry, logging)

### Error Handling

```python
from stratifyai.exceptions import ProviderError, RateLimitError

try:
    response = await provider.chat_completion(request)
except RateLimitError as e:
    logger.warning(f"Rate limit hit: {e}")
    raise
except ProviderError as e:
    logger.error(f"Provider error: {e}")
    raise
```

---

## Testing

### Test Requirements

- **Coverage Target**: > 80% code coverage
- **Test Types**: Unit tests, integration tests (with mocks)
- **Async Tests**: Use `pytest-asyncio` for async code
- **Mocking**: Mock external API calls (don't hit real APIs in tests)

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from stratifyai.providers.openai import OpenAIProvider

@pytest.mark.asyncio
async def test_chat_completion():
    """Test basic chat completion."""
    provider = OpenAIProvider(api_key="test-key")
    
    # Mock the API call
    with patch.object(provider.client.chat.completions, 'create') as mock_create:
        mock_create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="Hello!"))],
            usage=AsyncMock(prompt_tokens=10, completion_tokens=5)
        )
        
        response = await provider.chat_completion(request)
        assert response.content == "Hello!"
```

### Running Tests

```bash
# All tests
pytest

# Verbose output
pytest -v

# Specific file
pytest tests/test_providers.py

# Specific test
pytest tests/test_providers.py::test_openai_chat

# With coverage
pytest --cov=stratifyai --cov-report=html

# Skip slow tests
pytest -m "not slow"
```

---

## Commit Message Guidelines

We follow **Conventional Commits** format:

```
type(scope): brief description

Longer description if needed.

Co-Authored-By: Warp <agent@warp.dev>
```

### Commit Types

- **feat**: New feature or functionality
- **fix**: Bug fix
- **docs**: Documentation changes
- **refactor**: Code refactoring without functionality change
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, config)
- **perf**: Performance improvements
- **style**: Code style/formatting changes

### Scopes

- **core**: Core functionality
- **providers**: Provider implementations
- **chat**: Chat package modules
- **router**: Routing logic
- **cli**: CLI interface
- **api**: API endpoints
- **rag**: RAG/vector DB features
- **utils**: Utility functions
- **tests**: Testing infrastructure
- **docs**: Documentation

### Examples

```bash
feat(providers): add support for Mistral AI provider

fix(router): resolve fallback chain infinite loop

docs(readme): update installation instructions

refactor(chat): extract common builder logic to base class

test(providers): add integration tests for all providers

chore(deps): update anthropic SDK to 0.20.0

Co-Authored-By: Warp <agent@warp.dev>
```

### Guidelines

- Keep first line under 72 characters
- Use imperative mood ("add" not "added")
- Reference issues when applicable: `fix(api): resolve #123`
- Always include: `Co-Authored-By: Warp <agent@warp.dev>`

---

## Pull Request Process

### Before Submitting

1. ✅ Tests pass: `pytest`
2. ✅ Code is formatted: `black .`
3. ✅ Linting passes: `ruff check .`
4. ✅ Type checking passes: `mypy stratifyai`
5. ✅ Documentation is updated
6. ✅ Commit messages follow conventions

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Bullet point list of changes

## Testing
- How was this tested?
- What test cases were added?

## Checklist
- [ ] Tests pass
- [ ] Code is formatted (black)
- [ ] Linting passes (ruff)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] Commit messages follow conventions
```

### Review Process

- Maintainers will review within 48 hours
- Address feedback and push updates
- PRs require at least one approval
- CI checks must pass before merging

---

## Adding New Providers

To add a new LLM provider:

### 1. Create Provider Class

Create `stratifyai/providers/your_provider.py`:

```python
from typing import Optional, AsyncIterator
from stratifyai.providers.base import BaseProvider
from stratifyai.models import ChatRequest, ChatResponse, StreamChunk

class YourProvider(BaseProvider):
    """Provider implementation for YourProvider."""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        # Initialize client
    
    async def chat_completion(
        self,
        request: ChatRequest
    ) -> ChatResponse:
        """Execute chat completion."""
        # Implementation
        pass
    
    async def chat_completion_stream(
        self,
        request: ChatRequest
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completion."""
        # Implementation
        pass
```

### 2. Update Configuration

Add to `stratifyai/config.py`:

```python
MODEL_CATALOG = {
    "your-model-id": {
        "provider": "yourprovider",
        "context_window": 128000,
        "supports_vision": False,
        "supports_tools": True,
        "cost_per_1m_input_tokens": 1.00,
        "cost_per_1m_output_tokens": 3.00,
    }
}
```

### 3. Create Chat Module

Create `stratifyai/chat/stratifyai_yourprovider.py`:

```python
from stratifyai.chat.builder import ChatBuilder

_builder: ChatBuilder | None = None

def with_model(model: str) -> ChatBuilder:
    """Configure model."""
    global _builder
    _builder = ChatBuilder(provider="yourprovider", model=model)
    return _builder

# Add other builder methods...
```

### 4. Add Tests

Create `tests/test_yourprovider.py` with unit and integration tests.

### 5. Update Documentation

- Add provider to README.md
- Update AGENTS.md with setup instructions
- Add example to `examples/`

---

## Documentation

### Documentation Standards

- **Docstrings**: Google style for all public APIs
- **README**: Keep examples up-to-date
- **AGENTS.md**: Update for new features and setup changes
- **Type Hints**: Required on all functions

### Example Docstring

```python
def route_for_complexity(
    self,
    prompt: str,
    strategy: str = "hybrid"
) -> str:
    """
    Route request based on prompt complexity.
    
    Args:
        prompt: The user's input prompt
        strategy: Routing strategy (cost, quality, latency, hybrid)
        
    Returns:
        Selected model ID
        
    Raises:
        ValueError: If strategy is invalid
        
    Example:
        >>> router = Router()
        >>> model = router.route_for_complexity("Hello", strategy="cost")
        >>> print(model)
        'gpt-4o-mini'
    """
    pass
```

---

## Questions and Support

### Getting Help

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Documentation**: Check `docs/` folder for detailed guides

### Reporting Bugs

Include:
- Python version
- StratifyAI version
- Provider(s) used
- Minimal reproducible example
- Error message and stack trace

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Example API or usage pattern
- Willingness to contribute implementation

---

## License

By contributing to StratifyAI, you agree that your contributions will be licensed under the project's license (MIT).

---

Thank you for contributing to StratifyAI! 🚀
