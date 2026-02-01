# PyPI Publishing Guide

Step-by-step instructions for publishing StratumAI to PyPI.

**Last Updated:** February 1, 2026

---

## Prerequisites

1. **PyPI Account**: Create accounts on:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Install Build Tools**:
   ```bash
   pip install --upgrade pip setuptools wheel build twine
   ```

3. **API Tokens**: Generate API tokens from PyPI:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

---

## Pre-Publication Checklist

Before publishing, ensure:

- [ ] Version number updated in `pyproject.toml`
- [ ] README.md is complete and accurate
- [ ] LICENSE file exists (MIT)
- [ ] All tests pass: `pytest`
- [ ] Documentation is up-to-date
- [ ] CHANGELOG.md is updated (if exists)
- [ ] No sensitive data in codebase
- [ ] Git repository is clean: `git status`
- [ ] All changes committed and pushed

---

## Building the Package

### 1. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 2. Build Distribution Files

```bash
# Build source distribution and wheel
python -m build

# This creates:
# - dist/stratumai-0.1.0.tar.gz (source distribution)
# - dist/stratumai-0.1.0-py3-none-any.whl (wheel)
```

### 3. Verify Build

```bash
# Check distribution files
ls -lh dist/

# Verify package contents
tar -tzf dist/stratumai-0.1.0.tar.gz | head -20
unzip -l dist/stratumai-0.1.0-py3-none-any.whl | head -20

# Check package metadata
twine check dist/*
```

---

## Testing on TestPyPI

**Always test on TestPyPI first before publishing to production PyPI!**

### 1. Upload to TestPyPI

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Or with explicit URL
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# You'll be prompted for:
# - Username: __token__
# - Password: pypi-... (your TestPyPI token)
```

### 2. Install from TestPyPI

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    stratumai

# Test the installation
python -c "from llm_abstraction import LLMClient; print('Success!')"
stratumai --help

# Cleanup
deactivate
rm -rf test_env
```

---

## Publishing to PyPI (Production)

### 1. Final Checks

```bash
# Verify version is correct
grep version pyproject.toml

# Ensure git tag matches
git tag v0.1.0
git push origin v0.1.0

# Final test run
pytest
```

### 2. Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*

# You'll be prompted for:
# - Username: __token__
# - Password: pypi-... (your PyPI token)
```

### 3. Verify Publication

```bash
# Check PyPI page
open https://pypi.org/project/stratumai/

# Install from PyPI
pip install stratumai

# Test installation
python -c "from llm_abstraction import LLMClient; print('Success!')"
stratumai --version
```

---

## Using API Tokens (Recommended)

### Configure ~/.pypirc

Create `~/.pypirc` with your API tokens:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN

[testpypi]
username = __token__
password = pypi-YOUR_TEST_TOKEN
```

**Security**: Ensure proper permissions:
```bash
chmod 600 ~/.pypirc
```

### Upload with Configured Tokens

```bash
# TestPyPI
twine upload -r testpypi dist/*

# PyPI
twine upload -r pypi dist/*
```

---

## Version Bumping

### Semantic Versioning

StratumAI follows [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Update Version

1. **Edit pyproject.toml**:
   ```toml
   version = "0.2.0"  # Update version
   ```

2. **Create Git Tag**:
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```

3. **Rebuild and Publish**:
   ```bash
   rm -rf dist/
   python -m build
   twine upload dist/*
   ```

---

## Troubleshooting

### Problem: "File already exists"

**Solution**: You cannot overwrite existing versions on PyPI. Bump the version number.

```bash
# Update version in pyproject.toml
# Rebuild
rm -rf dist/ build/
python -m build
twine upload dist/*
```

### Problem: "Invalid distribution"

**Solution**: Check package structure and run validation:

```bash
twine check dist/*
pip install check-manifest
check-manifest
```

### Problem: Import errors after installation

**Solution**: Ensure `__init__.py` files exist in all packages:

```bash
find llm_abstraction -type d -exec touch {}/__init__.py \;
```

### Problem: Missing dependencies

**Solution**: Verify dependencies in pyproject.toml match requirements.txt:

```bash
pip install pip-tools
pip-compile pyproject.toml
```

---

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
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
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## Post-Publication

After publishing:

1. **Verify Installation**:
   ```bash
   pip install stratumai
   stratumai --help
   ```

2. **Update Documentation**:
   - Add installation instructions to README.md
   - Update docs with PyPI badge

3. **Announce**:
   - Create GitHub release
   - Update project homepage
   - Share on social media (optional)

4. **Monitor**:
   - Check download stats on PyPI
   - Monitor GitHub issues for installation problems
   - Keep dependencies updated

---

## PyPI Package URLs

- **Production**: https://pypi.org/project/stratumai/
- **Test**: https://test.pypi.org/project/stratumai/
- **Documentation**: Linked from PyPI page to GitHub README

---

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Setuptools Documentation](https://setuptools.pypa.io/)

---

## Quick Reference

```bash
# Full publication workflow
rm -rf dist/ build/ *.egg-info
python -m build
twine check dist/*
twine upload -r testpypi dist/*  # Test first
twine upload -r pypi dist/*      # Then production
```

## Notes

- Never publish with uncommitted changes
- Always test on TestPyPI first
- Use semantic versioning
- Keep CHANGELOG.md updated
- Tag releases in git
- Monitor PyPI download stats
