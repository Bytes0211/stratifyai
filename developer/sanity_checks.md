# StratifyAI Development Sanity Checks

**Project:** StratifyAI - Unified LLM Provider Abstraction  
**Created:** January 30, 2026  
**Purpose:** Quick validation commands to verify latest commits and implementation progress

---

## Quick Health Check (Run All)

```bash
# Run all checks in sequence
echo "=== Python Environment ==="
python3 --version
source .venv/bin/activate 2>/dev/null && echo "Virtual environment: ACTIVE" || echo "Virtual environment: INACTIVE"

echo -e "\n=== Dependencies ==="
pip list | grep -E "(openai|anthropic|google|requests)"

echo -e "\n=== Core Module Files ==="
ls -lh llm_abstraction/*.py 2>/dev/null | awk '{print $9, $5}' || echo "Module not found"

echo -e "\n=== Provider Implementations ==="
ls -lh llm_abstraction/providers/*.py 2>/dev/null | awk '{print $9, $5}' || echo "Providers not found"

echo -e "\n=== Test Files ==="
ls -lh tests/test_*.py 2>/dev/null | awk '{print $9, $5}' || echo "Tests not found"

echo -e "\n=== Recent Commits ==="
git --no-pager log --oneline -5

echo -e "\n=== Git Status ==="
git status --short
```

---

## 1. Virtual Environment

### Check if virtual environment exists
```bash
test -d .venv && echo "✅ Virtual environment exists" || echo "❌ Virtual environment missing"
```

**Expected Output:**
```
✅ Virtual environment exists
```

### Verify activation
```bash
source .venv/bin/activate && python -c "import sys; print('✅ Using:', sys.prefix)"
```

**Expected Output:**
```
✅ Using: /home/scotton/dev/projects/stratifyai/.venv
```

### Check Python version
```bash
python3 --version
```

**Expected Output:**
```
Python 3.10.x or higher
```

---

## 2. Dependencies

### List installed packages
```bash
pip list | grep -E "(openai|anthropic|google|requests|pytest)"
```

**Expected Packages:**
- `openai` (>= 1.0.0)
- `anthropic` (>= 0.18.0)
- `google-generativeai` (>= 0.3.0)
- `requests` (>= 2.31.0)
- `pytest` (>= 7.4.0)

### Verify requirements.txt sync
```bash
pip check
```

**Expected Output:**
```
No broken requirements found.
```

### Check for missing dependencies
```bash
python -c "
import sys
try:
    import openai
    print('✅ openai installed')
except ImportError:
    print('❌ openai missing')
"
```

---

## 3. Core Module Files

### List core module files
```bash
ls -lh llm_abstraction/*.py
```

**Expected Files:**
- `__init__.py` - Package initialization
- `client.py` - LLMClient unified interface
- `models.py` - Message, ChatRequest, ChatResponse, Usage
- `config.py` - Model catalogs and cost tables
- `exceptions.py` - Custom exception hierarchy
- `caching.py` - Response caching implementation (if Phase 3)

**Status:** ✅ Phase 1 should have all except caching.py

### Check core imports
```bash
python -c "
from stratifyai.client import LLMClient
from stratifyai.models import Message, ChatRequest, ChatResponse
from stratifyai.config import MODEL_CATALOG
from stratifyai.exceptions import ProviderError, ModelNotFoundError
print('✅ All core imports successful')
"
```

---

## 4. Provider Implementations

### List provider files
```bash
ls -lh llm_abstraction/providers/*.py
```

**Expected Providers (by phase):**

**Phase 1 (Week 1):**
- `base.py` - BaseProvider abstract class
- `openai.py` - OpenAI implementation

**Phase 2 (Week 2):**
- `anthropic.py` - Anthropic Claude
- `google.py` - Google Gemini
- `deepseek.py` - DeepSeek
- `groq.py` - Groq
- `grok.py` - Grok (X.AI)
- `openrouter.py` - OpenRouter
- `ollama.py` - Ollama local models

### Check provider imports
```bash
python -c "
from stratifyai.providers.base import BaseProvider
from stratifyai.providers.openai import OpenAIProvider
print('✅ Provider imports successful')
"
```

### Verify BaseProvider interface
```bash
python -c "
from stratifyai.providers.base import BaseProvider
import inspect
methods = [m for m in dir(BaseProvider) if not m.startswith('_')]
print('BaseProvider methods:', methods)
"
```

**Expected Methods:**
- `chat` - Core chat completion method
- `validate_model` - Model validation
- `calculate_cost` - Cost calculation

---

## 5. Data Models

### Verify model classes exist
```bash
python -c "
from stratifyai.models import Message, ChatRequest, ChatResponse, Usage
from dataclasses import fields

print('Message fields:', [f.name for f in fields(Message)])
print('ChatRequest fields:', [f.name for f in fields(ChatRequest)])
print('ChatResponse fields:', [f.name for f in fields(ChatResponse)])
print('Usage fields:', [f.name for f in fields(Usage)])
"
```

