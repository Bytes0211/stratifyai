# StratifyAI Local Installation Guide

> Prefer `docs/GETTING-STARTED.md` for the main install-and-first-request path. This page covers local package installation options in more detail.

This guide provides step-by-step instructions for installing StratifyAI as a local Python library/package for development and use in other projects.

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

There are three primary methods to install StratifyAI locally:

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
cd /home/scotton/dev/projects/stratifyai
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
# Check that stratifyai is installed
pip show stratifyai

# Test import
python -c "from stratifyai import LLMClient; print('Success!')"

# Test CLI
stratifyai --help
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
cd /home/scotton/dev/projects/stratifyai
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
pip show stratifyai
python -c "from stratifyai import LLMClient; print('Success!')"
```

### Note
With this method, you need to reinstall after making code changes:
```bash
pip install --upgrade --force-reinstall .
```

---

## Method 3: Build and Install as Wheel

This is the recommended **release-candidate** workflow when you want to create a local distro first, verify it, and then publish the exact same build to PyPI.

### Step 1: Prepare the Environment

```bash
cd /home/scotton/dev/projects/stratifyai
source .venv/bin/activate
```

### Step 2: Build the Local Distribution

```bash
# Clean previous artifacts
rm -rf dist/ build/

# Build wheel + source distribution using uv
uv build

