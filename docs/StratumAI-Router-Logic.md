# **StratumAI Routing System: Intelligent Model Selection Across Providers**

## A complete guide to StratumAI’s multi‑provider routing engine, including strategies, complexity analysis, capability filtering, fallback chains, and extraction‑specific routing.

StratumAI’s Router is the intelligence layer that selects the optimal LLM model for any given task. It evaluates cost, quality, latency, capabilities, and prompt complexity to determine the best model across nine supported providers. The router ensures that applications remain fast, cost‑efficient, and resilient — even when providers fail or workloads vary.

This guide explains how routing works, how to configure it, and how to integrate it into production‑grade LLM workflows.

---

## **1. Routing Overview**

StratumAI’s routing pipeline follows a structured decision flow:

```txt
Incoming Request
      │
      ▼
[1] Capability Filtering
      │
      ▼
[2] Complexity Analysis
      │
      ▼
[3] Candidate Model Selection
      │
      ▼
[4] Strategy Scoring
      │
      ▼
[5] Best Model Selected
      │
      ▼
[6] Optional Fallback Chain
```

This ensures that routing decisions are:

- **Accurate** — based on real metadata  
- **Adaptive** — complexity‑aware  
- **Efficient** — cost and latency optimized  
- **Resilient** — with automatic fallback support  

---

## **2. Routing Strategies**

StratumAI supports four routing strategies. Each strategy evaluates candidate models differently.

---

### **2.1 Cost‑Based Routing (`RoutingStrategy.COST`)**

Selects the **cheapest** model that satisfies all requirements.

#### **Scoring Formula**

```python
cost_score = (cost_per_1m_input + cost_per_1m_output) / 2
selected = min(candidates, key=cost_score)
```

#### **Best For**

- High‑volume workloads  
- Batch processing  
- Budget‑sensitive applications  

#### **Example**

```python
router = Router(strategy=RoutingStrategy.COST)
provider, model = router.route(
    messages=[Message(role="user", content="Summarize this text")],
    max_cost_per_1k_tokens=0.01
)
```

---

### **2.2 Quality‑Based Routing (`RoutingStrategy.QUALITY`)**

Selects the **highest‑quality** model based on benchmark scores.

#### **Scoring Formula**

```python
quality_score = model.quality_score
if complexity > 0.6 and model.reasoning_model:
    quality_score += 0.05
selected = max(candidates, key=quality_score)
```

#### **Example Quality Scores**

- gpt‑5: 0.98  
- o1: 0.96  
- claude‑3.5‑sonnet: 0.92  
- gemini‑2.5‑pro: 0.91  
- deepseek‑reasoner: 0.90  

#### **Best For**

- Complex reasoning  
- High‑stakes content  
- Enterprise decision workflows  

---

### **2.3 Latency‑Based Routing (`RoutingStrategy.LATENCY`)**

Selects the **fastest** model.

#### **Scoring Formula**

```python
selected = min(candidates, key=lambda m: m.avg_latency_ms)
```

#### **Latency Examples**

- Ollama (local): 100–120ms  
- Groq: 200–400ms  
- Gemini Flash: 600–1000ms  
- GPT‑4.1‑mini: ~800ms  
- Claude Haiku: ~1200ms  
- Reasoning models: 5000–10000ms  

#### **Best For**

- Real‑time chat  
- Interactive UI  
- Low‑latency applications  

---

### **2.4 Hybrid Routing (`RoutingStrategy.HYBRID`) — Default**

Balances **cost**, **quality**, and **latency** dynamically based on task complexity.

#### **Adaptive Weighting**

```python
quality_weight = 0.1 + (complexity * 0.5)
cost_weight = 0.6 - (complexity * 0.3)
latency_weight = 0.3 - (complexity * 0.2)
```

#### **Behavior**

| Complexity | Cost Weight | Quality Weight | Latency Weight |
|-----------|-------------|----------------|----------------|
| Low (0–0.3) | High | Low | Medium |
| Medium (0.3–0.6) | Balanced | Balanced | Balanced |
| High (0.6–1.0) | Lower | High | Low |

#### **Best For**

- General‑purpose workloads  
- Mixed complexity tasks  
- Applications needing both speed and quality  

---

