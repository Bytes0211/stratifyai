# Large File Upload Strategies for Token Limit Management

## Problem Statement
When uploading files to LLMs, you face token limits that vary by provider:
- **Standard models**: 128k-200k tokens (GPT-4, Claude Sonnet)
- **Long context models**: 200k-1M tokens (o1, Claude Opus 4.5, Gemini 2.5)
- **Ultra-long context**: 1M-1.8M tokens (Gemini 2.5, Grok 4.1)

**Token estimation**: ~1 token ≈ 4 characters (rough approximation)
- 128k tokens ≈ 512KB of text
- 200k tokens ≈ 800KB of text  
- 1M tokens ≈ 4MB of text

## Current Implementation

### File Upload Constraints (cli/stratifyai_cli.py)
```python
MAX_FILE_SIZE_MB = 5          # Hard limit on file size
LARGE_FILE_THRESHOLD_KB = 500 # Warn users about large files
```

### Token Limit Management
```python
# Interactive mode reserves 80% for history, 20% for response
max_history_tokens = int(context_window * 0.8)

# Truncation strategy: Remove oldest conversation pairs when limit exceeded
if estimated_tokens > max_history_tokens:
    # Remove oldest user/assistant message pairs
    conversation_messages = conversation_messages[2:]
```

## Solutions for Large File Uploads

### Solution 1: Smart Chunking with Summarization
**Best for**: Large documents that need full analysis

```python
def chunk_and_summarize(file_content: str, chunk_size: int = 50000):
    """
    Split large files into chunks and progressively summarize.
    
    Strategy:
    1. Split file into manageable chunks
    2. Summarize each chunk
    3. Combine summaries for final context
    """
    chunks = [file_content[i:i+chunk_size] 
              for i in range(0, len(file_content), chunk_size)]
    
    summaries = []
    for i, chunk in enumerate(chunks):
        # Use cheaper model for summarization
        summary_prompt = f"Summarize this section (part {i+1}/{len(chunks)}):\n\n{chunk}"
        summary = llm_client.chat_completion(
            ChatRequest(
                model="gpt-4o-mini",  # Cheaper model
                messages=[Message(role="user", content=summary_prompt)],
                max_tokens=1000
            )
        )
        summaries.append(summary.content)
    
    # Combine summaries
    return "\n\n---\n\n".join(summaries)
```

**Implementation in CLI:**
```python
@app.command()
def upload_large(
    file: Path,
    provider: str,
    model: str,
    summarize: bool = typer.Option(True, help="Auto-summarize large files"),
    chunk_size: int = typer.Option(50000, help="Characters per chunk")
):
    """Upload and process large files with automatic chunking."""
    content = file.read_text()
    
    if len(content) > chunk_size and summarize:
        console.print("[yellow]File too large, using chunked summarization...[/yellow]")
        processed_content = chunk_and_summarize(content, chunk_size)
    else:
        processed_content = content
    
    # Continue with normal processing
    ...
```

### Solution 2: Intelligent Extraction
**Best for**: Structured documents (logs, CSV, JSON)

```python
def extract_relevant_sections(file_content: str, query: str, max_tokens: int = 100000):
    """
    Extract only relevant sections based on user query.
    
    Strategy:
    1. Parse file structure
    2. Search for relevant sections
    3. Extract only what's needed
    """
    # For CSV/tabular data
    if file_path.suffix == '.csv':
        df = pd.read_csv(file_path)
        # Extract sample + statistics instead of full data
        summary = {
            "rows": len(df),
            "columns": list(df.columns),
            "sample": df.head(10).to_string(),
            "stats": df.describe().to_string(),
            "dtypes": df.dtypes.to_string()
        }
        return json.dumps(summary, indent=2)
    
    # For JSON
    elif file_path.suffix == '.json':
        data = json.loads(file_content)
        # Extract schema + sample instead of full data
        return extract_json_schema_sample(data)
    
    # For logs
    elif file_path.suffix == '.log':
        lines = file_content.splitlines()
        # Extract errors/warnings + sample
        errors = [l for l in lines if 'ERROR' in l or 'WARN' in l]
        return f"Errors/Warnings:\n{chr(10).join(errors[:100])}\n\nTotal lines: {len(lines)}"
```

**Implementation in CLI:**
```python
@app.command()
def analyze_file(
    file: Path,
    query: Optional[str] = None,
    extract_mode: str = typer.Option(
        "smart",
        help="Extraction mode: full, smart, sample, schema"
    )
):
    """Intelligently analyze large files."""
    if extract_mode == "smart":
        content = extract_relevant_sections(file, query)
    elif extract_mode == "sample":
        content = file.read_text()[:50000]  # First 50k chars
    elif extract_mode == "schema":
        content = extract_schema_only(file)
    else:
        content = file.read_text()
    ...
```

### Solution 3: Use Long-Context Models
**Best for**: When you truly need full file context

