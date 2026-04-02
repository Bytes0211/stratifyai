# Frontend Integration Guide

Integrate StratifyAI streaming with any frontend framework using Server-Sent Events (SSE) or WebSockets.

**Last Updated:** February 4, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Server-Sent Events (SSE)](#server-sent-events-sse)
4. [WebSocket Integration](#websocket-integration)
5. [Frontend Examples](#frontend-examples)
6. [Event Format](#event-format)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Overview

StratifyAI provides streaming responses via Python generators. To expose this to web frontends, you need a thin HTTP layer that converts these generators into SSE or WebSocket streams.

**Key Principles:**
- StratifyAI stays framework-agnostic — no frontend dependencies
- Standard SSE/WebSocket protocols work with any frontend
- Consistent event format across all providers

---

## Architecture

```
┌─────────────────┐     SSE/WS      ┌─────────────────┐     Generator    ┌─────────────────┐
│  Frontend       │ ◄─────────────► │  HTTP Server    │ ◄──────────────► │  StratifyAI      │
│  (React/Vue/    │                 │  (FastAPI/      │                  │  LLMClient      │
│   vanilla JS)   │                 │   Flask/etc)    │                  │                 │
└─────────────────┘                 └─────────────────┘                  └─────────────────┘
```

---

## Server-Sent Events (SSE)

SSE is the recommended approach for most use cases. It's simpler than WebSockets and works well for unidirectional streaming (server → client).

### FastAPI Example

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from stratifyai import LLMClient
from stratifyai.models import Message

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_methods=["*"],
    allow_headers=["*"],
)

client = LLMClient()


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int | None = None


@app.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """Stream chat completion via SSE."""
    
    def event_generator():
        try:
            messages = [
                Message(role=m["role"], content=m["content"])
                for m in request.messages
            ]
            
            for chunk in client.chat_completion_stream(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                event = {
                    "type": "chunk",
                    "content": chunk.content,
                    "model": chunk.model,
                    "provider": chunk.provider,
                }
                yield f"data: {json.dumps(event)}\n\n"
            
            # Send completion event with usage info
            yield f"data: {json.dumps({'type': 'done', 'usage': {'total_tokens': chunk.usage.total_tokens, 'cost_usd': chunk.usage.cost_usd}})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat completion."""
    messages = [
        Message(role=m["role"], content=m["content"])
        for m in request.messages
    ]
    
    response = client.chat(
        model=request.model,
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
    
    return {
        "content": response.content,
        "model": response.model,
        "provider": response.provider,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost_usd": response.usage.cost_usd,
        }
    }
```

### Flask Example

```python
from flask import Flask, request, Response
import json

from stratifyai import LLMClient
from stratifyai.models import Message

app = Flask(__name__)
client = LLMClient()


@app.route("/chat/stream", methods=["POST"])
def stream_chat():
    data = request.json
    
    def generate():
        messages = [
            Message(role=m["role"], content=m["content"])
            for m in data["messages"]
        ]
        
        for chunk in client.chat_completion_stream(
            model=data["model"],
            messages=messages,
            temperature=data.get("temperature", 0.7)
        ):
            event = {"type": "chunk", "content": chunk.content}
            yield f"data: {json.dumps(event)}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")
```

---

## WebSocket Integration

Use WebSockets when you need bidirectional communication (e.g., interrupting generation, sending multiple messages without new connections).

### FastAPI WebSocket Example

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import asyncio

from stratifyai import LLMClient
from stratifyai.models import Message

app = FastAPI()
client = LLMClient()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                messages = [
                    Message(role=m["role"], content=m["content"])
                    for m in data["messages"]
                ]
                
                # Stream response back to client
                for chunk in client.chat_completion_stream(
                    model=data["model"],
                    messages=messages,
                    temperature=data.get("temperature", 0.7)
                ):
                    await websocket.send_json({
                        "type": "chunk",
                        "content": chunk.content,
                    })
                    # Allow other tasks to run
                    await asyncio.sleep(0)
                
                await websocket.send_json({
                    "type": "done",
                    "usage": {
                        "total_tokens": chunk.usage.total_tokens,
                        "cost_usd": chunk.usage.cost_usd,
                    }
                })
                
    except WebSocketDisconnect:
        pass
```

---

## Frontend Examples

### Vanilla JavaScript (SSE)

```javascript
async function streamChat(model, messages) {
  const response = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));
        
        if (event.type === 'chunk') {
          // Append content to UI
          document.getElementById('output').textContent += event.content;
        } else if (event.type === 'done') {
          console.log('Usage:', event.usage);
        } else if (event.type === 'error') {
          console.error('Error:', event.message);
        }
      }
    }
  }
}
```

### React Hook

```jsx
import { useState, useCallback } from 'react';

export function useStreamChat() {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState(null);

  const streamChat = useCallback(async (model, messages) => {
    setContent('');
    setIsStreaming(true);
    setError(null);

    try {
      const response = await fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const event = JSON.parse(line.slice(6));

            if (event.type === 'chunk') {
              setContent(prev => prev + event.content);
            } else if (event.type === 'done') {
              setUsage(event.usage);
            } else if (event.type === 'error') {
              setError(event.message);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { content, isStreaming, usage, error, streamChat };
}

// Usage in component
function ChatComponent() {
  const { content, isStreaming, usage, error, streamChat } = useStreamChat();
  const [input, setInput] = useState('');

  const handleSubmit = () => {
    streamChat('gpt-4o-mini', [{ role: 'user', content: input }]);
  };

  return (
    <div>
      <input value={input} onChange={e => setInput(e.target.value)} />
      <button onClick={handleSubmit} disabled={isStreaming}>Send</button>
      <div>{content}</div>
      {usage && <div>Tokens: {usage.total_tokens} | Cost: ${usage.cost_usd.toFixed(4)}</div>}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

### Vue 3 Composable

```javascript
import { ref } from 'vue';

export function useStreamChat() {
  const content = ref('');
  const isStreaming = ref(false);
  const usage = ref(null);
  const error = ref(null);

  async function streamChat(model, messages) {
    content.value = '';
    isStreaming.value = true;
    error.value = null;

    try {
      const response = await fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const event = JSON.parse(line.slice(6));

            if (event.type === 'chunk') {
              content.value += event.content;
            } else if (event.type === 'done') {
              usage.value = event.usage;
            } else if (event.type === 'error') {
              error.value = event.message;
            }
          }
        }
      }
    } catch (err) {
      error.value = err.message;
    } finally {
      isStreaming.value = false;
    }
  }

  return { content, isStreaming, usage, error, streamChat };
}
```

---

## Event Format

All SSE/WebSocket events follow a consistent JSON format:

### Chunk Event
```json
{
  "type": "chunk",
  "content": "Hello",
  "model": "gpt-4o-mini",
  "provider": "openai"
}
```

### Done Event
```json
{
  "type": "done",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60,
    "cost_usd": 0.0001
  }
}
```

### Error Event
```json
{
  "type": "error",
  "message": "Rate limit exceeded",
  "code": "rate_limit_error"
}
```

### Progress Event (Optional)
For long-running operations, emit progress updates:
```json
{
  "type": "progress",
  "message": "Processing...",
  "progress": 50
}
```

---

## Error Handling

### Server-Side

```python
from stratifyai.exceptions import (
    RateLimitError,
    AuthenticationError,
    InvalidModelError,
    ProviderError
)

