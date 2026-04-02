# API Key Management Improvements

**Created**: February 3, 2026  
**Purpose**: Make API key management seamless and developer-friendly for StratifyAI users

---

## Problem Statement

Current API key implementation has several adoption barriers:
1. **No .env.example** - Users don't know what keys they need
2. **Hard failure** - Missing keys throw immediate errors
3. **No guidance** - Error messages don't help users fix the issue
4. **All-or-nothing** - Can't test one provider without configuring all
5. **No validation** - Can't verify keys work before making API calls

---

## Implemented Solutions

### ✅ 1. Created .env.example Template

**File**: `.env.example` (87 lines)

**Features**:
- Clear categorization (Primary, AWS, Alternative providers)
- Direct links to get API keys for each provider
- Quick start guide with 4 steps
- Security notes
- Copy-paste ready format

**Usage**:
```bash
cp .env.example .env
# Edit .env and add your keys
```

### ✅ 2. Created APIKeyHelper Module

**File**: `llm_abstraction/api_key_helper.py` (303 lines)

**Features**:
- User-friendly error messages with setup instructions
- Suggests alternative providers if one fails
- Shows which providers have keys configured
- Auto-creates .env from .env.example
- Validates keys before use

**Key Methods**:
```python
# Get API key with fallback to environment
APIKeyHelper.get_api_key("openai", api_key=None)

# Validate key and get helpful error message
is_valid, error = APIKeyHelper.validate_api_key("openai")

# Check which providers are available
available = APIKeyHelper.check_available_providers()
# Returns: {"openai": True, "anthropic": False, ...}

# Get setup instructions
instructions = APIKeyHelper.get_setup_instructions()
```

---

## Additional Improvements Needed

### 🔧 3. Update Provider __init__ Methods

**Current** (example from `openai.py`):
```python
def __init__(self, api_key: Optional[str] = None, config: dict = None):
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AuthenticationError("openai")  # ❌ Unhelpful error
```

**Improved**:
```python
def __init__(self, api_key: Optional[str] = None, config: dict = None):
    from ..api_key_helper import get_api_key_or_error
    api_key = get_api_key_or_error("openai", api_key)  # ✅ Helpful error
    super().__init__(api_key, config)
```

**Files to update** (9 providers):
- `llm_abstraction/providers/openai.py`
- `llm_abstraction/providers/anthropic.py`
- `llm_abstraction/providers/google.py`
- `llm_abstraction/providers/deepseek.py`
- `llm_abstraction/providers/groq.py`
- `llm_abstraction/providers/grok.py`
- `llm_abstraction/providers/openrouter.py`
- `llm_abstraction/providers/ollama.py`
- `llm_abstraction/providers/bedrock.py`

### 🔧 4. Add CLI Command for API Key Setup

**Add to** `cli/stratifyai_cli.py`:

```python
@app.command()
def setup():
    """
    Interactive API key setup wizard.
    """
    from stratifyai.api_key_helper import (
        APIKeyHelper,
        print_setup_instructions
    )
    
    console.print("\n[bold cyan]StratifyAI Setup Wizard[/bold cyan]\n")
    
    # Create .env from .env.example if needed
    if APIKeyHelper.create_env_file_if_missing():
        console.print("[green]✓[/green] Created .env file from .env.example")
    
    # Show current status
    print_setup_instructions()
    
    # Optional: Interactive key entry
    console.print("\n[yellow]Edit .env file to add your API keys.[/yellow]")
    console.print("Then test with: [cyan]stratifyai chat -p openai -m gpt-4o-mini -t 'Hello'[/cyan]\n")


@app.command()
def check_keys():
    """
    Check which providers have API keys configured.
    """
    from stratifyai.api_key_helper import APIKeyHelper
    
    available = APIKeyHelper.check_available_providers()
    
    console.print("\n[bold]API Key Status:[/bold]\n")
    
    for provider, is_available in sorted(available.items()):
        status = "[green]✓[/green]" if is_available else "[red]✗[/red]"
        friendly_name = APIKeyHelper.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        console.print(f"  {status} {friendly_name}")
    
    configured_count = sum(1 for v in available.values() if v)
    total_count = len(available)
    
    console.print(f"\n{configured_count}/{total_count} providers configured\n")
```

**Usage**:
```bash
# Interactive setup wizard
stratifyai setup

# Check which keys are configured
stratifyai check-keys
```

