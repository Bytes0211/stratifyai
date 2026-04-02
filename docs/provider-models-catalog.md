# StratifyAI Provider & Model Catalog

**Document Version:** 1.0  
**Validation Date:** January 31, 2026  
**Status:** All providers configured and tested ✅

---

## Overview

This document lists all configured and tested LLM providers in StratifyAI along with their available models. All providers listed below have been implemented, tested, and are operational.

**Total Providers:** 8  
**Total Models Available:** 30

---

## Provider Status Summary

| Provider | Status | Models Available | API Type | Requires API Key |
|----------|--------|------------------|----------|------------------|
| OpenAI | ✅ Operational | 15 | Native | Yes |
| Anthropic | ✅ Operational | 3 | Native | Yes |
| Google (Gemini) | ✅ Operational | 3 | OpenAI-Compatible | Yes |
| DeepSeek | ✅ Operational | 2 | OpenAI-Compatible | Yes |
| Groq | ✅ Operational | 3 | OpenAI-Compatible | Yes |
| Grok (X.AI) | ✅ Operational | 1 | OpenAI-Compatible | Yes |
| OpenRouter | ✅ Operational | 2+ | OpenAI-Compatible | Yes |
| Ollama | ✅ Operational | 3+ | OpenAI-Compatible | No (Local) |

---

## 1. OpenAI Provider

**Provider Name:** `openai`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `OPENAI_API_KEY`  
**Implementation:** Native OpenAI SDK  
**Temperature Range:** 0.0 - 2.0

### Available Models (15)

#### Production Models
1. **gpt-4o**
   - Context: 128,000 tokens
   - Cost: $2.50 input / $10.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

2. **gpt-4o-mini**
   - Context: 128,000 tokens
   - Cost: $0.15 input / $0.60 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

3. **gpt-4-turbo**
   - Context: 128,000 tokens
   - Cost: $10.00 input / $30.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓

4. **gpt-4**
   - Context: 8,192 tokens
   - Cost: $30.00 input / $60.00 output (per 1M tokens)
   - Features: Tools ✓

5. **gpt-3.5-turbo**
   - Context: 16,385 tokens
   - Cost: $0.50 input / $1.50 output (per 1M tokens)
   - Features: Tools ✓

#### Reasoning Models (O-Series)
6. **o1**
   - Context: 200,000 tokens
   - Cost: $15.00 input / $60.00 output (per 1M tokens)
   - Features: Reasoning model (fixed temperature)

7. **o1-mini**
   - Context: 128,000 tokens
   - Cost: $3.00 input / $12.00 output (per 1M tokens)
   - Features: Reasoning model (fixed temperature)

8. **o3-mini**
   - Context: 200,000 tokens
   - Cost: $1.10 input / $4.40 output (per 1M tokens)
   - Features: Reasoning model (fixed temperature)

9. **o1-preview**
   - Context: 128,000 tokens
   - Cost: $15.00 input / $60.00 output (per 1M tokens)
   - Features: Reasoning model (fixed temperature)

10. **o1-2024-12-17**
    - Context: 200,000 tokens
    - Cost: $15.00 input / $60.00 output (per 1M tokens)
    - Features: Reasoning model (fixed temperature)

11. **o1-mini-2024-09-12**
    - Context: 128,000 tokens
    - Cost: $3.00 input / $12.00 output (per 1M tokens)
    - Features: Reasoning model (fixed temperature)

#### Future Models (Placeholders)
12. **gpt-5**
    - Context: 128,000 tokens
    - Cost: $10.00 input / $30.00 output (per 1M tokens)
    - Features: Vision ✓, Tools ✓, Caching ✓

13. **gpt-5-mini**
    - Context: 128,000 tokens
    - Cost: $2.00 input / $6.00 output (per 1M tokens)
    - Features: Vision ✓, Tools ✓, Caching ✓

14. **gpt-5-nano**
    - Context: 128,000 tokens
    - Cost: $1.00 input / $3.00 output (per 1M tokens)
    - Features: Tools ✓

15. **gpt-4.1**
    - Context: 128,000 tokens
    - Cost: $2.50 input / $10.00 output (per 1M tokens)
    - Features: Vision ✓, Tools ✓, Caching ✓

---

## 2. Anthropic Provider

**Provider Name:** `anthropic`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `ANTHROPIC_API_KEY`  
**Implementation:** Native Anthropic Messages API  
**Temperature Range:** 0.0 - 1.0

### Available Models (3)

1. **claude-3-5-sonnet-20241022**
   - Context: 200,000 tokens
   - Cost: $3.00 input / $15.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

2. **claude-3-5-haiku-20241022**
   - Context: 200,000 tokens
   - Cost: $0.80 input / $4.00 output (per 1M tokens)
   - Features: Tools ✓, Caching ✓

