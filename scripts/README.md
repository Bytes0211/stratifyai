# Scripts

Utility scripts for StratifyAI development and release workflows. All scripts are run from the project root.

## Deployment Order

Follow this sequence for every release:

```
1. python scripts/bump_version.py 2.1.0       # sync version across all files
2. python scripts/validate_catalog.py          # validate model catalog
3. bash scripts/test_deploy_stratifyai.sh      # deploy to TestPyPI
4. bash scripts/prod_deploy_stratifyai.sh      # deploy to Production PyPI
```

## bump_version.py

Bumps the version string across all project files in a single command. The source of truth is `pyproject.toml`.

```bash
python scripts/bump_version.py          # show current version + file sync status
python scripts/bump_version.py 2.1.0    # bump to 2.1.0
```

**Files updated:**
- `pyproject.toml` (source of truth)
- `package.json` (root)
- `frontend/package.json`
- `stratifyai/__init__.py` (fallback)
- `api/main.py` (fallback)
- `README.md` (title line)
- `developer/PYPI-PUBLISHING.md` (intro + expected output block)
- `docs/CHANGELOG.md` (reminder to update manually)

After bumping, the script reads back each file and verifies the version matches. Mismatches are flagged with a red indicator.

## validate_catalog.py

Validates the model catalog (`catalog/models.json`) against its schema and business rules.

```bash
python scripts/validate_catalog.py
```

**Checks performed:**
- JSON syntax validity
- Required top-level fields (`version`, `updated`, `providers`) and semver format
- Provider names are lowercase, no duplicate model IDs
- Required model fields (`context`, `cost_input`, `cost_output`)
- Context windows are positive integers, pricing values are non-negative
- Deprecated models have `deprecated_date` and `replacement_model`
- Warns on missing `quality_score` or `avg_latency_ms` (used by the router)

## build_safeguards.sh

Shared safeguard functions sourced by both deploy scripts. Not run directly.

**Functions provided:**
- `verify_version_consistency` — checks all managed files match the pyproject.toml version
- `rebuild_frontend` — rebuilds the Vite frontend so the correct version is baked into the bundle, then verifies it in the output
- `audit_tarball` — inspects the built `.tar.gz` for forbidden patterns and aborts if any are found

**Forbidden patterns** (build is rejected if any appear in the artifact):
- `.env`, `.env.*` — environment secrets
- `mcp.json`, `mcp.json.backup` — editor MCP server configs with API keys
- `.cursor/`, `.vscode/`, `.claude/` — editor/IDE directories
- `*.sqlite`, `*.sqlite3`, `*.db` — database files
- `*.backup` — backup files
- `credentials`, `secret` — sensitive files
- `node_modules/` — frontend dependencies

## test_deploy_stratifyai.sh

Deploys the package to **TestPyPI** for pre-release validation.

```bash
bash scripts/test_deploy_stratifyai.sh
```

**Workflow:**
1. Reads local version from `pyproject.toml`
2. Verifies version consistency across all files
3. Rebuilds frontend to bake correct version into bundle
4. Compares against TestPyPI — aborts if not newer
5. Cleans and rebuilds distribution
6. Audits the tarball for sensitive/forbidden files
7. Uploads via `twine` to TestPyPI

## prod_deploy_stratifyai.sh

Deploys the package to **Production PyPI**. Requires a successful TestPyPI deployment first.

```bash
bash scripts/prod_deploy_stratifyai.sh
```

**Workflow:**
1. Reads local version from `pyproject.toml`
2. Verifies version consistency across all files
3. Rebuilds frontend to bake correct version into bundle
4. Verifies local version matches TestPyPI (must deploy there first)
5. Verifies local version is newer than Production PyPI
6. Cleans and rebuilds distribution
7. Audits the tarball for sensitive/forbidden files
8. Uploads via `twine` to Production PyPI
