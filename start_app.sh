#!/bin/bash

# Start app
source .venv/bin/activate
python api/main.py
# Pause 0.25 minutes
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
