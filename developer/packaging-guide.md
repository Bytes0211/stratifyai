# StratifyAI Packaging & Distribution Guide

This guide explains how to build a wheel package for StratifyAI and publish it to PyPI.

## Prerequisites

### Install Build Tools
```bash
# Install build and twine (for PyPI uploads)
pip install build twine

# Or with uv
uv pip install build twine
```

### PyPI Account Setup
1. Create account at [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. Verify your email address
3. Enable 2FA (required for publishing)
4. Create API token at [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
   - Token scope: "Entire account" or project-specific
   - Save the token securely (starts with `pypi-`)

### TestPyPI (Optional but Recommended)
1. Create account at [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/)
2. Create API token at [https://test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/)
3. Use TestPyPI to verify package before publishing to production PyPI

## Part 1: Building the Wheel Package

### Step 1: Verify Package Configuration

Check that `pyproject.toml` is properly configured:

```bash
# View current configuration
cat pyproject.toml
```

Key sections to verify:
- `[project]` - name, version, description, dependencies
- `[project.scripts]` - CLI entry point: `stratifyai = "cli.stratifyai_cli:main"`
- `[tool.setuptools]` - packages to include: `["llm_abstraction", "cli"]`

### Step 2: Clean Previous Builds (if any)

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info stratifyai.egg-info

# Verify clean state
ls -la
```

### Step 3: Build the Package

```bash
# Build both source distribution (.tar.gz) and wheel (.whl)
python -m build

# Or specify only wheel
python -m build --wheel
```

**Expected Output:**
```
* Creating venv isolated environment...
* Installing packages in isolated environment... (setuptools>=61.0, wheel)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist...
Successfully built stratifyai-0.1.0.tar.gz and stratifyai-0.1.0-py3-none-any.whl
```

### Step 4: Verify Build Artifacts

```bash
# List generated files
ls -lh dist/

# Expected files:
# stratifyai-0.1.0-py3-none-any.whl  (wheel)
# stratifyai-0.1.0.tar.gz            (source distribution)
```

### Step 5: Inspect Wheel Contents

```bash
# View wheel contents
unzip -l dist/stratifyai-0.1.0-py3-none-any.whl

# Or extract to temp directory
mkdir -p /tmp/wheel-contents
unzip dist/stratifyai-0.1.0-py3-none-any.whl -d /tmp/wheel-contents
tree /tmp/wheel-contents
```

**Expected structure:**
```
stratifyai-0.1.0-py3-none-any.whl
├── llm_abstraction/           # Main package
│   ├── __init__.py
│   ├── client.py
│   ├── models.py
│   ├── providers/
│   └── ...
├── cli/                       # CLI package
│   ├── __init__.py
│   └── stratifyai_cli.py
└── stratifyai-0.1.0.dist-info/ # Metadata
    ├── entry_points.txt       # CLI entry point
    ├── METADATA
    └── ...
```

### Step 6: Install the Wheel Locally

```bash
# Install from wheel (in current virtual environment)
pip install dist/stratifyai-0.1.0-py3-none-any.whl

# Or with CLI dependencies
pip install dist/stratifyai-0.1.0-py3-none-any.whl[cli]

# Or install all optional dependencies
pip install dist/stratifyai-0.1.0-py3-none-any.whl[all]
```

### Step 7: Test the Installed CLI

```bash
# Verify CLI is installed
which stratifyai

# Test CLI command
stratifyai --help

# Test basic chat
stratifyai chat "Hello, world!" --provider openai --model gpt-4o-mini
```

### Step 8: Uninstall (if needed)

```bash
# Uninstall package
pip uninstall stratifyai

# Or force uninstall
pip uninstall -y stratifyai
```

## Part 2: Publishing to PyPI

### Option A: Publish to TestPyPI (Recommended First)

TestPyPI is a separate instance for testing package uploads without affecting production.

#### Step 1: Configure TestPyPI Credentials

```bash
# Create/edit ~/.pypirc
cat > ~/.pypirc << 'EOF'
[testpypi]
  username = __token__
  password = pypi-YOUR_TESTPYPI_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

#### Step 2: Upload to TestPyPI

```bash
# Upload using twine
python -m twine upload --repository testpypi dist/*

# Or specify token directly (more secure)
python -m twine upload --repository testpypi dist/* \
  --username __token__ \
  --password pypi-YOUR_TESTPYPI_TOKEN_HERE
```

#### Step 3: Verify on TestPyPI

Visit: `https://test.pypi.org/project/stratifyai/`

#### Step 4: Test Installation from TestPyPI

```bash
# Create fresh virtual environment
python -m venv test-env
source test-env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  stratifyai[cli]

# Test CLI
stratifyai --help

# Cleanup
deactivate
rm -rf test-env
```

### Option B: Publish to Production PyPI

**⚠️ WARNING:** Once published, you **cannot** delete or replace a version. Version numbers are permanent.

#### Step 1: Final Pre-Publish Checks

```bash
# Validate package distribution
python -m twine check dist/*

# Expected output:
# Checking dist/stratifyai-0.1.0-py3-none-any.whl: PASSED
# Checking dist/stratifyai-0.1.0.tar.gz: PASSED
```

#### Step 2: Configure PyPI Credentials

```bash
# Create/edit ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
  username = __token__
  password = pypi-YOUR_PYPI_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

#### Step 3: Upload to PyPI

```bash
# Upload using twine
python -m twine upload dist/*

# Or specify token directly (recommended for CI/CD)
python -m twine upload dist/* \
  --username __token__ \
  --password pypi-YOUR_PYPI_TOKEN_HERE
```

**Expected Output:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading stratifyai-0.1.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 52.3/52.3 kB • 00:00 • ?
Uploading stratifyai-0.1.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.1/45.1 kB • 00:00 • ?

View at:
https://pypi.org/project/stratifyai/0.1.0/
```

#### Step 4: Verify on PyPI

Visit: `https://pypi.org/project/stratifyai/`

#### Step 5: Test Installation from PyPI

```bash
# Create fresh virtual environment
python -m venv prod-test-env
source prod-test-env/bin/activate

# Install from PyPI
pip install stratifyai[cli]

# Test CLI
stratifyai --help
stratifyai chat "Test message" --provider openai --model gpt-4o-mini

# Cleanup
deactivate
rm -rf prod-test-env
```

## Updating the Package (New Version)

### Step 1: Update Version Number

Edit `pyproject.toml`:
```toml
[project]
name = "stratifyai"
version = "0.1.1"  # Increment version
```

### Step 2: Update Changelog

Create/update `CHANGELOG.md`:
```markdown
## [0.1.1] - 2026-02-02
### Added
- New feature X

### Fixed
- Bug fix Y
```

### Step 3: Clean and Rebuild

```bash
# Remove old builds
rm -rf build/ dist/ *.egg-info

# Build new version
python -m build
```

### Step 4: Upload New Version

```bash
# Check package
python -m twine check dist/*

# Upload to PyPI
python -m twine upload dist/*
```

## Troubleshooting

### Build Errors

**Error: "No module named 'build'"**
```bash
pip install build
```

**Error: "packages not found"**
- Verify `[tool.setuptools]` packages list in `pyproject.toml`
- Ensure `__init__.py` exists in package directories

### Upload Errors

**Error: "403 Forbidden"**
- Check API token is correct
- Verify token has proper scope
- Ensure 2FA is enabled on PyPI account

**Error: "400 File already exists"**
- Version already published (cannot overwrite)
- Increment version number in `pyproject.toml`

**Error: "Invalid distribution filename"**
- Ensure version follows semantic versioning (e.g., 0.1.0, not 0.1)
- Check for spaces or invalid characters in package name

### Installation Errors

**Error: "stratifyai command not found"**
- Ensure `[project.scripts]` is configured in `pyproject.toml`
- Verify installation: `pip show stratifyai`
- Check entry points: `pip show -f stratifyai | grep console_scripts`

**Error: "ModuleNotFoundError: No module named 'llm_abstraction'"**
- Verify packages are included: `[tool.setuptools] packages = ["llm_abstraction", "cli"]`
- Reinstall with: `pip install --force-reinstall stratifyai`

## Best Practices

### Version Numbering
- Follow semantic versioning: `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes

### Pre-Release Checklist
- [ ] All tests passing (`pytest`)
- [ ] Linting clean (`ruff check .`)
- [ ] Type checking passes (`mypy llm_abstraction cli`)
- [ ] Documentation updated
- [ ] Version number incremented
- [ ] Changelog updated
- [ ] Test on TestPyPI first
- [ ] Verify installation in clean environment

### Security
- Never commit `~/.pypirc` or API tokens to git
- Use API tokens instead of username/password
- Restrict token scope to specific projects when possible
- Rotate tokens periodically
- Use environment variables for tokens in CI/CD

### CI/CD Integration

Example GitHub Actions workflow (`.github/workflows/publish.yml`):
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: python -m twine upload dist/*
```

## Additional Resources

- **Python Packaging Guide:** https://packaging.python.org/
- **PyPI Help:** https://pypi.org/help/
- **Setuptools Documentation:** https://setuptools.pypa.io/
- **Twine Documentation:** https://twine.readthedocs.io/
- **PEP 621 (pyproject.toml):** https://peps.python.org/pep-0621/

## Quick Reference

```bash
# Build wheel
python -m build

# Check package
python -m twine check dist/*

# Install locally
pip install dist/stratifyai-0.1.0-py3-none-any.whl[cli]

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*

# Test CLI
stratifyai --help
```