```python
# Model selection based on file size
def select_model_for_file_size(file_size_chars: int) -> tuple[str, str]:
    """Auto-select model based on file size."""
    estimated_tokens = file_size_chars // 4
    
    if estimated_tokens < 100000:
        return "openai", "gpt-4o"  # 128k context
    elif estimated_tokens < 180000:
        return "openai", "o1"  # 200k context
    elif estimated_tokens < 900000:
        return "google", "gemini-2.5-pro"  # 1M context
    else:
        return "openrouter", "x-ai/grok-4.1-fast"  # 1.8M context
```

**Implementation in CLI:**
```python
@app.command()
def upload(
    file: Path,
    auto_select_model: bool = typer.Option(
        True,
        help="Auto-select model based on file size"
    )
):
    """Upload file with automatic model selection."""
    content = file.read_text()
    
    if auto_select_model:
        provider, model = select_model_for_file_size(len(content))
        console.print(f"[cyan]Auto-selected {provider}/{model} for {len(content):,} chars[/cyan]")
    
    # Continue with upload
    ...
```

### Solution 4: Prompt Caching (Anthropic/OpenAI)
**Best for**: Multiple queries on same large file

```python
def upload_with_caching(file_content: str, provider: str, model: str):
    """
    Use prompt caching to avoid re-uploading file context.
    
    Strategy:
    1. Mark large file content as cacheable
    2. First request: Full cost
    3. Subsequent requests: ~90% cheaper for cached content
    """
    # Mark file content for caching (Anthropic/OpenAI)
    messages = [
        Message(
            role="user",
            content=f"[File Context - Cache This]\n\n{file_content}",
            cache_control={"type": "ephemeral"}  # Anthropic caching
        )
    ]
    
    # First query incurs full cost + cache write
    response = client.chat_completion(
        ChatRequest(model=model, messages=messages)
    )
    
    # Subsequent queries use cached context (~90% cheaper)
    messages.append(Message(role="assistant", content=response.content))
    messages.append(Message(role="user", content="Follow-up question..."))
    
    response2 = client.chat_completion(
        ChatRequest(model=model, messages=messages)
    )
```

**Implementation in CLI:**
```python
@app.command()
def interactive_cached(
    file: Path,
    provider: str = "anthropic",  # Best caching support
    model: str = "claude-sonnet-4-5"
):
    """Interactive session with file caching."""
    content = file.read_text()
    
    # Initial message with cache control
    messages = [
        Message(
            role="user",
            content=f"[Context from {file.name}]\n\n{content}",
            cache_control={"type": "ephemeral"}
        )
    ]
    
    console.print("[yellow]File cached - subsequent queries will be ~90% cheaper[/yellow]")
    
    while True:
        user_query = Prompt.ask("Query")
        if user_query.lower() == 'exit':
            break
        
        messages.append(Message(role="user", content=user_query))
        response = client.chat_completion(ChatRequest(model=model, messages=messages))
        
        # Show cache savings
        if response.usage.cache_read_tokens > 0:
            savings = response.usage.cache_read_tokens * 0.9
            console.print(f"[green]Cache hit! Saved ~{savings:.0f} tokens cost[/green]")
        
        messages.append(Message(role="assistant", content=response.content))
        console.print(response.content)
```

### Solution 5: Streaming Uploads for RAG
**Best for**: Very large files (>5MB)

```python
def create_vector_db(file_path: Path):
    """
    Create vector database for semantic search instead of direct upload.
    
    Strategy:
    1. Split file into chunks
    2. Create embeddings for each chunk
    3. Store in vector DB (ChromaDB, Pinecone, etc.)
    4. Query relevant chunks only
    """
    import chromadb
    
    # Split into chunks
    content = file_path.read_text()
    chunks = split_into_chunks(content, chunk_size=1000)
    
    # Create vector DB
    client = chromadb.Client()
    collection = client.create_collection(file_path.stem)
    
    # Add chunks with embeddings
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            ids=[f"chunk_{i}"]
        )
    
    return collection

def query_with_rag(query: str, collection, llm_client):
    """Query only relevant chunks."""
    # Semantic search for top-k relevant chunks
    results = collection.query(query_texts=[query], n_results=5)
    
    # Combine only relevant chunks
    context = "\n\n---\n\n".join(results['documents'][0])
    
    # Send to LLM with reduced context
    response = llm_client.chat_completion(
        ChatRequest(
            model="gpt-4o",
            messages=[
                Message(role="user", content=f"Context:\n{context}\n\nQuery: {query}")
            ]
        )
    )
    
    return response.content
```

### Solution 6: Compression Techniques
**Best for**: Repetitive or structured data

```python
def compress_content(file_content: str, mode: str = "auto"):
    """
    Intelligently compress content before upload.
    
    Strategies:
    - Remove whitespace/formatting
    - De-duplicate repeated sections
    - Extract key information only
    """
    if mode == "minify":
        # Remove extra whitespace
        import re
        compressed = re.sub(r'\s+', ' ', file_content)
        return compressed.strip()
    
    elif mode == "deduplicate":
        # Remove duplicate lines/sections
        lines = file_content.splitlines()
        unique_lines = []
        seen = set()
        for line in lines:
            if line not in seen:
                unique_lines.append(line)
                seen.add(line)
        return "\n".join(unique_lines)
    
    elif mode == "structured":
        # For code files: extract functions/classes only
        # For logs: extract unique error patterns
        # For CSV: extract schema + sample
        return extract_structured_info(file_content)
```

