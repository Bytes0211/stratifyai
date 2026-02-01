#!/bin/bash

# Start StratumAI CLI in interactive mode
source .venv/bin/activate
python -m cli.stratumai_cli chat

# Note: To start the FastAPI web GUI instead, use:
# uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
