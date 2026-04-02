# Token Limit Quick Reference Guide

**Last Updated:** February 3, 2026  
**Status:** All major features implemented (Phases 7.1-7.5 complete)  
**Providers:** 9 providers including AWS Bedrock  
**Key Features:** Token estimation, chunking, extraction, auto-selection, caching, RAG/Vector DB

---

## Token Capacity by Model

| Provider | Model | Context Window | Estimated File Size |
|----------|-------|----------------|---------------------|
| OpenAI | gpt-4o | 128k tokens | ~512 KB |
| OpenAI | o1, o3-mini | 200k tokens | ~800 KB |
| Anthropic | Claude Sonnet 4.5 | 200k tokens | ~800 KB |
| Anthropic | Claude Opus 4.5 | 1M tokens* | ~4 MB* |
| Google | Gemini 2.5 Pro/Flash | 1M tokens | ~4 MB |
| OpenRouter | Grok 4.1 Fast | 1.8M tokens | ~7.2 MB |
| AWS Bedrock | Claude 3.5 Sonnet | 200k tokens | ~800 KB |
| AWS Bedrock | Llama 3.3 70B | 128k tokens | ~512 KB |
| AWS Bedrock | Titan Premier | 32k tokens | ~128 KB |

*Note: Claude Opus 4.5 has 200k API input limit despite 1M context window

## Six Solutions for Large Files

### 1. Smart Chunking (Best for: Large documents)
**Problem**: 2 MB file exceeds 128k token limit  
**Solution**: Split into chunks, summarize each, combine summaries  
**Savings**: 94% cost reduction  
**Command**: `stratifyai upload file.txt --chunked --chunk-size 50000`

### 2. Intelligent Extraction (Best for: CSV, JSON, Logs)
**Problem**: 10 MB CSV file  
**Solution**: Extract schema + sample + stats instead of full data  
**Savings**: 99%+ token reduction  
**Command**: `stratifyai analyze data.csv --extract-mode schema`

### 3. Long-Context Models (Best for: Need full context)
**Problem**: 3 MB file needs full analysis  
**Solution**: Auto-select Gemini 2.5 Pro (1M context)  
**Savings**: Fits in context (vs. failing with smaller models)  
**Command**: `stratifyai upload file.txt --auto-select-model`

### 4. Prompt Caching (Best for: Multiple queries on same file)
**Problem**: Re-analyzing same 2 MB file 10 times  
**Solution**: Cache file context, subsequent queries 90% cheaper  
**Savings**: 90% on queries 2-10  
**Command**: `stratifyai interactive-cached file.txt --provider anthropic`

### 5. RAG/Vector DB (Best for: Massive datasets >10 MB)
**Problem**: 50 MB documentation, only need relevant sections  
**Solution**: Create vector DB, semantic search relevant chunks only  
**Savings**: 95%+ token reduction  
**Implementation**: ✅ ChromaDB integration available (Phase 7.5)

### 6. Compression (Best for: Repetitive data)
**Problem**: Logs with duplicate entries  
**Solution**: De-duplicate, extract errors only  
**Savings**: 70-90% token reduction  
**Command**: `stratifyai analyze log.txt --compress deduplicate`

## Decision Tree

```
Is file < 500 KB?
├─ YES → Use current upload (no optimization needed)
└─ NO → Is file size known?
    ├─ < 4 MB → Use Solution 3: Long-context models
    ├─ 4-10 MB → Multiple queries? 
    │   ├─ YES → Use Solution 4: Prompt caching
    │   └─ NO → Use Solution 1: Chunking + summarization
    └─ > 10 MB → Use Solution 5: RAG/Vector DB

File type specific:
├─ CSV/JSON → Use Solution 2: Schema extraction
├─ Logs → Use Solution 2: Error extraction
├─ Code → Use Solution 2: Function/class extraction
└─ Documents → Use Solution 1: Chunking + summarization
```

## Implementation Priority

### ✅ Completed (Phase 7.1-7.5)
1. ✅ Token count estimation before upload (Phase 7.1)
2. ✅ Warning when file exceeds model context (Phase 7.1)
3. ✅ Smart chunking implementation (Phase 7.1)
4. ✅ Intelligent extraction for CSV/JSON/logs/code (Phase 7.2)
5. ✅ Auto-model selection based on file size (Phase 7.3)
6. ✅ Enhanced caching UI with analytics (Phase 7.4)
7. ✅ RAG/Vector DB integration with ChromaDB (Phase 7.5)
8. ✅ AWS Bedrock provider (9th provider - Feb 3, 2026)

### Future Enhancements
9. File compression utilities
10. Additional vector DB backends (Pinecone, Weaviate)
11. Advanced RAG strategies (HyDE, multi-query)

## Example Scenarios

### Scenario 1: Analyzing Large CSV
```bash
# Problem: 5 MB CSV with 1M rows
stratifyai analyze sales_data.csv --extract-mode schema

# Result: 
# - Extracted schema: 200 bytes
# - Sample 100 rows: ~20 KB
# - Statistics: ~5 KB
# Total: ~25 KB (99.5% reduction!)
```

### Scenario 2: Multiple Queries on Same Document
```bash
# Problem: Need to query 2 MB research paper 10 times
stratifyai interactive-cached paper.pdf --provider anthropic

# Cost comparison:
# Without caching: 10 queries × $1.50 = $15.00
# With caching: $3.38 + 9 × $0.15 = $4.73 (68% savings)
```

### Scenario 3: Processing Large Log File
```bash
# Problem: 10 MB log file, need to find errors
stratifyai analyze server.log --extract errors

# Result:
# - Total lines: 500,000
# - Errors extracted: 234 errors
# - Token reduction: 500k → 5k (99% reduction)
```