3. **claude-3-opus-20240229**
   - Context: 200,000 tokens
   - Cost: $15.00 input / $75.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

---

## 3. Google Gemini Provider

**Provider Name:** `google`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `GOOGLE_API_KEY`  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `https://generativelanguage.googleapis.com/v1beta/openai/`  
**Temperature Range:** 0.0 - 2.0

### Available Models (3)

1. **gemini-2.5-pro**
   - Context: 1,000,000 tokens
   - Cost: $1.25 input / $5.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

2. **gemini-2.5-flash**
   - Context: 1,000,000 tokens
   - Cost: $0.075 input / $0.30 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓, Caching ✓

3. **gemini-2.5-flash-lite**
   - Context: 1,000,000 tokens
   - Cost: Free ($0.00 input / $0.00 output)
   - Features: Limited (no vision, no tools)

---

## 4. DeepSeek Provider

**Provider Name:** `deepseek`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `DEEPSEEK_API_KEY`  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `https://api.deepseek.com`  
**Temperature Range:** 0.0 - 2.0

### Available Models (2)

1. **deepseek-chat**
   - Context: 64,000 tokens
   - Cost: $0.14 input / $0.28 output (per 1M tokens)
   - Features: Tools ✓

2. **deepseek-reasoner**
   - Context: 64,000 tokens
   - Cost: $0.55 input / $2.19 output (per 1M tokens)
   - Features: Reasoning model (fixed temperature)

---

## 5. Groq Provider

**Provider Name:** `groq`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `GROQ_API_KEY`  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `https://api.groq.com/openai/v1`  
**Temperature Range:** 0.0 - 2.0

### Available Models (3)

1. **llama-3.1-70b-versatile**
   - Context: 131,072 tokens
   - Cost: $0.59 input / $0.79 output (per 1M tokens)
   - Features: Tools ✓

2. **llama-3.1-8b-instant**
   - Context: 131,072 tokens
   - Cost: $0.05 input / $0.08 output (per 1M tokens)
   - Features: Tools ✓

3. **mixtral-8x7b-32768**
   - Context: 32,768 tokens
   - Cost: $0.24 input / $0.24 output (per 1M tokens)
   - Features: Tools ✓

---

## 6. Grok (X.AI) Provider

**Provider Name:** `grok`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `GROK_API_KEY`  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `https://api.x.ai/v1`  
**Temperature Range:** 0.0 - 2.0

### Available Models (1)

1. **grok-beta**
   - Context: 131,072 tokens
   - Cost: $5.00 input / $15.00 output (per 1M tokens)
   - Features: Tools ✓

---

## 7. OpenRouter Provider

**Provider Name:** `openrouter`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `OPENROUTER_API_KEY`  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `https://openrouter.ai/api/v1`  
**Temperature Range:** 0.0 - 2.0

### Available Models (2+)

1. **anthropic/claude-3-5-sonnet**
   - Context: 200,000 tokens
   - Cost: $3.00 input / $15.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓

2. **openai/gpt-4-turbo**
   - Context: 128,000 tokens
   - Cost: $10.00 input / $30.00 output (per 1M tokens)
   - Features: Vision ✓, Tools ✓

**Note:** OpenRouter supports many more models. Additional models can be added to the catalog as needed.

---

## 8. Ollama Provider

**Provider Name:** `ollama`  
**Status:** ✅ Operational  
**API Key Environment Variable:** `OLLAMA_API_KEY` (optional - runs locally)  
**Implementation:** OpenAI-Compatible API  
**Base URL:** `http://localhost:11434/v1`  
**Temperature Range:** 0.0 - 2.0

### Available Models (3+)

1. **llama3.2**
   - Context: 128,000 tokens
   - Cost: Free (local)
   - Features: Local model

2. **mistral**
   - Context: 32,768 tokens
   - Cost: Free (local)
   - Features: Local model

3. **codellama**
   - Context: 16,384 tokens
   - Cost: Free (local)
   - Features: Local model

**Note:** Ollama supports any locally installed model. Additional models can be pulled and used via `ollama pull <model-name>`.

---

## Model Selection Guide

### By Use Case

**General Purpose (Best Quality):**
- `gpt-4o` (OpenAI)
- `claude-3-5-sonnet-20241022` (Anthropic)
- `gemini-2.5-pro` (Google)

**Cost-Effective:**
- `gpt-4o-mini` (OpenAI) - $0.15/$0.60
- `gemini-2.5-flash` (Google) - $0.075/$0.30
- `deepseek-chat` (DeepSeek) - $0.14/$0.28

**Reasoning/Complex Tasks:**
- `o1` (OpenAI)
- `o3-mini` (OpenAI)
- `deepseek-reasoner` (DeepSeek)

