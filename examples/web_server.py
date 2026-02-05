"""
StratifyAI Web Server Example

A complete FastAPI server demonstrating SSE and WebSocket streaming
for frontend integration.

Usage:
    # Install dependencies
    pip install fastapi uvicorn

    # Run server
    uvicorn examples.web_server:app --reload --port 8000

    # Test SSE streaming
    curl -N -X POST http://localhost:8000/chat/stream \
        -H "Content-Type: application/json" \
        -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello!"}]}'

    # Open browser for interactive demo
    http://localhost:8000/

Author: StratifyAI Team
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest as LLMChatRequest
from stratifyai.exceptions import (
    RateLimitError,
    AuthenticationError,
    InvalidModelError,
    InvalidProviderError,
    ProviderError,
)

# Initialize FastAPI app
app = FastAPI(
    title="StratifyAI Web Server",
    description="SSE and WebSocket streaming for StratifyAI",
    version="1.0.0",
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize StratifyAI client
client = LLMClient()


# ============================================================================
# Request/Response Models
# ============================================================================


class ChatRequest(BaseModel):
    """Chat completion request."""

    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    provider: Optional[str] = None

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list) -> list:
        if not v:
            raise ValueError("Messages cannot be empty")
        for msg in v:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content'")
        return v


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    content: str
    model: str
    provider: str
    usage: dict


class ModelsResponse(BaseModel):
    """List of available models."""

    providers: dict[str, list[str]]


# ============================================================================
# Helper Functions
# ============================================================================


def create_error_event(code: str, message: str) -> str:
    """Create a formatted SSE error event."""
    return f"data: {json.dumps({'type': 'error', 'code': code, 'message': message})}\n\n"


def create_chunk_event(content: str, model: str, provider: str) -> str:
    """Create a formatted SSE chunk event."""
    return f"data: {json.dumps({'type': 'chunk', 'content': content, 'model': model, 'provider': provider})}\n\n"


def create_done_event(usage: dict) -> str:
    """Create a formatted SSE done event."""
    return f"data: {json.dumps({'type': 'done', 'usage': usage})}\n\n"


# ============================================================================
# REST Endpoints
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a simple interactive demo page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>StratifyAI Demo</title>
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                background: #1a1a2e;
                color: #eee;
            }
            h1 { color: #00d4ff; }
            .container { display: flex; flex-direction: column; gap: 16px; }
            .input-group { display: flex; gap: 8px; }
            select, input, button {
                padding: 12px;
                border: 1px solid #333;
                border-radius: 8px;
                font-size: 14px;
                background: #16213e;
                color: #eee;
            }
            input { flex: 1; }
            button {
                background: #00d4ff;
                color: #1a1a2e;
                border: none;
                cursor: pointer;
                font-weight: 600;
            }
            button:hover { background: #00b8e6; }
            button:disabled { background: #444; color: #888; cursor: not-allowed; }
            #output {
                background: #16213e;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 16px;
                min-height: 200px;
                white-space: pre-wrap;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 14px;
                line-height: 1.5;
            }
            #usage {
                background: #0f3460;
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
            }
            .streaming { border-color: #00d4ff !important; }
        </style>
    </head>
    <body>
        <h1>🚀 StratifyAI Demo</h1>
        <div class="container">
            <div class="input-group">
                <select id="model">
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="claude-sonnet-4-5-20250929">Claude Sonnet</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="deepseek-chat">DeepSeek Chat</option>
                    <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
                </select>
                <input type="text" id="prompt" placeholder="Enter your message..." value="Write a haiku about coding">
                <button id="send" onclick="sendMessage()">Send</button>
            </div>
            <div id="output"></div>
            <div id="usage"></div>
        </div>
        
        <script>
            async function sendMessage() {
                const model = document.getElementById('model').value;
                const prompt = document.getElementById('prompt').value;
                const output = document.getElementById('output');
                const usage = document.getElementById('usage');
                const sendBtn = document.getElementById('send');
                
                output.textContent = '';
                output.classList.add('streaming');
                usage.textContent = '';
                sendBtn.disabled = true;
                
                try {
                    const response = await fetch('/chat/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            model: model,
                            messages: [{ role: 'user', content: prompt }]
                        })
                    });
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\\n\\n');
                        buffer = lines.pop() || '';
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const event = JSON.parse(line.slice(6));
                                
                                if (event.type === 'chunk') {
                                    output.textContent += event.content;
                                } else if (event.type === 'done') {
                                    usage.innerHTML = `
                                        <strong>Model:</strong> ${event.usage.model || model} | 
                                        <strong>Provider:</strong> ${event.usage.provider || 'unknown'} | 
                                        <strong>Tokens:</strong> ${event.usage.total_tokens} | 
                                        <strong>Cost:</strong> $${event.usage.cost_usd.toFixed(6)}
                                    `;
                                } else if (event.type === 'error') {
                                    output.textContent = `Error: ${event.message}`;
                                }
                            }
                        }
                    }
                } catch (err) {
                    output.textContent = `Error: ${err.message}`;
                } finally {
                    output.classList.remove('streaming');
                    sendBtn.disabled = false;
                }
            }
            
            // Send on Enter key
            document.getElementById('prompt').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stratifyai-web"}


@app.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available models by provider."""
    providers = {}
    for provider in client.get_supported_providers():
        providers[provider] = client.get_supported_models(provider)
    return {"providers": providers}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat completion."""
    try:
        messages = [
            Message(role=m["role"], content=m["content"]) for m in request.messages
        ]

        # Create LLM request
        llm_request = LLMChatRequest(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        response = client.chat_completion(llm_request)

        return ChatResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cost_usd": response.usage.cost_usd,
            },
        )

    except InvalidModelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Invalid API key")
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """
    Stream chat completion via Server-Sent Events (SSE).

    Event format:
        - chunk: {"type": "chunk", "content": "...", "model": "...", "provider": "..."}
        - done: {"type": "done", "usage": {...}}
        - error: {"type": "error", "code": "...", "message": "..."}
    """

    def event_generator():
        last_chunk = None

        try:
            messages = [
                Message(role=m["role"], content=m["content"]) for m in request.messages
            ]

            # Create LLM request
            llm_request = LLMChatRequest(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            for chunk in client.chat_completion_stream(llm_request):
                last_chunk = chunk
                yield create_chunk_event(
                    content=chunk.content,
                    model=chunk.model,
                    provider=chunk.provider,
                )

            # Send completion event with usage info
            if last_chunk:
                yield create_done_event(
                    {
                        "model": last_chunk.model,
                        "provider": last_chunk.provider,
                        "prompt_tokens": last_chunk.usage.prompt_tokens,
                        "completion_tokens": last_chunk.usage.completion_tokens,
                        "total_tokens": last_chunk.usage.total_tokens,
                        "cost_usd": last_chunk.usage.cost_usd,
                    }
                )

        except InvalidModelError as e:
            yield create_error_event("invalid_model", str(e))
        except InvalidProviderError as e:
            yield create_error_event("invalid_provider", str(e))
        except AuthenticationError:
            yield create_error_event("auth_error", "Invalid API key")
        except RateLimitError as e:
            yield create_error_event("rate_limit", str(e))
        except ProviderError as e:
            yield create_error_event("provider_error", str(e))
        except Exception as e:
            yield create_error_event("unknown", str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional chat streaming.

    Client sends:
        {"type": "chat", "model": "...", "messages": [...], "temperature": 0.7}

    Server sends:
        - chunk: {"type": "chunk", "content": "..."}
        - done: {"type": "done", "usage": {...}}
        - error: {"type": "error", "code": "...", "message": "..."}
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                try:
                    messages = [
                        Message(role=m["role"], content=m["content"])
                        for m in data["messages"]
                    ]

                    llm_request = LLMChatRequest(
                        model=data["model"],
                        messages=messages,
                        temperature=data.get("temperature", 0.7),
                        max_tokens=data.get("max_tokens"),
                        stream=True,
                    )

                    last_chunk = None

                    # Stream response back to client
                    for chunk in client.chat_completion_stream(llm_request):
                        last_chunk = chunk
                        await websocket.send_json(
                            {
                                "type": "chunk",
                                "content": chunk.content,
                                "model": chunk.model,
                                "provider": chunk.provider,
                            }
                        )
                        # Allow other tasks to run
                        await asyncio.sleep(0)

                    # Send completion event
                    if last_chunk:
                        await websocket.send_json(
                            {
                                "type": "done",
                                "usage": {
                                    "model": last_chunk.model,
                                    "provider": last_chunk.provider,
                                    "total_tokens": last_chunk.usage.total_tokens,
                                    "cost_usd": last_chunk.usage.cost_usd,
                                },
                            }
                        )

                except InvalidModelError as e:
                    await websocket.send_json(
                        {"type": "error", "code": "invalid_model", "message": str(e)}
                    )
                except AuthenticationError:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "auth_error",
                            "message": "Invalid API key",
                        }
                    )
                except RateLimitError as e:
                    await websocket.send_json(
                        {"type": "error", "code": "rate_limit", "message": str(e)}
                    )
                except Exception as e:
                    await websocket.send_json(
                        {"type": "error", "code": "unknown", "message": str(e)}
                    )

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("Starting StratifyAI Web Server...")
    print("Open http://localhost:8000 in your browser for the demo")
    uvicorn.run(app, host="0.0.0.0", port=8000)
