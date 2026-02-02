# StratumAI Local Installation Guide

This guide provides step-by-step instructions for installing StratumAI as a local Python library/package for development and use in other projects.

## Table of Contents
- [Installation Methods](#installation-methods)
- [Method 1: Editable Install (Recommended for Development)](#method-1-editable-install-recommended-for-development)
- [Method 2: Local Package Install](#method-2-local-package-install)
- [Method 3: Build and Install as Wheel](#method-3-build-and-install-as-wheel)
- [Verification](#verification)
- [Usage Examples](#usage-examples)
- [Uninstallation](#uninstallation)
- [Troubleshooting](#troubleshooting)

---

## Installation Methods

There are three primary methods to install StratumAI locally:

1. **Editable Install** - Best for active development (changes are reflected immediately)
2. **Local Package Install** - Standard installation from local directory
3. **Wheel Build & Install** - Production-like installation from distribution file

---

## Method 1: Editable Install (Recommended for Development)

This method installs the package in "editable" mode, meaning code changes are immediately reflected without reinstalling.

### Prerequisites

```bash
# Ensure you have Python 3.10+ installed
python3 --version

# Ensure pip is up to date
python3 -m pip install --upgrade pip
```

### Step 1: Navigate to Project Directory

```bash
cd /home/scotton/dev/projects/stratumai
```

### Step 2: Create/Activate Virtual Environment (Recommended)

```bash
# Create virtual environment (if not already created)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### Step 3: Install in Editable Mode

```bash
# Install package in editable mode with all dependencies
pip install -e .

# OR with development dependencies (includes testing tools)
pip install -e ".[dev]"
```

### Step 4: Verify Installation

```bash
# Check that stratumai is installed
pip show stratumai

# Test import
python -c "from llm_abstraction import LLMClient; print('Success!')"

# Test CLI
stratumai --help
```

### Benefits of Editable Install
- Code changes take effect immediately (no reinstall needed)
- Perfect for active development and testing
- Easy to debug and iterate
- Can work on multiple projects using the same local package

---

## Method 2: Local Package Install

This method installs the package normally from the local directory.

### Step 1: Navigate to Project Directory

```bash
cd /home/scotton/dev/projects/stratumai
```

### Step 2: Create/Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Package

```bash
# Install from current directory
pip install .

# OR with specific extras
pip install ".[dev]"
```

### Step 4: Verify Installation

```bash
pip show stratumai
python -c "from llm_abstraction import LLMClient; print('Success!')"
```

### Note
With this method, you need to reinstall after making code changes:
```bash
pip install --upgrade --force-reinstall .
```

---

## Method 3: Build and Install as Wheel

This method creates a distribution file (.whl) that can be installed or shared.

### Step 1: Install Build Tools

```bash
cd /home/scotton/dev/projects/stratumai
source .venv/bin/activate

# Install build tools
pip install build
```

### Step 2: Build the Package

```bash
# Build wheel and source distribution
python -m build

# This creates files in dist/:
# - stratumai-0.1.0-py3-none-any.whl
# - stratumai-0.1.0.tar.gz
```

### Step 3: Install the Wheel

```bash
# Install the built wheel
pip install dist/stratumai-0.1.0-py3-none-any.whl

# OR install in another environment/project
# (from outside the stratumai directory)
pip install /home/scotton/dev/projects/stratumai/dist/stratumai-0.1.0-py3-none-any.whl
```

### Step 4: Verify Installation

```bash
pip show stratumai
stratumai --help
```

### Benefits of Wheel Install
- Creates portable distribution file
- Can install in multiple environments
- Production-ready installation
- Can share with others (though not on PyPI yet)

---

## Verification

After installation (any method), verify everything works:

### 1. Check Package Installation

```bash
pip show stratumai
```

Expected output:
```
Name: stratumai
Version: 0.1.0
Summary: Unified LLM abstraction layer for 8 providers
Home-page: https://github.com/yourusername/stratumai
Author: Your Name
Author-email: your.email@example.com
Location: /home/scotton/dev/projects/stratumai
Requires: anthropic, google-generativeai, httpx, openai, python-dotenv, rich, typer
```

### 2. Test Python Import

```bash
python3 << 'EOF'
from llm_abstraction import LLMClient, ChatRequest, Message
from llm_abstraction.router import Router, RoutingStrategy

# Test client initialization
client = LLMClient()
print("✓ LLMClient imported successfully")

# Test router
router = Router()
print("✓ Router imported successfully")

# List supported providers
providers = LLMClient.get_supported_providers()
print(f"✓ Supported providers: {', '.join(providers)}")
EOF
```

### 3. Test CLI Commands

```bash
# Test CLI installation
stratumai --help

# List providers
stratumai providers

# List models
stratumai models

# Test cache stats
stratumai cache-stats
```

### 4. Run Unit Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_client.py -v

# Run CLI tests
pytest tests/test_cli_chat.py -v
```

---

## Usage Examples

### Using StratumAI in Your Python Projects

Once installed, you can use StratumAI in any Python project:

#### Example 1: Basic Usage

```python
# your_project/main.py
from llm_abstraction import LLMClient, ChatRequest, Message

# Initialize client
client = LLMClient(provider="openai")

# Create request
request = ChatRequest(
    model="gpt-4.1-mini",
    messages=[
        Message(role="user", content="Explain quantum computing in one sentence")
    ]
)

# Get response
response = client.chat_completion(request)
print(response.content)
print(f"Cost: ${response.usage.cost_usd:.6f}")
```

#### Example 2: Using the Router

```python
# your_project/router.py
# As defined in local-installation-guide.md - Example 2
# Use Router with cost optimization and auto model selection

from dotenv import load_dotenv
from llm_abstraction import Message
from llm_abstraction.router import Router, RoutingStrategy

# Load environment variables from .env file
load_dotenv()

# Create router with cost-optimized strategy
router = Router(strategy=RoutingStrategy.COST)

# Let router select best model
messages = [Message(role="user", content="What is the capital of France?")]
provider, model = router.route(messages)

print(f"Selected: {provider}/{model}")

# Get response
response = client.chat_completion(request)
print(response.content)
print(f"Cost: ${response.usage.cost_usd:.6f}")
```

#### Example 3: Multi-Provider Comparison

```python
from dotenv import load_dotenv
from llm_abstraction import LLMClient, ChatRequest, Message

# Load environment variables from .env file
load_dotenv()

providers = ["openai", "anthropic", "google"]
messages = [Message(role="user", content="Write a haiku about Python")]

for provider in providers:
    client = LLMClient(provider=provider)
    
    # Get default model for provider
    models = LLMClient.get_supported_models(provider=provider)
    
    request = ChatRequest(model=models[0], messages=messages)
    response = client.chat_completion(request)
    
    print(f"\n{provider.upper()}:")
    print(response.content)
    print(f"Cost: ${response.usage.cost_usd:.6f}")
```

#### Example 4: Using the CLI

The StratumAI CLI provides a rich terminal interface for interacting with LLMs:

```python
# example_cli_usage.py
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()

# Example: Simple chat via CLI
# Run: stratumai chat "Explain Python decorators" -p openai -m gpt-4.1-mini
result = subprocess.run(
    ["stratumai", "chat", "Explain Python decorators", "-p", "openai", "-m", "gpt-4.1-mini"],
    capture_output=True,
    text=True
)
print(result.stdout)

# Example: Using CLI with streaming
# Run: stratumai chat "Tell me a story" -p openai -m gpt-4.1-mini --stream
subprocess.run(
    ["stratumai", "chat", "Tell me a story", "-p", "openai", "-m", "gpt-4.1-mini", "--stream"]
)

# Example: Chat with file input
# Run: stratumai chat "Summarize this:" -f document.txt -p openai -m gpt-4.1-mini
subprocess.run(
    ["stratumai", "chat", "Summarize this:", "-f", "document.txt", "-p", "openai", "-m", "gpt-4.1-mini"]
)
```

**Direct CLI Commands:**

```bash
# Quick chat
stratumai chat "Explain Python decorators" -p openai -m gpt-4.1-mini

# Interactive mode with conversation history
stratumai interactive -p anthropic -m claude-3-5-sonnet-20241022

# Smart routing with quality optimization
stratumai route "Complex analysis task" --strategy quality --execute

# Stream response in real-time
stratumai chat "Tell me a story" -p openai -m gpt-4.1-mini --stream

# With file input
stratumai chat "Summarize this:" -f document.txt -p openai -m gpt-4.1-mini

# With system message and custom temperature
stratumai chat "Explain quantum physics" -p openai -m gpt-4.1-mini -s "You are a physics professor" -t 0.3

# List available providers
stratumai providers

# List available models
stratumai models

# Check cache statistics
stratumai cache-stats
```

---

## Setting Up API Keys

StratumAI requires API keys for the providers you want to use.

### Method 1: Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export GROQ_API_KEY="gsk_..."
export XAI_API_KEY="xai-..."
export DEEPSEEK_API_KEY="sk-..."
export OPENROUTER_API_KEY="sk-or-..."

# Reload shell
source ~/.bashrc
```

### Method 2: .env File

Create `.env` in your project root:

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=gsk_...
XAI_API_KEY=xai-...
DEEPSEEK_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

StratumAI will automatically load from `.env` when available.

### Method 3: Pass Directly to Client

```python
from llm_abstraction import LLMClient

client = LLMClient(provider="openai", api_key="sk-...")
```

---

## Using in Other Virtual Environments

### Install from Local Path

From any other project:

```bash
# In your other project
cd /path/to/your/other/project
source venv/bin/activate

# Install stratumai from local path
pip install /home/scotton/dev/projects/stratumai

# OR in editable mode (links to source)
pip install -e /home/scotton/dev/projects/stratumai
```

### Add to requirements.txt

```txt
# requirements.txt

# Install from local path
/home/scotton/dev/projects/stratumai

# OR as editable install
-e /home/scotton/dev/projects/stratumai

# OR if you built a wheel
/home/scotton/dev/projects/stratumai/dist/stratumai-0.1.0-py3-none-any.whl
```

---

## Uninstallation

### Remove Package

```bash
# Uninstall stratumai
pip uninstall stratumai

# Confirm
# y
```

### Clean Build Artifacts

```bash
cd /home/scotton/dev/projects/stratumai

# Remove build directories
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/

# Remove cache
rm -rf __pycache__/
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

---

## Troubleshooting

### Issue: "Module not found" after installation

**Solution 1**: Ensure virtual environment is activated
```bash
source .venv/bin/activate
python -c "import sys; print(sys.prefix)"  # Should show .venv path
```

**Solution 2**: Reinstall package
```bash
pip uninstall stratumai
pip install -e .
```

**Solution 3**: Check Python path
```python
import sys
print('\n'.join(sys.path))
```

### Issue: CLI command not found

**Solution 1**: Ensure scripts directory is in PATH
```bash
# Add to ~/.bashrc
export PATH="$HOME/dev/projects/stratumai/.venv/bin:$PATH"
source ~/.bashrc
```

**Solution 2**: Use full path
```bash
.venv/bin/stratumai --help
```

**Solution 3**: Reinstall with CLI extras
```bash
pip install -e ".[cli]"
```

### Issue: Import errors for dependencies

**Solution**: Install all dependencies
```bash
pip install -r requirements.txt
```

### Issue: Changes not reflected (editable install)

**Cause**: Python caches .pyc files

**Solution**: Clear cache
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Issue: Permission errors during install

**Solution**: Don't use sudo, use virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Issue: Conflicting versions in different projects

**Solution**: Use separate virtual environments for each project
```bash
# Project 1
cd /path/to/project1
python3 -m venv venv
source venv/bin/activate
pip install -e /home/scotton/dev/projects/stratumai

# Project 2
cd /path/to/project2
python3 -m venv venv
source venv/bin/activate
pip install -e /home/scotton/dev/projects/stratumai
```

---

## Next Steps

After successful installation:

1. **Set up API keys** for the providers you want to use
2. **Review examples** in `docs/stratumai-technical-approach.md`
3. **Run tests** to ensure everything works: `pytest`
4. **Explore CLI** commands: `stratumai --help`
5. **Try the Web GUI** (if Phase 3.5 is implemented)
6. **Read the API documentation** for advanced usage
7. **Consider publishing to PyPI** for easier distribution (Phase 6)

---

## Additional Resources

- **Project README**: `/home/scotton/dev/projects/stratumai/README.md`
- **Technical Approach**: `docs/stratumai-technical-approach.md`
- **Project Status**: `docs/project-status.md`
- **Development Guide**: `WARP.md`
- **CLI Documentation**: Available via `stratumai --help` for each command

---

## Future: Publishing to PyPI

Once ready for public release:

1. Create account on PyPI: https://pypi.org/account/register/
2. Configure `~/.pypirc` with credentials
3. Build distribution: `python -m build`
4. Upload to PyPI: `python -m twine upload dist/*`
5. Install from PyPI: `pip install stratumai`

See Phase 6 in `docs/project-status.md` for production readiness tasks.