**Vision/Multimodal:**
- `gpt-4o` (OpenAI)
- `claude-3-5-sonnet-20241022` (Anthropic)
- `gemini-2.5-pro` (Google)

**Large Context:**
- `gemini-2.5-pro` (1M tokens)
- `gemini-2.5-flash` (1M tokens)
- `o1` (200K tokens)

**Local/Private:**
- `llama3.2` (Ollama)
- `mistral` (Ollama)
- `codellama` (Ollama)

---

## Cost Comparison

**Cheapest Models (Input Cost per 1M tokens):**
1. Free: `gemini-2.5-flash-lite`, All Ollama models
2. $0.05: `llama-3.1-8b-instant` (Groq)
3. $0.075: `gemini-2.5-flash` (Google)
4. $0.14: `deepseek-chat` (DeepSeek)
5. $0.15: `gpt-4o-mini` (OpenAI)

**Most Expensive Models (Input Cost per 1M tokens):**
1. $30.00: `gpt-4` (OpenAI)
2. $15.00: `claude-3-opus-20240229` (Anthropic), `o1` series (OpenAI)
3. $10.00: `gpt-4-turbo` (OpenAI)
4. $5.00: `grok-beta` (Grok)

---

## Feature Matrix

| Feature | Providers |
|---------|-----------|
| **Vision Support** | OpenAI (gpt-4o, gpt-4-turbo), Anthropic (claude-3-5-sonnet, claude-3-opus), Google (gemini-2.5-pro, gemini-2.5-flash), OpenRouter (select models) |
| **Function/Tool Calling** | All providers except Ollama and reasoning models |
| **Prompt Caching** | OpenAI (gpt-4o, gpt-4o-mini), Anthropic (all Claude 3.5 models), Google (gemini-2.5-pro, gemini-2.5-flash) |
| **Reasoning Models** | OpenAI (o1/o3 series), DeepSeek (deepseek-reasoner) |
| **Streaming** | All providers ✓ |
| **Free Tier** | Gemini (flash-lite), Ollama (all local models) |

---

## Usage Examples

### OpenAI
```python
from stratifyai import LLMClient

client = LLMClient(provider="openai", api_key="sk-...")
response = client.chat_completion("gpt-4o", messages=[...])
```

### Anthropic
```python
client = LLMClient(provider="anthropic", api_key="sk-ant-...")
response = client.chat_completion("claude-3-5-sonnet-20241022", messages=[...])
```

### Google Gemini
```python
client = LLMClient(provider="google", api_key="...")
response = client.chat_completion("gemini-2.5-flash", messages=[...])
```

### Ollama (Local)
```python
client = LLMClient(provider="ollama")  # No API key needed
response = client.chat_completion("llama3.2", messages=[...])
```

---

## Environment Variables

All API keys should be set as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export GROQ_API_KEY="..."
export GROK_API_KEY="..."
export OPENROUTER_API_KEY="..."
# OLLAMA_API_KEY not required for local usage
```

---

## Notes

- **Validation Status:** All 8 providers have been implemented and tested (Phase 2 complete as of Jan 30, 2026)
- **Test Coverage:** 77 unit tests passing across all providers
- **Model Availability:** Some models (e.g., gpt-5 series) are placeholders for future releases
- **Dynamic Models:** OpenRouter and Ollama support additional models not listed here
- **Cost Tracking:** All providers include automatic cost calculation per request
- **Streaming Support:** All providers support streaming responses via `chat_completion_stream()`
- **Temperature Validation:** All providers validate temperature ranges before API calls (Anthropic: 0.0-1.0, Others: 0.0-2.0)

---

## Document Maintenance

**Last Updated:** January 31, 2026  
**Next Review:** Phase 3 completion (Advanced Features)  
**Update Frequency:** After each phase or when new models are added

For technical implementation details, see:
- `llm_abstraction/config.py` - Model catalog and pricing
- `llm_abstraction/providers/` - Provider implementations
- `docs/stratifyai-technical-approach.md` - Complete technical design

---

## Temperature Constraints

Different providers have different temperature validation requirements:

- **Anthropic (Claude):** 0.0 to 1.0
- **OpenAI:** 0.0 to 2.0
- **Google (Gemini):** 0.0 to 2.0
- **DeepSeek:** 0.0 to 2.0
- **Groq:** 0.0 to 2.0
- **Grok (X.AI):** 0.0 to 2.0
- **OpenRouter:** 0.0 to 2.0
- **Ollama:** 0.0 to 2.0

The library automatically validates temperature parameters before making API calls and raises a `ValidationError` if the temperature is out of the valid range for the provider.

---

**Document Status:** ✅ Current and validated  
**Project Phase:** Phase 2 Complete → Phase 3 In Progress
