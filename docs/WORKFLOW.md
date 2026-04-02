# StratifyAI Workflow with Integrated Profiles  

This workflow reflects how StratifyAI unifies providers, models, profiles, prompt templates, and user input into a single predictable pipeline.

### 1. Provider Selection  
Choosing a provider defines the API surface, capabilities, latency, and cost structure. Providers differ in reasoning strength, context window, and modality support, so this step sets the boundaries for everything that follows.

- OpenAI for balanced reasoning and broad support  
- Anthropic for long-context and safety  
- Amazon Bedrock for enterprise integration  
- Google Gemini for multimodal strength  

---

### 2. Model Selection  
Once the provider is chosen, the model determines context window, reasoning power, speed, and cost. StratifyAI abstracts these differences so models can be swapped without rewriting prompts.

Examples include:  
- GPT‑4.1  
- Claude 3.7 Sonnet  
- Gemini 2.0 Flash  
- Llama 3.3  

---

### 3. Profile Selection
> **Status: Planned — not yet implemented.** Profile parameters are currently configured manually per-request via the ChatBuilder API or UI config tab.

Profiles are reusable configuration bundles that will define *how* the model behaves before any prompt template is applied. They will standardize:

- temperature and randomness  
- max tokens  
- reasoning depth  
- speed vs. accuracy tradeoffs  
- cost sensitivity  
- multimodal or vision usage  
- JSON or schema enforcement  
- tool availability  

Profiles will make the system predictable across providers and models.

Planned StratifyAI profile types include:

- **fast** — low latency, low cost, minimal reasoning  
- **balanced** — general-purpose, stable outputs  
- **reasoning** — deeper chain-of-thought, higher accuracy  
- **vision** — multimodal input/output  
- **json** — strict schema enforcement  
- **cheap** — cost-optimized for high-volume tasks  

Profiles will allow StratifyAI to behave consistently even when the underlying model changes.

---

### 4. Prompt Template Selection  
Templates define the structure, tone, constraints, and formatting of the output. They are provider‑agnostic and reusable across tasks.

Examples include:

- **Summarization**  
- **Analysis**  
- **Email drafting**  
- **Code explanation**  
- **RAG templates**  

Templates ensure consistent output across providers and models.

---

### 5. User Input  
User input fills the template’s variables. It may be:

- text  
- documents  
- images  
- structured payloads  
- conversation turns  

StratifyAI’s large‑file intelligence and chunking logic operate here.

---

### 6. Execution  
StratifyAI assembles:

- provider  
- model  
- profile  
- template  
- user input  
- parameters  

It then executes the request with streaming, cost tracking, and unified error handling.

---

### 7. Post‑Processing  
Depending on the template and profile, StratifyAI may apply:

- JSON validation  
- schema enforcement  
- markdown rendering  
- cost reporting  
- summarization  
- extraction of structured fields  

This step ensures outputs are production‑ready.

---

## Full Workflow Summary  
The complete StratifyAI pipeline becomes:

1. **Provider**  
2. **Model**  
3. **Profile**  
4. **Prompt Template**  
5. **User Input**  
6. **Execution**  
7. **Post‑Processing**

Profiles are the glue that make the system predictable, scalable, and provider‑agnostic.