def event_generator():
    try:
        for chunk in client.chat_completion_stream(...):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.content})}\n\n"
    except RateLimitError as e:
        yield f"data: {json.dumps({'type': 'error', 'code': 'rate_limit', 'message': str(e)})}\n\n"
    except AuthenticationError as e:
        yield f"data: {json.dumps({'type': 'error', 'code': 'auth_error', 'message': 'Invalid API key'})}\n\n"
    except InvalidModelError as e:
        yield f"data: {json.dumps({'type': 'error', 'code': 'invalid_model', 'message': str(e)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'code': 'unknown', 'message': str(e)})}\n\n"
```

### Client-Side

```javascript
// Reconnection with exponential backoff
async function streamWithRetry(model, messages, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      await streamChat(model, messages);
      return; // Success
    } catch (err) {
      if (attempt === maxRetries - 1) throw err;
      await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000));
    }
  }
}
```

---

## Best Practices

### 1. CORS Configuration
Configure CORS properly for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### 2. Request Validation
Validate incoming requests:
```python
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 0.7
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('Temperature must be between 0 and 2')
        return v
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('Messages cannot be empty')
        return v
```

### 3. Rate Limiting
Implement rate limiting to protect your API:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat/stream")
@limiter.limit("10/minute")
async def stream_chat(request: Request, chat_request: ChatRequest):
    ...
```

### 4. Authentication
Secure your endpoints:
```python
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    # Validate token
    return token

@app.post("/chat/stream")
async def stream_chat(request: ChatRequest, token: str = Depends(verify_token)):
    ...
```

### 5. Nginx Proxy Configuration
For production deployments with nginx:
```nginx
location /chat/stream {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
}
```

---

## Running the Sample Server

See `examples/web_server.py` for a complete working example:

```bash
# Install dependencies
pip install fastapi uvicorn

# Run server
uvicorn examples.web_server:app --reload --port 8000

# Test streaming
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello!"}]}'
```