**Expected Output:**
```
Message fields: ['role', 'content']
ChatRequest fields: ['model', 'messages', 'temperature', 'max_tokens', 'stream']
ChatResponse fields: ['id', 'model', 'message', 'usage', 'created_at']
Usage fields: ['prompt_tokens', 'completion_tokens', 'total_tokens']
```

### Test model instantiation
```bash
python -c "
from stratifyai.models import Message, ChatRequest

msg = Message(role='user', content='Hello')
req = ChatRequest(model='gpt-4', messages=[msg])
print('✅ Model instantiation successful')
print(f'   Message: {msg}')
print(f'   Request model: {req.model}')
"
```

---

## 6. Configuration

### Check model catalog
```bash
python -c "
from stratifyai.config import MODEL_CATALOG
providers = list(MODEL_CATALOG.keys())
print('Configured providers:', providers)
for provider in providers:
    models = list(MODEL_CATALOG[provider].keys())
    print(f'  {provider}: {len(models)} models')
"
```

**Expected Providers (Phase 1):**
- `openai` - GPT models

**Expected Providers (Phase 2+):**
- `openai`, `anthropic`, `google`, `deepseek`, `groq`, `grok`, `openrouter`, `ollama`

### Verify cost tables
```bash
python -c "
from stratifyai.config import MODEL_CATALOG
# Check OpenAI GPT-4 pricing
if 'openai' in MODEL_CATALOG and 'gpt-4' in MODEL_CATALOG['openai']:
    gpt4 = MODEL_CATALOG['openai']['gpt-4']
    print(f'GPT-4 pricing: ${gpt4[\"cost_per_1k_prompt_tokens\"]}/1K prompt, ${gpt4[\"cost_per_1k_completion_tokens\"]}/1K completion')
else:
    print('⚠️ GPT-4 not in catalog yet')
"
```

---

## 7. Custom Exceptions

### List custom exceptions
```bash
python -c "
from stratifyai import exceptions
import inspect

exc_classes = [name for name, obj in inspect.getmembers(exceptions) 
               if inspect.isclass(obj) and issubclass(obj, Exception)]
print('Custom exceptions:', exc_classes)
"
```

**Expected Exceptions:**
- `LLMAbstractionError` - Base exception
- `ProviderError` - Provider-specific errors
- `ModelNotFoundError` - Model not in catalog
- `APIKeyMissingError` - Missing API credentials
- `RateLimitError` - Rate limit exceeded
- `CostLimitExceededError` - Budget exceeded
- `ValidationError` - Input validation failed

### Test exception hierarchy
```bash
python -c "
from stratifyai.exceptions import ProviderError, ModelNotFoundError, LLMAbstractionError

assert issubclass(ProviderError, LLMAbstractionError)
assert issubclass(ModelNotFoundError, LLMAbstractionError)
print('✅ Exception hierarchy correct')
"
```

---

## 8. LLMClient

### Verify client instantiation
```bash
python -c "
from stratifyai.client import LLMClient
import os

# Mock API key for instantiation test
os.environ['OPENAI_API_KEY'] = 'test-key'
client = LLMClient()
print('✅ LLMClient instantiation successful')
"
```

### Check available methods
```bash
python -c "
from stratifyai.client import LLMClient
import inspect

methods = [m for m, _ in inspect.getmembers(LLMClient, predicate=inspect.isfunction) 
           if not m.startswith('_')]
print('LLMClient methods:', methods)
"
```

**Expected Methods:**
- `chat` - Unified chat completion
- `list_models` - List available models
- `get_model_info` - Get model details
- `calculate_cost` - Cost estimation (Phase 3)
- `set_budget` - Budget management (Phase 3)

---

## 9. Tests

### List test files
```bash
ls -lh tests/test_*.py
```

**Expected Test Files:**
- `test_models.py` - Data model tests
- `test_client.py` - LLMClient tests
- `test_openai_provider.py` - OpenAI provider tests
- `test_anthropic_provider.py` - Anthropic tests (Phase 2)
- `test_caching.py` - Caching tests (Phase 3)

### Run all tests
```bash
pytest -v
```

**Expected Output:**
```
tests/test_models.py::test_message_creation PASSED
tests/test_models.py::test_chat_request_validation PASSED
tests/test_client.py::test_client_initialization PASSED
tests/test_openai_provider.py::test_openai_chat PASSED
...
========== X passed in Y.YYs ==========
```

### Run specific test file
```bash
pytest tests/test_models.py -v
```

### Run with coverage
```bash
pytest --cov=llm_abstraction --cov-report=term-missing
```

**Expected Coverage:** > 80%