## Recommended Strategy by File Type

| File Type | Recommended Solution | Why |
|-----------|---------------------|-----|
| **Code files** | Solution 2: Intelligent Extraction | Extract functions/classes, ignore boilerplate |
| **Large docs** | Solution 1: Chunking + Summarization | Progressive summarization preserves meaning |
| **CSV/Data** | Solution 2: Schema + Sample | Schema + statistics + sample rows sufficient |
| **Logs** | Solution 2: Error Extraction | Extract errors/warnings, ignore routine logs |
| **JSON/Config** | Solution 2: Schema Extraction | Schema + sample values enough |
| **Research papers** | Solution 4: Prompt Caching | Re-query same paper multiple times |
| **Massive datasets** | Solution 5: RAG/Vector DB | Only retrieve relevant sections |

## Implementation Roadmap

### Phase 1: Enhanced File Upload (Week 1)
- [ ] Add `--chunk-size` parameter to commands
- [ ] Implement automatic chunking for files >500KB
- [ ] Add warning for files exceeding model context
- [ ] Display token count estimates before upload

### Phase 2: Intelligent Extraction (Week 2)
- [ ] Add file type detection
- [ ] Implement CSV/JSON schema extraction
- [ ] Add log file error extraction
- [ ] Create `--extract-mode` parameter

### Phase 3: Model Auto-Selection (Week 3)
- [ ] Implement file size → model mapping
- [ ] Add `--auto-select-model` flag
- [ ] Display model selection reasoning
- [ ] Cost estimation before upload

### Phase 4: Advanced Features (Week 4)
- [ ] Implement prompt caching support
- [ ] Add RAG/vector DB integration (optional)
- [ ] Create file compression utilities
- [ ] Add multi-file upload with merge strategies

## CLI Usage Examples

### Current Usage (Basic)
```bash
# Upload file with size warnings
stratifyai interactive --file large_doc.txt --provider openai --model gpt-4o

# Warning: File too large: 2.3 MB
# This will consume substantial tokens and may incur significant costs
# Continue loading this file? [y/N]
```

### Enhanced Usage (Proposed)
```bash
# Auto-select model based on file size
stratifyai upload large_doc.txt --auto-select-model
# → Auto-selected google/gemini-2.5-pro for 1,234,567 chars (1M context)

# Chunk and summarize large file
stratifyai upload huge_log.txt --chunked --chunk-size 50000
# → Processing in 12 chunks, summarizing...

# Extract only relevant data
stratifyai analyze data.csv --extract-mode schema
# → Extracting schema + sample (200 rows) from 1M row dataset

# Use caching for multiple queries
stratifyai interactive-cached report.pdf --provider anthropic
# → File cached - subsequent queries will be ~90% cheaper

# Intelligent extraction by file type
stratifyai analyze error.log --extract errors
# → Extracted 234 errors from 50,000 log lines
```

## Cost Optimization

### Without Optimization
```
File: 2MB text file ≈ 500k tokens
Model: gpt-4o ($2.5 per 1M input tokens)
Cost: ~$1.25 per upload
```

### With Chunking + Summarization
```
File: 2MB → 10 chunks of 50k tokens each
Summarize each chunk: 10 × 50k = 500k tokens @ gpt-4o-mini ($0.15 per 1M)
Final summary: ~10k tokens
Total cost: ~$0.075 (94% savings!)
```

### With Prompt Caching (Anthropic)
```
First upload: 500k tokens @ $3/1M = $1.50
Cache write: 500k tokens @ $3.75/1M = $1.88
Total first query: $3.38

Subsequent queries (cached):
Cache read: 500k tokens @ $0.30/1M = $0.15 (90% savings!)
```

## Testing

Create test files:
```bash
# Generate large test file
python -c "print('x' * 1000000)" > test_1mb.txt

# Test chunking
stratifyai upload test_1mb.txt --chunked --chunk-size 100000

# Test auto-select
stratifyai upload test_1mb.txt --auto-select-model
```

## Future Enhancements

1. **Intelligent file splitting**: Split at natural boundaries (paragraphs, functions, etc.)
2. **Multi-modal support**: Handle images, PDFs with OCR
3. **Streaming processing**: Process files in real-time as they're read
4. **Cost preview**: Show estimated cost before upload
5. **Resume capability**: Resume interrupted large uploads
6. **Batch processing**: Process multiple files efficiently

## References

- [Anthropic Prompt Caching](https://docs.anthropic.com/claude/docs/prompt-caching)
- [OpenAI Context Management](https://platform.openai.com/docs/guides/prompt-engineering)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
