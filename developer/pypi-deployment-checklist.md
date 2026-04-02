# PyPI Deployment Checklist

**Project**: StratifyAI  
**Target Version**: 0.2.0 (Beta)  
**Deployment Date**: TBD  

---

## Pre-Deployment Tasks

### 1. Version & Metadata
- [ ] Bump version to `0.2.0` in `pyproject.toml`
- [ ] Update `keywords` to include "bedrock", "aws", "rag", "vector-db"
- [ ] Verify all URLs in `[project.urls]` are correct
- [ ] Ensure author email is correct (currently `scotton@example.com`)

### 2. Legal & Licensing
- [ ] Create `LICENSE` file (MIT license text)
- [ ] Add copyright notice to LICENSE
- [ ] Verify no copyrighted code from provider SDKs

### 3. Documentation
- [ ] Create `CHANGELOG.md` with version history
- [ ] Review README.md for accuracy (currently excellent)
- [ ] Add PyPI badges to README:
  ```markdown
  [![PyPI version](https://badge.fury.io/py/stratifyai.svg)](https://badge.fury.io/py/stratifyai)
  [![Downloads](https://pepy.tech/badge/stratifyai)](https://pepy.tech/project/stratifyai)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  ```
- [ ] Add "Quick comparison with LiteLLM/LangChain" section to README
- [ ] Verify all code examples in README work

### 4. Code Quality
- [ ] Run full test suite: `pytest`
- [ ] Check test coverage: `pytest --cov`
- [ ] Run linter: `ruff check .`
- [ ] Run formatter: `ruff format --check .`
- [ ] Run type checker: `mypy llm_abstraction/`
- [ ] Fix any warnings/errors

### 5. Build & Test Installation
- [ ] Clean old builds: `rm -rf dist/ build/ *.egg-info`
- [ ] Build package: `python -m build`
- [ ] Verify contents: `tar -tzf dist/stratifyai-0.2.0.tar.gz | head -20`
- [ ] Test install locally:
  ```bash
  python -m venv test_env
  source test_env/bin/activate
  pip install dist/stratifyai-0.2.0-*.whl
  python -c "from stratifyai import LLMClient; print('Success!')"
  ```
- [ ] Test CLI works: `stratifyai --help`

### 6. PyPI Account Setup
- [ ] Create PyPI account: https://pypi.org/account/register/
- [ ] Enable 2FA on PyPI account
- [ ] Create API token: https://pypi.org/manage/account/token/
- [ ] Install twine: `pip install twine`

### 7. Test Deployment (TestPyPI)
- [ ] Upload to TestPyPI first:
  ```bash
  python -m twine upload --repository testpypi dist/*
  ```
- [ ] Test installation from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ stratifyai
  ```
- [ ] Verify package page looks correct: https://test.pypi.org/project/stratifyai/

### 8. Production Deployment
- [ ] Upload to PyPI:
  ```bash
  python -m twine upload dist/*
  ```
- [ ] Verify package page: https://pypi.org/project/stratifyai/
- [ ] Test installation: `pip install stratifyai`
- [ ] Test import: `python -c "import stratifyai; print(llm_abstraction.__version__)"`

### 9. Version Control
- [ ] Commit all changes: `git add -A && git commit -m "chore: prepare v0.2.0 release"`
- [ ] Create Git tag: `git tag -a v0.2.0 -m "Release v0.2.0: Add AWS Bedrock, RAG integration"`
- [ ] Push to GitHub: `git push origin main --tags`
- [ ] Create GitHub Release with changelog

### 10. Post-Deployment
- [ ] Update GitHub repo description to mention PyPI
- [ ] Add PyPI badge to README
- [ ] Post announcement on:
  - [ ] Reddit r/Python
  - [ ] Reddit r/MachineLearning  
  - [ ] Hacker News (Show HN: StratifyAI - Multi-provider LLM abstraction with cost tracking)
  - [ ] Twitter/X with hashtags #Python #LLM #AI #OpenAI #Anthropic
  - [ ] LinkedIn (professional audience)
- [ ] Monitor PyPI downloads: https://pepy.tech/project/stratifyai
- [ ] Monitor GitHub issues for user feedback

---

## Post-Launch Monitoring (Week 1)

- [ ] Day 1: Check PyPI downloads
- [ ] Day 2: Monitor GitHub issues/stars
- [ ] Day 3: Respond to any installation issues
- [ ] Day 7: Analyze feedback, plan next release

---

## Version 0.2.0 Features to Highlight

**New in 0.2.0**:
- AWS Bedrock provider (9th provider)
- RAG/Vector DB integration with ChromaDB
- Enhanced caching with analytics
- Model auto-selection for file types
- Large file handling with intelligent extraction

**Upgrade from 0.1.0**:
```bash
pip install --upgrade stratifyai
```

---

## Troubleshooting

### Build fails
```bash
# Clear build artifacts
rm -rf dist/ build/ *.egg-info
python -m build
```

### Upload fails
```bash
# Check credentials
python -m twine check dist/*
# Re-upload with verbose
python -m twine upload --verbose dist/*
```

### Installation fails
```bash
# Check package integrity
pip download stratifyai
tar -tzf stratifyai-0.2.0.tar.gz
```

---

## Resources

- PyPI Help: https://pypi.org/help/
- Packaging Guide: https://packaging.python.org/
- Twine Docs: https://twine.readthedocs.io/
- TestPyPI: https://test.pypi.org/

---

**Status**: Ready for deployment pending checklist completion
