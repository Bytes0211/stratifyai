# StratifyAI API Server

FastAPI-based REST API and Web GUI for StratifyAI multi-provider LLM abstraction.

## Features

- **REST API** for chat completions across 8 providers
- **WebSocket streaming** for real-time responses
- **Interactive Web UI** for testing and comparing providers
- **Cost tracking** with real-time dashboard
- **Auto-generated API docs** (Swagger UI)

## Quick Start

### 1. Install Dependencies

```bash
# From project root
source .venv/bin/activate
uv pip install fastapi uvicorn websockets
```

### 2. Set API Keys

Export API keys for the providers you want to use:

```bash
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"
export DEEPSEEK_API_KEY="your-key-here"
export GROQ_API_KEY="your-key-here"
export GROK_API_KEY="your-key-here"
export OPENROUTER_API_KEY="your-key-here"
# Ollama doesn't require an API key (runs locally)
```

### 3. Run the Server

```bash
# From project root
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
cd api
python main.py
```

### 4. Access the Interface

- **Web UI:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc

## API Endpoints

### Chat Completion

```bash
POST /api/chat
Content-Type: application/json

{
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### WebSocket Streaming

```javascript
const ws = new WebSocket('ws://localhost:8000/api/chat/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    provider: 'openai',
    model: 'gpt-4.1-mini',
    messages: [{role: 'user', content: 'Tell me a story'}],
    temperature: 0.7
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (!data.done) {
    console.log(data.content); // Stream chunk
  } else {
    console.log('Stream complete');
  }
};
```

### List Providers

```bash
GET /api/providers
```

### List Models

```bash
GET /api/models/{provider}
```

### Cost Summary

```bash
GET /api/cost
```

### Reset Cost Tracker

```bash
POST /api/cost/reset
```

## Web UI Features

The interactive web interface (`http://localhost:8000`) provides:

1. **Provider Selection** - Choose from 8 LLM providers
2. **Model Selection** - Dynamically loaded models for each provider
3. **Temperature Control** - Adjust response creativity (0-2)
4. **Max Tokens** - Optional limit on response length
5. **Chat Interface** - Conversational UI with message history
6. **Cost Tracking** - Real-time cost, token, and call count tracking
7. **Reset Chat** - Clear conversation history

## Architecture

```
api/
├── main.py              # FastAPI application
├── static/
│   └── index.html       # Web UI
└── README.md            # This file
```

The API server:
- Uses `LLMClient` from the core `llm_abstraction` package
- Tracks costs with the `CostTracker` module
- Supports all 8 providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, Ollama, OpenRouter)
- Provides both REST and WebSocket endpoints

## Cost Tracking

The server maintains a global `CostTracker` that monitors:
- Total cost in USD
- Total tokens used
- Number of API calls
- Per-provider breakdown
- Per-model breakdown
- Cache hit rates

Access the summary at `/api/cost` or view it in the web UI sidebar.

## Development

### Run with Hot Reload

```bash
uvicorn api.main:app --reload
```

### View Logs

The server logs all requests and errors to stdout. Set log level:

```bash
LOG_LEVEL=DEBUG uvicorn api.main:app
```

### CORS Configuration

CORS is enabled for all origins by default. For production, restrict to specific origins:

```python
# In api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    ...
)
```

## Production Deployment

### Using Gunicorn + Uvicorn

```bash
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Set these in production:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `DEEPSEEK_API_KEY`
- `GROQ_API_KEY`
- `GROK_API_KEY`
- `OPENROUTER_API_KEY`

## Security Notes

- API keys should be stored securely (environment variables, secrets manager)
- No authentication is implemented - add it for production
- Rate limiting should be implemented for public APIs
- HTTPS should be used in production

## Troubleshooting

### Port Already in Use

```bash
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000
```

### Import Errors

Make sure you're in the project root and the virtual environment is activated:

```bash
cd /path/to/stratifyai
source .venv/bin/activate
python -m uvicorn api.main:app
```

### Provider Not Available

Check that the API key is set:

```bash
echo $OPENAI_API_KEY  # Should print your key
```

## Next Steps

- Add authentication/authorization
- Implement rate limiting
- Add request validation
- Set up monitoring and logging
- Deploy to production environment