### Check for test failures
```bash
pytest --tb=short 2>&1 | grep -E "(FAILED|ERROR)" || echo "✅ All tests passing"
```

---

## 10. Git Status

### Check current branch
```bash
git branch --show-current
```

**Expected Output:**
```
main
```

### View recent commits
```bash
git --no-pager log --oneline -10
```

**Expected Recent Commits:**
- Phase 1 Day 1: `docs: initial commit`
- Phase 1 Day 2: `feat(providers): implement BaseProvider abstract class`
- Phase 1 Day 3: `feat(providers): implement OpenAI provider`
- Phase 1 Day 4: `feat(client): implement unified LLMClient`
- Phase 1 Day 5: `test: add unit tests for core components`

### Check for uncommitted changes
```bash
git status --short
```

**Expected Output (clean state):**
```
(empty output - no uncommitted changes)
```

### Verify last commit message format
```bash
git --no-pager log -1 --pretty=format:"Type: %s%nAuthor: %an%nDate: %ad%n%b"
```

**Expected Format:**
- Follows conventional commits: `type(scope): description`
- Includes co-author: `Co-Authored-By: Warp <agent@warp.dev>`

---

## 11. Code Quality

### Run type checking (if mypy installed)
```bash
mypy llm_abstraction/ --strict 2>&1 | tail -1
```

**Expected Output:**
```
Success: no issues found in X source files
```

### Check code formatting (if ruff installed)
```bash
ruff format --check stratifyai/ cli/ api/ tests/ 2>&1 | tail -1
```

**Expected Output:**
```
N files already formatted
```

### Run linting (if ruff installed)
```bash
ruff check llm_abstraction/ tests/
```

**Expected Output:**
```
All checks passed!
```

---

## 12. OpenAI Provider Integration

### Verify OpenAI provider without API call
```bash
python -c "
from stratifyai.providers.openai import OpenAIProvider
import os

os.environ['OPENAI_API_KEY'] = 'test-key'
provider = OpenAIProvider()
print('✅ OpenAI provider instantiation successful')
print(f'   Supported models: {provider.supported_models[:3]}...')
"
```

### Test with mock API key
```bash
python -c "
from stratifyai.client import LLMClient
from stratifyai.models import Message
import os

os.environ['OPENAI_API_KEY'] = 'test-key'
client = LLMClient()
print('✅ Client ready for OpenAI')
"
```

---

## 13. Cost Tracking (Phase 3)

### Check cost calculation implementation
```bash
python -c "
from stratifyai.config import MODEL_CATALOG

# Verify cost tables exist
if 'openai' in MODEL_CATALOG:
    for model, config in MODEL_CATALOG['openai'].items():
        if 'cost_per_1k_prompt_tokens' in config:
            print(f'✅ {model}: Cost tracking enabled')
        else:
            print(f'⚠️ {model}: Cost tracking missing')
"
```

### Test cost calculation
```bash
python -c "
from stratifyai.client import LLMClient
import os

os.environ['OPENAI_API_KEY'] = 'test-key'
client = LLMClient()

# Test if calculate_cost method exists
if hasattr(client, 'calculate_cost'):
    print('✅ Cost calculation available')
else:
    print('⚠️ Cost calculation not yet implemented (expected for Phase 3)')
"
```

---

## 14. Caching Implementation (Phase 3)

### Check if caching module exists
```bash
test -f llm_abstraction/caching.py && echo "✅ Caching module exists" || echo "⚠️ Caching not yet implemented (expected for Phase 3)"
```

### Verify caching functionality
```bash
python -c "
try:
    from stratifyai.caching import ResponseCache
    print('✅ Caching implementation available')
except ImportError:
    print('⚠️ Caching not yet implemented (expected for Phase 3)')
"
```

---

## 15. Comprehensive Validation Script

Save this as `validate_stratifyai.sh`:

```bash
#!/bin/bash

# StratifyAI Development Validation Script
# Version: 1.0
# Date: January 30, 2026

set -e

echo "======================================"
echo "StratifyAI Development Validation"
echo "======================================"
echo "Date: $(date)"
echo "Python: $(python3 --version)"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_resource() {
  local name=$1
  local command=$2
  
  echo -n "Checking $name... "
  if eval $command >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
    return 0
  else
    echo -e "${RED}FAILED${NC}"
    return 1
  fi
}

# 1. Virtual Environment
echo "=== Virtual Environment ==="
check_resource "Virtual environment exists" "test -d .venv"
check_resource "Python executable" "test -f .venv/bin/python"
echo ""

# 2. Core Module Files
echo "=== Core Module Files ==="
check_resource "client.py" "test -f llm_abstraction/client.py"
check_resource "models.py" "test -f llm_abstraction/models.py"
check_resource "config.py" "test -f llm_abstraction/config.py"
check_resource "exceptions.py" "test -f llm_abstraction/exceptions.py"
echo ""

# 3. Provider Files
echo "=== Provider Files ==="
check_resource "base.py" "test -f llm_abstraction/providers/base.py"
check_resource "openai.py" "test -f llm_abstraction/providers/openai.py"
echo ""

# 4. Test Files
echo "=== Test Files ==="
check_resource "test_models.py" "test -f tests/test_models.py"
check_resource "test_client.py" "test -f tests/test_client.py"
check_resource "test_openai_provider.py" "test -f tests/test_openai_provider.py"
echo ""

# 5. Python Imports
echo "=== Python Imports ==="
source .venv/bin/activate 2>/dev/null || true
check_resource "Core imports" "python -c 'from stratifyai.client import LLMClient'"
check_resource "Model imports" "python -c 'from stratifyai.models import Message, ChatRequest'"
check_resource "Provider imports" "python -c 'from stratifyai.providers.base import BaseProvider'"
echo ""

# 6. Tests
echo "=== Running Tests ==="
if command -v pytest &> /dev/null; then
  echo -n "Running pytest... "
  if pytest -q 2>&1 | tail -1 | grep -q "passed"; then
    echo -e "${GREEN}OK${NC}"
  else
    echo -e "${YELLOW}SOME FAILURES${NC}"
  fi
else
  echo -e "${YELLOW}pytest not installed${NC}"
fi
echo ""

# 7. Git Status
echo "=== Git Status ==="
echo "Branch: $(git branch --show-current)"
echo "Last commit: $(git --no-pager log -1 --oneline)"
uncommitted=$(git status --short | wc -l)
if [ "$uncommitted" -eq 0 ]; then
  echo -e "Working tree: ${GREEN}CLEAN${NC}"
else
  echo -e "Working tree: ${YELLOW}$uncommitted uncommitted changes${NC}"
fi
echo ""

echo "======================================"
echo "Validation Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "- ${GREEN}OK${NC} = Component ready"
echo "- ${YELLOW}WARNING${NC} = Component exists but needs review"
echo "- ${RED}FAILED${NC} = Component missing"
echo ""
echo "Next steps:"
echo "  pytest -v              # Run all tests"
echo "  python main.py         # Run example"
echo "  git status             # Check for uncommitted changes"
```

**Usage:**
```bash
chmod +x validate_stratifyai.sh
./validate_stratifyai.sh
```

---

## 16. Quick Troubleshooting Commands

### Recreate virtual environment
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fix import errors
```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Check for circular imports
```bash
python -c "import stratifyai" && echo "✅ No circular imports" || echo "❌ Circular import detected"
```

### Verify API keys (without exposing values)
```bash
env | grep -E "(OPENAI|ANTHROPIC|GOOGLE)_API_KEY" | sed 's/=.*/=***REDACTED***/'
```

### Clear pytest cache
```bash
rm -rf .pytest_cache __pycache__ tests/__pycache__ llm_abstraction/__pycache__
```

### Check file permissions
```bash
ls -la llm_abstraction/*.py | awk '{print $1, $9}'
```

---

## Expected Results Summary

**Phase 1 - Week 1 (Jan 30 - Feb 5):**
- ✅ Day 1: Project setup + technical design
- ✅ Day 2: BaseProvider abstract class
- ✅ Day 3: OpenAI provider implementation
- ✅ Day 4: LLMClient unified interface
- ✅ Day 5: Error handling + unit tests

**Phase 2 - Week 2 (Feb 6 - Feb 12):**
- 📝 All 8 providers operational (Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama)
- 📝 Provider integration tests
- 📝 Model catalog complete

**Phase 3 - Week 3 (Feb 13 - Feb 19):**
- 📝 Streaming support
- 📝 Cost tracking
- 📝 Retry logic with fallbacks
- 📝 Response caching

**Phase 4 - Week 4 (Feb 20 - Feb 26):**
- 📝 Intelligent router
- 📝 Cost-optimized routing
- 📝 Performance benchmarks

**Phase 5 - Week 5 (Feb 27 - Mar 5):**
- 📝 Documentation complete
- 📝 Usage examples
- 📝 PyPI package ready

---

## Notes

- **Python Version:** Requires Python 3.10+
- **Dependencies:** Use `pip install -r requirements.txt` to install
- **API Keys:** Store in `.env` file (never commit!)
- **Testing:** Run `pytest -v` for verbose test output
- **Coverage:** Target > 80% test coverage
- **Cost:** All validation commands are free (no API calls)

---

**Document Version:** 1.0  
**Created:** January 30, 2026  
**Last Updated:** January 30, 2026  
**Author:** scotton  
**Project:** StratifyAI - Unified LLM Provider Abstraction  
**Status:** Phase 1 Week 1 - Core Implementation In Progress