### Scenario 4: Very Large Document
```bash
# Problem: 8 MB documentation file
python -m cli.stratifyai_cli chat --file docs.txt --auto-select

# Result:
# - Auto-selected: google/gemini-2.5-pro (1M context)
# - File size: 8 MB ≈ 2M tokens (too large!)
# - Fallback: chunking + summarization
```

### Scenario 5: RAG for Massive Documentation (✅ Now Available)
```python
# Problem: 50 MB documentation, need to query multiple times
from stratifyai import RAGClient

rag = RAGClient()

# Index entire directory (one-time operation)
result = rag.index_directory(
    directory_path="./docs",
    collection_name="my_docs",
    chunk_size=1000
)
# Indexed 450 chunks from 50 MB → stored in vector DB

# Query with semantic search (retrieves only relevant chunks)
response = rag.query(
    collection_name="my_docs",
    query="How do I configure authentication?",
    n_results=5  # Only retrieve top 5 relevant chunks
)

# Result:
# - Retrieved: 5 most relevant chunks (~5k tokens)
# - Cost: $0.02 (vs. $25 for full 50 MB file)
# - Reduction: 99%+ token savings
# - Citations: Source attribution included
```

## Cost Comparison Table

| Approach | 2MB File | Cost (GPT-4o) | Cost (Claude Sonnet) | Notes |
|----------|----------|---------------|----------------------|-------|
| **Direct upload** | 500k tokens | $1.25 | $1.50 | May exceed limit |
| **Chunking + summary** | 10k tokens | $0.08 | $0.10 | 94% savings |
| **Schema extraction** | 5k tokens | $0.01 | $0.02 | 99% savings |
| **Long-context model** | 500k tokens | $0.63 (Gemini) | $1.50 | Fits in context |
| **Caching (2nd query)** | 500k cached | $0.13 | $0.15 | 90% savings |

## Best Practices

### DO:
✅ Estimate tokens before upload (chars ÷ 4)  
✅ Use long-context models when you need full file  
✅ Use caching for multiple queries on same file  
✅ Extract schema/sample for structured data  
✅ Chunk and summarize large documents  
✅ Show token count warnings to users  

### DON'T:
❌ Upload full 5 MB CSV when schema suffices  
❌ Re-upload same large file without caching  
❌ Use expensive models for simple summarization  
❌ Ignore token limits (requests will fail)  
❌ Upload binary files without conversion  

## Token Calculation Examples

```python
# Simple estimation
text = file.read_text()
estimated_tokens = len(text) // 4

# More accurate (requires tiktoken)
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
token_count = len(enc.encode(text))

# Check against model limits
context_window = 128000  # GPT-4o
if token_count > context_window * 0.8:
    print("Warning: File may exceed model context!")
```

## CLI Commands Quick Reference

```bash
# Interactive mode with file (includes token warnings)
python -m cli.stratifyai_cli interactive --file large.txt

# Chat with file and auto-select model
python -m cli.stratifyai_cli chat --file large.txt --auto-select

# Chunk large file (automatic with --chunked flag)
python -m cli.stratifyai_cli chat --file huge.txt --chunked --chunk-size 50000

# Analyze and extract schema from CSV
python -m cli.stratifyai_cli analyze data.csv

# View cache statistics
python -m cli.stratifyai_cli cache-stats --detailed

# Clear response cache
python -m cli.stratifyai_cli cache-clear

# Interactive mode (supports /file command with auto-extraction)
python -m cli.stratifyai_cli interactive --provider anthropic
# Within interactive: /file large.csv (prompts for extraction)

# Use AWS Bedrock models
python -m cli.stratifyai_cli chat "Hello" --provider bedrock --model anthropic.claude-3-5-sonnet-20241022-v2:0
```

## Support Matrix

| Solution | Implemented | Tested | Documented | Phase |
|----------|-------------|--------|------------|-------|
| File size warnings | ✅ | ✅ | ✅ | 7.1 |
| Token estimation | ✅ | ✅ | ✅ | 7.1 |
| Long-context models | ✅ | ✅ | ✅ | 1-2 |
| Smart chunking | ✅ | ✅ | ✅ | 7.1 |
| CSV schema extraction | ✅ | ✅ | ✅ | 7.2 |
| JSON schema extraction | ✅ | ✅ | ✅ | 7.2 |
| Log error extraction | ✅ | ✅ | ✅ | 7.2 |
| Code structure extraction | ✅ | ✅ | ✅ | 7.2 |
| Model auto-select | ✅ | ✅ | ✅ | 7.3 |
| Prompt caching | ✅ | ✅ | ✅ | 6, 7.4 |
| RAG/Vector DB (ChromaDB) | ✅ | ✅ | ✅ | 7.5 |
| AWS Bedrock provider | ✅ | ✅ | ✅ | 2 (Feb 3) |
| Compression utilities | ❌ | ❌ | ⚠️ | Future |

Legend: ✅ Complete | ⚠️ Partial | ❌ Not implemented

## Next Steps

1. **Review** docs/LARGE_FILE_STRATEGIES.md for detailed implementation
2. **Test** current file upload with large files
3. **Implement** priority features based on use cases
4. **Monitor** token usage and costs in production
5. **Iterate** based on user feedback

## Resources

- Full guide: `docs/LARGE_FILE_STRATEGIES.md`
- Auth error handling: `docs/AUTH_ERROR_HANDLING.md`
- CLI usage: `docs/cli-usage.md`
- API reference: `docs/API-REFERENCE.md`
