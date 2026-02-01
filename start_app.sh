#!/bin/bash

# Start StratumAI CLI in interactive mode
source .venv/bin/activate

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

python -m cli.stratumai_cli chat

# Note: To start the FastAPI web GUI instead, use:
# uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