## **3. Capability‑Based Filtering**

Before scoring, the router filters models based on required capabilities.

### **Supported Capabilities**
- `vision` — image understanding  
- `tools` — function calling  
- `reasoning` — chain‑of‑thought / deep reasoning  

### **Example**

```python
router.route(
    messages=messages,
    required_capabilities=["vision", "tools"],
    max_cost_per_1k_tokens=0.02,
    max_latency_ms=2000,
    min_context_window=100000,
)
```

---

## **4. Complexity Analysis**

StratumAI analyzes prompt complexity to adjust routing decisions.

### **Weighted Factors**

| Factor | Weight |
|--------|--------|
| Reasoning keywords | 40% |
| Text length | 20% |
| Code/technical content | 20% |
| Conversation depth | 10% |
| Mathematical content | 10% |

#### **Output**

A score from **0.0 (simple)** to **1.0 (complex)**.

```python
complexity = router._analyze_complexity(messages)
```

---

## **5. Fallback Chain Routing**

StratumAI can return a ranked list of fallback models for resilient applications.

### **Example**

```python
fallbacks = router.get_fallback_chain(
    messages=[Message(role="user", content="Explain quantum entanglement")],
    count=3,
    required_capabilities=["reasoning"],
    max_cost_per_1k_tokens=0.05,
)
```

### **Example Output**

```txt
[
  ("openai", "o3-mini"),
  ("anthropic", "claude-3-5-sonnet"),
  ("deepseek", "deepseek-reasoner")
]
```

### **Retry Integration**

```python
@with_retry(
    config=RetryConfig(max_retries=2),
    fallback_models=fallback_models,
)
def resilient_chat(client, messages, model):
    return client.chat(model=model, messages=messages)
```

---

## **6. Extraction‑Specific Routing**

Optimized routing for file analysis tasks.

### **Example**

```python
provider, model = router.route_for_extraction(
    file_type=FileType.CSV,
    extraction_mode="schema",
    max_cost_per_1k_tokens=0.02,
)
```

### **Extraction Mode Weights**

| Mode | Quality Weight | Notes |
|------|----------------|-------|
| schema | 90% | Structure detection |
| structure | 85% | Hierarchy extraction |
| errors | 80% | Boosts reasoning models |
| summary | 70% | Balanced |

---

## **7. Provider Preferences**

Developers can prioritize or exclude providers.

```python
router = Router(
    strategy=RoutingStrategy.HYBRID,
    preferred_providers=["openai", "anthropic"],
    excluded_providers=["ollama"],
)
```

---

## **8. API Reference**

### **Router Class**

```python
class Router:
    def __init__(..., strategy=RoutingStrategy.HYBRID, ...): ...
    def route(...): ...
    def get_fallback_chain(...): ...
    def route_for_extraction(...): ...
    def get_model_info(...): ...
    def list_models(...): ...
```

### **ModelMetadata**

```python
@dataclass
class ModelMetadata:
    provider: str
    model: str
    quality_score: float
    cost_per_1m_input: float
    cost_per_1m_output: float
    avg_latency_ms: float
    context_window: int
    capabilities: List[str]
    reasoning_model: bool = False
    supports_streaming: bool = True
```

### **RoutingStrategy Enum**

```python
class RoutingStrategy(str, Enum):
    COST = "cost"
    QUALITY = "quality"
    LATENCY = "latency"
    HYBRID = "hybrid"
```

---

## **9. CLI Usage**

```bash
stratumai route "Explain machine learning" --strategy hybrid
stratumai route "Summarize this text" --strategy cost
stratumai route "Quick question" --strategy latency
stratumai route "Analyze this image" --strategy quality --capability vision
```

---

## **10. Best Practices**

1. **Use HYBRID as the default**  
2. **Always specify required capabilities**  
3. **Set cost ceilings for production workloads**  
4. **Use fallback chains for reliability**  
5. **Monitor complexity scores**  
6. **Prefer providers you trust**  

---

## **11. Version History**

**v0.1.0 (2026‑02‑04)**  

- Initial router implementation  
- Four routing strategies  
- Complexity analysis  
- Capability filtering  
- Extraction routing  
- Fallback chain support  
- 33+ unit tests  

---

