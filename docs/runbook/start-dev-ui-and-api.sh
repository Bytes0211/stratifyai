#!/usr/bin/env bash
set -euo pipefail

# Starts FastAPI backend and Vite frontend dev server together.
# Usage: ./docs/runbook/start-dev-ui-and-api.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_PORT="${STRATIFYAI_BACKEND_PORT:-8080}"
FRONTEND_DIR="$ROOT_DIR/frontend"

cleanup() {
  local exit_code=$?

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "Error: .venv not found at $ROOT_DIR/.venv"
  echo "Create it with: uv venv"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Error: frontend dependencies not installed"
  echo "Run: cd $FRONTEND_DIR && npm install"
  exit 1
fi

cd "$ROOT_DIR"
source .venv/bin/activate

echo "Starting backend on http://localhost:${BACKEND_PORT} ..."
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

echo "Starting frontend dev server ..."
(
  cd "$FRONTEND_DIR"
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend/API:  http://localhost:${BACKEND_PORT}"
echo "Frontend URL: check Vite output (usually http://localhost:5173)"
echo ""
echo "Press Ctrl+C to stop both services."

wait -n "$BACKEND_PID" "$FRONTEND_PID"
