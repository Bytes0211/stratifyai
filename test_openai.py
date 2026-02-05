#!/usr/bin/env python3
"""Simple script to test OpenAI chat functionality."""

from stratifyai.chat.stratifyai_openai import chat_sync

if __name__ == "__main__":
    prompt = "What is Python in one sentence?"
    print(f"Prompt: {prompt}\n")
    
    response = chat_sync(prompt)
    print(f"Response: {response.content}")
    print(f"\nModel: {response.model}")
    print(f"Tokens: {response.usage.total_tokens}")
    print(f"Cost: ${response.cost:.6f}")
