# StratifyAI Runbook: Web UI, CLI, and API

This runbook provides copy-paste commands for local development and daily operations.

Related runbook:
- See docs/runbook/phase15-security-runbook.md for security hardening assumptions, environment settings, and verification checks.

## 1) One-time setup

```bash
cd /home/scotton/dev/projects/stratifyai

# Create and activate environment (if needed)
uv venv
source .venv/bin/activate

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
cd ..
```

## 2) Start the Web UI

### Option 0: One-command dev launcher (backend + frontend)

```bash
cd /home/scotton/dev/projects/stratifyai
./docs/runbook/start-dev-ui-and-api.sh
```

Optional custom backend port:

```bash
cd /home/scotton/dev/projects/stratifyai
STRATIFYAI_BACKEND_PORT=8090 ./docs/runbook/start-dev-ui-and-api.sh
```

### Option A: Production-like local mode (UI served by FastAPI)

```bash
cd /home/scotton/dev/projects/stratifyai
source .venv/bin/activate

# Build SPA assets
cd frontend
npm run build
cd ..

# Start backend that also serves the built UI
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

Open:
- Web UI: http://localhost:8080
- Swagger docs: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

### Option B: Frontend dev mode (HMR)

Terminal 1:

```bash
cd /home/scotton/dev/projects/stratifyai
source .venv/bin/activate
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

Terminal 2:

```bash
cd /home/scotton/dev/projects/stratifyai/frontend
npm run dev
```

Open frontend dev server URL printed by Vite (typically http://localhost:5173).

## 3) Start and use the CLI

```bash
cd /home/scotton/dev/projects/stratifyai
source .venv/bin/activate
```

### Quick checks

```bash
# Show available providers
uv run python -m cli.stratifyai_cli providers

# Show models
uv run python -m cli.stratifyai_cli models

# Check API key setup
uv run python -m cli.stratifyai_cli check-keys

# Diagnostics (human-readable)
uv run python -m cli.stratifyai_cli doctor

# Diagnostics (JSON for CI/automation)
uv run python -m cli.stratifyai_cli doctor --json
```

### Chat and routing

```bash
# Interactive chat prompt flow
uv run python -m cli.stratifyai_cli chat

# Direct chat call
uv run python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini "Hello"

# Interactive session mode
uv run python -m cli.stratifyai_cli interactive

# Route analysis only (no API call)
uv run python -m cli.stratifyai_cli route --dry-run "Summarize this architecture"

# Route and execute
uv run python -m cli.stratifyai_cli route --execute "Explain event loops"
```

## 4) Start API service only

```bash
cd /home/scotton/dev/projects/stratifyai
source .venv/bin/activate
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

## 5) API command examples

### Providers and models

```bash
curl -s http://localhost:8080/api/providers
curl -s http://localhost:8080/api/models/openai
```

### Health and metrics

```bash
curl -s http://localhost:8080/health/providers
curl -s http://localhost:8080/api/health/providers
curl -s http://localhost:8080/api/metrics
```

### Chat completion

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    "temperature": 0.0,
    "max_tokens": 16
  }'
```

### Cost endpoints

```bash
curl -s http://localhost:8080/api/cost
curl -s -X POST http://localhost:8080/api/cost/reset
```

## 6) Environment variables (common)

```bash
# Provider keys (set only what you use)
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export GROQ_API_KEY="..."
export GROK_API_KEY="..."
export OPENROUTER_API_KEY="..."

# Optional API auth (recommended outside local dev)
export STRATIFYAI_API_KEY="your-api-bearer-token"
```

## 7) Troubleshooting commands

```bash
# Full test suite
uv run pytest

# Type check
uv run mypy stratifyai cli api

# Check only new Phase 14 tests
uv run pytest tests/test_phase14_developer_experience.py -q
```