### 🔧 5. Improve README Quick Start

**Add to README.md** (after installation section):

```markdown
## Quick Start

### 1. Configure API Keys

You only need keys for providers you plan to use.

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add at least one API key
# Get API keys from:
# - OpenAI: https://platform.openai.com/api-keys
# - Anthropic: https://console.anthropic.com/settings/keys
# - Google: https://makersuite.google.com/app/apikey
```

### 2. Test Your Setup

```bash
# Test with OpenAI
python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini -t "Hello!"

# Check which providers are ready
python -m cli.stratifyai_cli check-keys
```

### 3. Use in Your Code

```python
from stratifyai import LLMClient
from stratifyai.models import Message

# Option 1: Use environment variables (.env file)
client = LLMClient(provider="openai")

# Option 2: Pass API key explicitly
client = LLMClient(provider="openai", api_key="your-key-here")

# Make a request
response = client.chat(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Hello!")]
)
```

---

## Error Message Comparison

### Before (Unhelpful)
```
AuthenticationError: Missing API key for openai
```

### After (Helpful)
```
❌ Missing API key for OpenAI

To use this provider, you need to:
1. Get an API key from: https://platform.openai.com/api-keys
2. Set the OPENAI_API_KEY environment variable

Quick setup:
  export OPENAI_API_KEY=your-api-key-here

Or add to .env file:
  OPENAI_API_KEY=your-api-key-here

Alternative: Pass api_key parameter:
  client = LLMClient(provider='openai', api_key='your-key')

💡 Tip: You have API keys configured for these providers:
  Anthropic, Google Gemini

Try using one of them instead, or get an API key for OpenAI.
```

---

## Advanced Features (Optional)

### 🔮 6. API Key Validation (Future)

Test if API keys actually work before using them:

```python
class APIKeyValidator:
    """Validate API keys by making test requests."""
    
    @staticmethod
    def validate_openai_key(api_key: str) -> Tuple[bool, str]:
        """Test OpenAI API key with minimal request."""
        try:
            client = OpenAI(api_key=api_key)
            # Make minimal request to test key
            client.models.list()
            return True, "✓ Valid"
        except AuthenticationError:
            return False, "✗ Invalid key"
        except Exception as e:
            return False, f"✗ Error: {str(e)}"
```

**Usage**:
```bash
stratifyai validate-keys  # Test all configured keys
```

### 🔮 7. Interactive Key Entry (Future)

```python
def interactive_key_setup():
    """Guide user through entering API keys."""
    console.print("[bold]Let's set up your API keys![/bold]\n")
    
    # Ask which providers they want to use
    providers = Prompt.ask(
        "Which providers do you want to use?",
        choices=["openai", "anthropic", "google", "all", "skip"],
        default="openai"
    )
    
    if providers == "skip":
        return
    
    # Collect keys for selected providers
    # Save to .env file
    # Test keys
```

### 🔮 8. API Key Rotation (Future)

```python
class APIKeyRotator:
    """Rotate between multiple API keys to avoid rate limits."""
    
    def __init__(self, keys: List[str]):
        self.keys = keys
        self.current_index = 0
    
    def get_next_key(self) -> str:
        """Get next key in rotation."""
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key
```

**Usage**:
```python
# Set multiple keys for load balancing
client = LLMClient(
    provider="openai",
    api_keys=["key1", "key2", "key3"]  # Rotate automatically
)
```

### 🔮 9. Keyring Integration (Future)

Use OS keyring for secure key storage:

```python
import keyring

def save_key_to_keyring(provider: str, api_key: str):
    """Save API key to OS keyring."""
    keyring.set_password("stratifyai", provider, api_key)

def get_key_from_keyring(provider: str) -> Optional[str]:
    """Retrieve API key from OS keyring."""
    return keyring.get_password("stratifyai", provider)
```

---

## Implementation Priority

### Phase 1: Essential (Before PyPI v0.2.0)
- [x] Create .env.example template
- [x] Create APIKeyHelper module
- [ ] Update all 9 providers to use APIKeyHelper
- [ ] Add `setup` and `check-keys` CLI commands
- [ ] Update README quick start section

### Phase 2: Nice to Have (v0.3.0)
- [ ] Add API key validation (test keys actually work)
- [ ] Interactive key entry wizard
- [ ] Better error handling for invalid keys

