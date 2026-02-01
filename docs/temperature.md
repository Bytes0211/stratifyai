In an AI prompt/response context, **temperature** is a setting that controls how *creative, random, or deterministic* the model’s output will be. It’s one of the most important knobs you can turn when shaping an LLM’s behavior.

Here’s the simplest way to think about it:

# 🔥 Temperature = Creativity vs. Predictability

- **Low temperature (0.0–0.3)**  
  The model becomes *focused, precise, and deterministic*.  
  It picks the most likely next word almost every time.  
  Great for:  
  - factual answers  
  - coding  
  - math  
  - instructions  
  - summarization  

- **Medium temperature (0.4–0.7)**  
  Balanced, natural, conversational.  
  Good for:  
  - general chat  
  - brainstorming  
  - rewriting  
  - explanations  

- **High temperature (0.8–1.5)**  
  The model becomes *creative, surprising, and more random*.  
  It explores less likely word choices.  
  Great for:  
  - creative writing  
  - ideation  
  - fiction  
  - metaphors  
  - unusual or diverse outputs  

---

# 🎯 Why Temperature Matters

Temperature affects **probability distribution**.  
A low temperature sharpens the distribution → the model chooses the highest‑probability token.  
A high temperature flattens the distribution → the model samples from a wider range of possibilities.

In practice:

| Temperature | Behavior | Example |
|-------------|----------|---------|
| **0.0** | Deterministic | Always gives the same answer |
| **0.2** | Precise | “The capital of France is Paris.” |
| **0.7** | Balanced | “Paris is known for art, food, and culture.” |
| **1.2** | Creative | “Paris feels like a living poem stitched together with light.” |

---

# 🧠 How it fits into your work (StratumAI)

Temperature becomes part of your **unified request schema**, letting you:

- Normalize behavior across providers  
- Tune creativity per model  
- Let the router choose temperature dynamically  
- Provide consistent defaults across OpenAI, Anthropic, Google, etc.  

It’s one of the few parameters that behaves consistently across all major LLM APIs.

---