# This creates files in dist/:
# - stratifyai-2.0.0-py3-none-any.whl
# - stratifyai-2.0.0.tar.gz
```

### Step 3: Validate the Artifacts

```bash
# Check package metadata and long description rendering
uv run --with twine python -m twine check dist/*

# Inspect the generated files
ls -lh dist/
tar -tzf dist/stratifyai-2.0.0.tar.gz | head -20
unzip -l dist/stratifyai-2.0.0-py3-none-any.whl | head -20
```

### Step 4: Install the Wheel Locally

```bash
# Install the built wheel in the current environment
pip install --force-reinstall dist/stratifyai-2.0.0-py3-none-any.whl

# OR install from another environment/project
pip install /home/scotton/dev/projects/stratifyai/dist/stratifyai-2.0.0-py3-none-any.whl
```

### Step 5: Verify Installation

```bash
pip show stratifyai
python -c "import stratifyai; print(stratifyai.__version__)"
stratifyai --help
```

### Benefits of Wheel Install
- Creates a portable local distribution you can test before release
- Lets you verify the exact `2.0.0` artifact that will be uploaded to PyPI
- Works well for local deployment, staging, and handoff to other environments
- Mirrors a production installation more closely than editable mode

---

## Verification

After installation (any method), verify everything works:

### 1. Check Package Installation

```bash
pip show stratifyai
```

Expected output:
```
Name: stratifyai
Version: 2.0.0
Summary: Unified multi-provider LLM abstraction module with intelligent routing, cost tracking, and caching
Home-page: https://github.com/Bytes0211/stratifyai
Author: Steven Cotton
Location: /home/scotton/dev/projects/stratifyai
```

### 2. Test Python Import

```bash
python3 << 'EOF'
from stratifyai import LLMClient, ChatRequest, Message
from stratifyai.router import Router, RoutingStrategy

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
stratifyai --help

# List providers
stratifyai providers

# List models
stratifyai models

# Test cache stats
stratifyai cache-stats
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

### Using StratifyAI in Your Python Projects

Once installed, you can use StratifyAI in any Python project:

#### Example 1: Basic Usage

```python
# your_project/main.py
from stratifyai import LLMClient, ChatRequest, Message

# Initialize client
client = LLMClient(provider="openai")

# Create request
request = ChatRequest(
    model="gpt-4o-mini",
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
from stratifyai import Message
from stratifyai.router import Router, RoutingStrategy

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
from stratifyai import LLMClient, ChatRequest, Message

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

The StratifyAI CLI provides a rich terminal interface for interacting with LLMs:

```python
# example_cli_usage.py
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()

# Example: Simple chat via CLI
# Run: stratifyai chat "Explain Python decorators" -p openai -m gpt-4o-mini
result = subprocess.run(
    ["stratifyai", "chat", "Explain Python decorators", "-p", "openai", "-m", "gpt-4o-mini"],
    capture_output=True,
    text=True
)
print(result.stdout)

# Example: Using CLI with streaming
# Run: stratifyai chat "Tell me a story" -p openai -m gpt-4o-mini --stream
subprocess.run(
    ["stratifyai", "chat", "Tell me a story", "-p", "openai", "-m", "gpt-4o-mini", "--stream"]
)

# Example: Chat with file input
# Run: stratifyai chat "Summarize this:" -f document.txt -p openai -m gpt-4o-mini
subprocess.run(
    ["stratifyai", "chat", "Summarize this:", "-f", "document.txt", "-p", "openai", "-m", "gpt-4o-mini"]
)
```

**Direct CLI Commands:**

```bash
# Quick chat
stratifyai chat "Explain Python decorators" -p openai -m gpt-4o-mini

# Interactive mode with conversation history
stratifyai interactive -p anthropic -m claude-3-5-sonnet-20241022

# Smart routing with quality optimization
stratifyai route "Complex analysis task" --strategy quality --execute

# Stream response in real-time
stratifyai chat "Tell me a story" -p openai -m gpt-4o-mini --stream

# With file input
stratifyai chat "Summarize this:" -f document.txt -p openai -m gpt-4o-mini

# With system message and custom temperature
stratifyai chat "Explain quantum physics" -p openai -m gpt-4o-mini -s "You are a physics professor" -t 0.3

# List available providers
stratifyai providers

# List available models
stratifyai models

# Check cache statistics
stratifyai cache-stats
```

---

## Setting Up API Keys

StratifyAI requires API keys for the providers you want to use.

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

StratifyAI will automatically load from `.env` when available.

### Method 3: Pass Directly to Client

```python
from stratifyai import LLMClient

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

# Install stratifyai from local path
pip install /home/scotton/dev/projects/stratifyai

# OR in editable mode (links to source)
pip install -e /home/scotton/dev/projects/stratifyai
```

### Add to requirements.txt

```txt
# requirements.txt

# Install from local path
/home/scotton/dev/projects/stratifyai

# OR as editable install
-e /home/scotton/dev/projects/stratifyai

# OR if you built a wheel
/home/scotton/dev/projects/stratifyai/dist/stratifyai-2.0.0-py3-none-any.whl
```

---

## Uninstallation

### Remove Package

```bash
# Uninstall stratifyai
pip uninstall stratifyai

# Confirm
# y
```

### Clean Build Artifacts

```bash
cd /home/scotton/dev/projects/stratifyai

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
pip uninstall stratifyai
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
export PATH="$HOME/dev/projects/stratifyai/.venv/bin:$PATH"
source ~/.bashrc
```

**Solution 2**: Use full path
```bash
.venv/bin/stratifyai --help
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
pip install -e /home/scotton/dev/projects/stratifyai

# Project 2
cd /path/to/project2
python3 -m venv venv
source venv/bin/activate
pip install -e /home/scotton/dev/projects/stratifyai
```

---

## Next Steps

After successful installation:

1. **Set up API keys** for the providers you want to use
2. **Review examples** in `docs/stratifyai-technical-approach.md`
3. **Run tests** to ensure everything works: `uv run pytest`
4. **Explore CLI** commands: `stratifyai --help`
5. **Try the Web GUI** if you want a local API/UI smoke test
6. **Read the API documentation** for advanced usage
7. **If releasing publicly, build a local distro first and then publish to TestPyPI/PyPI**

---

## Additional Resources

- **Project README**: `/home/scotton/dev/projects/stratifyai/README.md`
- **Technical Approach**: `docs/stratifyai-technical-approach.md`
- **Project Status**: `docs/project-status.md`
- **Development Guide**: `AGENTS.md`
- **CLI Documentation**: Available via `stratifyai --help` for each command

---

## Future: Publishing to PyPI

Once ready for public release:

1. Create accounts on PyPI and TestPyPI
2. Configure `~/.pypirc` with API tokens
3. Build the release locally first: `uv build`
4. Validate the artifacts: `uv run --with twine python -m twine check dist/*`
5. Upload to TestPyPI, verify install, then upload to PyPI
6. Install from PyPI: `pip install stratifyai==2.0.0`

For the full 2.0.0 workflow, see `developer/PYPI-PUBLISHING.md`. 
