#!/bin/bash

# Start StratifyAI CLI in interactive mode
source .venv/bin/activate

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

python -m cli.stratifyai_cli chat