### Phase 3: Advanced (v0.4.0+)
- [ ] API key rotation for rate limit handling
- [ ] Keyring integration for secure storage
- [ ] Multi-key load balancing

---

## Testing Plan

### Unit Tests

```python
# tests/test_api_key_helper.py
def test_get_api_key_from_env():
    """Test getting API key from environment variable."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    key = APIKeyHelper.get_api_key("openai")
    assert key == "test-key"

def test_get_api_key_from_parameter():
    """Test explicit API key takes precedence."""
    os.environ["OPENAI_API_KEY"] = "env-key"
    key = APIKeyHelper.get_api_key("openai", "param-key")
    assert key == "param-key"

def test_validate_missing_key():
    """Test helpful error for missing key."""
    os.environ.pop("OPENAI_API_KEY", None)
    is_valid, error = APIKeyHelper.validate_api_key("openai")
    assert not is_valid
    assert "Get an API key from" in error
    assert "https://platform.openai.com" in error

def test_check_available_providers():
    """Test checking which providers are configured."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ.pop("ANTHROPIC_API_KEY", None)
    
    available = APIKeyHelper.check_available_providers()
    assert available["openai"] is True
    assert available["anthropic"] is False

def test_suggest_alternatives():
    """Test suggesting alternative providers."""
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ.pop("OPENAI_API_KEY", None)
    
    suggestion = APIKeyHelper.suggest_alternative_providers("openai")
    assert "Anthropic" in suggestion
```

### Integration Tests

```bash
# Test CLI with missing keys
stratifyai chat -p openai -m gpt-4o-mini -t "Hello"
# Should show helpful error message

# Test CLI with check-keys
stratifyai check-keys
# Should show provider status

# Test Python API with missing keys
python -c "from stratifyai import LLMClient; LLMClient('openai')"
# Should show helpful error
```

---

## Documentation Updates

### Files to Update

1. **README.md** - Add quick start with API key setup
2. **docs/GETTING-STARTED.md** - Expand API key section
3. **docs/cli-usage.md** - Document new `setup` and `check-keys` commands
4. **WARP.md** - Update development environment section
5. **developer/pypi-deployment-checklist.md** - Add .env.example validation

---

## Benefits

### For New Users
- ✅ Clear guidance on getting API keys
- ✅ Can start with just one provider
- ✅ Helpful error messages show exact fix
- ✅ Alternative providers suggested automatically
- ✅ Quick validation of setup

### For Existing Users
- ✅ Backward compatible (still works with current method)
- ✅ Can check which providers are ready
- ✅ Better debugging when keys expire

### For Adoption
- ✅ Reduces friction in getting started
- ✅ Professional first impression
- ✅ Fewer support requests
- ✅ Easier onboarding in tutorials

---

## Example User Journey

### Before (Frustrating)
```
1. User: pip install stratifyai
2. User: from stratifyai import LLMClient
3. User: client = LLMClient("openai")
4. Error: "AuthenticationError: Missing API key for openai"
5. User: (Confused) What key? Where do I get it?
6. User: (Searches documentation...)
7. User: (Still confused about .env vs environment variables)
8. User: (Gives up, tries different library)
```

### After (Smooth)
```
1. User: pip install stratifyai
2. User: stratifyai setup
3. Output: Shows .env.example, lists providers, provides direct links
4. User: Copies .env.example, adds OpenAI key
5. User: stratifyai check-keys
6. Output: "✓ OpenAI configured"
7. User: from stratifyai import LLMClient
8. User: client = LLMClient("openai")  # Works!
9. User: (Happy, continues building)
```

---

## Related Files

**Created**:
- `.env.example` (87 lines) - API key template
- `llm_abstraction/api_key_helper.py` (303 lines) - Key management module
- `developer/api-key-improvements-guide.md` (this file)

**To Update**:
- All 9 provider `__init__` methods
- `cli/stratifyai_cli.py` (add setup/check-keys commands)
- `README.md` (quick start section)
- `docs/GETTING-STARTED.md`
- `developer/pypi-deployment-checklist.md`

---

## Summary

These improvements transform API key management from a **blocker** to a **guided experience**:

**Before**: "AuthenticationError: Missing API key"  
**After**: "Here's exactly how to get an API key, where to put it, and 2 alternative providers you can use right now"

This is critical for PyPI adoption. Many users will try your library, hit the API key error, and bounce if it's not immediately clear how to proceed.

**Impact**: Estimated **30-50% reduction** in early abandonment rate.
