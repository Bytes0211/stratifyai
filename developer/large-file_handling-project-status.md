# StratifyAI - Phase 7: Large File Handling
## Project Status Document

**Phase:** Phase 7 - Large File Handling  
**Status:** Planning (0% Complete)  
**Start Date:** February 3, 2026  
**Target Completion:** March 10, 2026 (5 weeks)  
**Priority:** High  

## Executive Summary

Phase 7 introduces intelligent large file handling capabilities to manage token limits across all LLM providers. Current implementation supports files up to 5MB with basic warnings, but lacks intelligent processing for files exceeding model context windows (128k-1.8M tokens). This phase implements six distinct strategies for handling large files efficiently and cost-effectively.

## Problem Statement

### Current Limitations
- **Hard file size limit**: 5MB cap with basic size warnings
- **No intelligent processing**: Large files uploaded directly, often exceeding token limits
- **Cost inefficiency**: Full file uploads cost 10-100x more than necessary
- **Context overflow**: Files exceeding model limits cause request failures
- **No file-type awareness**: CSV, logs, code treated identically to documents

### Impact
- Users cannot analyze files >500KB effectively
- Wasted tokens on unnecessary content (99% in some cases)
- High costs for repetitive queries on same file
- Failed requests when files exceed context windows

### Solution Overview
Implement 5 core capabilities:
1. **Automatic Chunking**: Split large files, progressive summarization
2. **Intelligent Extraction**: File-type aware content extraction
3. **Model Auto-Selection**: Choose optimal model based on file size
4. **Enhanced Caching UI**: Leverage prompt caching for cost savings
5. **RAG/Vector DB Integration**: Semantic search for massive datasets

## Phase Breakdown

### Week 1: Foundation & Chunking (Feb 3-7)
**Focus**: Token estimation, file analysis, basic chunking

#### Tasks
- [ ] **1.1**: Implement token count estimation utility
  - Add `tiktoken` dependency for accurate token counting
  - Create `estimate_tokens()` function in utils
  - Display token estimates before file upload
  - **Estimated effort**: 4 hours
  - **Dependencies**: None
  
- [ ] **1.2**: Add file size analyzer
  - Detect file type (CSV, JSON, log, code, text)
  - Calculate token estimate for each file type
  - Display warnings for files >80% of model context
  - **Estimated effort**: 3 hours
  - **Dependencies**: 1.1
  
- [ ] **1.3**: Implement basic chunking
  - Create `chunk_content()` function with configurable size
  - Add `--chunk-size` CLI parameter
  - Split files at natural boundaries (paragraphs, newlines)
  - **Estimated effort**: 6 hours
  - **Dependencies**: 1.1
  
- [ ] **1.4**: Implement progressive summarization
  - Create `summarize_chunk()` using cheaper model (gpt-4o-mini)
  - Combine chunk summaries with metadata
  - Add progress bar for multi-chunk processing
  - **Estimated effort**: 8 hours
  - **Dependencies**: 1.3
  
- [ ] **1.5**: Add chunking to CLI commands
  - Update `interactive` command with `--chunked` flag
  - Update `chat` command with chunking support
  - Add token count display in output
  - **Estimated effort**: 4 hours
  - **Dependencies**: 1.4

**Week 1 Deliverables**:
- Token estimation utility (100% accurate)
- Automatic chunking for files >500KB
- Progressive summarization pipeline
- Updated CLI with chunking support

**Testing**: 5 unit tests, 2 integration tests

---

### Week 2: Intelligent Extraction (Feb 10-14)
**Focus**: File-type specific extraction strategies

#### Tasks
- [ ] **2.1**: Implement CSV/DataFrame extraction
  - Install `pandas` dependency
  - Extract schema (columns, dtypes)
  - Sample first/last N rows
  - Generate statistics (describe, value_counts)
  - **Estimated effort**: 6 hours
  - **Dependencies**: None
  
- [ ] **2.2**: Implement JSON extraction
  - Create schema extractor for nested JSON
  - Sample top-level keys with values
  - Detect arrays and extract length + sample
  - **Estimated effort**: 5 hours
  - **Dependencies**: None
  
- [ ] **2.3**: Implement log file extraction
  - Detect log format (syslog, JSON logs, custom)
  - Extract ERROR/WARN/CRITICAL lines
  - De-duplicate repeated errors
  - Show error frequency distribution
  - **Estimated effort**: 6 hours
  - **Dependencies**: None
  
- [ ] **2.4**: Implement code file extraction
  - Use AST parsing for Python files
  - Extract function/class signatures
  - Generate code structure summary
  - Support other languages (JS, Java, Go) with regex
  - **Estimated effort**: 8 hours
  - **Dependencies**: None
  
- [ ] **2.5**: Add extraction to CLI
  - Create `analyze` CLI command
  - Add `--extract-mode` parameter (schema, errors, summary, full)
  - Auto-detect file type and suggest extraction mode
  - **Estimated effort**: 5 hours
  - **Dependencies**: 2.1-2.4

**Week 2 Deliverables**:
- CSV/JSON schema extraction (99% token reduction)
- Log error extraction
- Code structure extraction
- New `analyze` CLI command

**Testing**: 8 unit tests (2 per file type), 3 integration tests

---

### Week 3: Model Auto-Selection (Feb 17-21)
**Focus**: Intelligent model routing based on file size

#### Tasks
- [ ] **3.1**: Create model selection algorithm
  - Build file size → model context mapping
  - Factor in provider costs
  - Prefer cheaper models when possible
  - **Estimated effort**: 4 hours
  - **Dependencies**: None
  
- [ ] **3.2**: Implement auto-selection logic
  - Create `select_optimal_model()` function
  - Consider user preferences (cost, quality, latency)
  - Fallback to chunking if file too large
  - **Estimated effort**: 5 hours
  - **Dependencies**: 3.1, Week 1 tasks
  
- [ ] **3.3**: Add cost estimation preview
  - Calculate estimated cost before upload
  - Show comparison with chunking/extraction
  - Display warning if cost >$0.50
  - **Estimated effort**: 4 hours
  - **Dependencies**: 3.2
  
- [ ] **3.4**: Integrate with CLI
  - Add `--auto-select-model` flag to commands
  - Display model selection reasoning
  - Allow user override
  - **Estimated effort**: 3 hours
  - **Dependencies**: 3.2, 3.3
  
- [ ] **3.5**: Create model recommendation engine
  - Suggest best strategy per file type
  - Learn from user preferences
  - Display strategy comparison table
  - **Estimated effort**: 6 hours
  - **Dependencies**: 3.2, Week 2 tasks

**Week 3 Deliverables**:
- File size → model auto-selection
- Cost estimation and preview
- Strategy recommendation engine
- Enhanced CLI with auto-selection

**Testing**: 6 unit tests, 2 integration tests

---

### Week 4: Enhanced Caching UI (Feb 24-28)
**Focus**: Improved prompt caching experience

#### Tasks
- [ ] **4.1**: Enhance cache control in models
  - Update `Message` dataclass with cache_control field
  - Add validation for cache-supporting providers
  - Track cache write/read tokens separately
  - **Estimated effort**: 4 hours
  - **Dependencies**: None
  
- [ ] **4.2**: Create interactive caching mode
  - New `interactive-cached` CLI command
  - Automatically mark large content as cacheable
  - Display cache statistics in real-time
  - **Estimated effort**: 6 hours
  - **Dependencies**: 4.1
  
- [ ] **4.3**: Add cache savings display
  - Show cache hit/miss indicators
  - Calculate and display cost savings
  - Cumulative savings tracker
  - **Estimated effort**: 4 hours
  - **Dependencies**: 4.2
  
- [ ] **4.4**: Implement cache strategy selector
  - Auto-enable caching for files >500KB
  - Suggest caching for repeated queries
  - Prompt user when caching beneficial
  - **Estimated effort**: 3 hours
  - **Dependencies**: 4.2, 4.3
  
- [ ] **4.5**: Cache management commands
  - Add `cache-info` command to show current cache state
  - Display cache TTL and estimated savings
  - Show which content is cached
  - **Estimated effort**: 3 hours
  - **Dependencies**: 4.2, 4.3

**Week 4 Deliverables**:
- Enhanced cache control in data models
- New `interactive-cached` command
- Real-time cache savings display
- Cache management commands

**Testing**: 7 unit tests, 3 integration tests

---

### Week 5: RAG/Vector DB Integration (Mar 3-7)
**Focus**: Semantic search for massive files

#### Tasks
- [ ] **5.1**: Evaluate vector DB options
  - Compare ChromaDB, FAISS, Pinecone
  - Choose embedded solution (ChromaDB or FAISS)
  - Design integration architecture
  - **Estimated effort**: 4 hours
  - **Dependencies**: None
  
- [ ] **5.2**: Implement text splitting
  - Install `langchain-text-splitters` or equivalent
  - Smart splitting (paragraphs, sentences, code blocks)
  - Configurable chunk size with overlap
  - **Estimated effort**: 5 hours
  - **Dependencies**: 5.1
  
- [ ] **5.3**: Create vector DB wrapper
  - Abstract vector DB operations
  - Implement ChromaDB/FAISS backend
  - Add document indexing
  - **Estimated effort**: 8 hours
  - **Dependencies**: 5.1, 5.2
  
- [ ] **5.4**: Implement semantic search
  - Query vector DB for relevant chunks
  - Rank results by relevance
  - Retrieve top-k chunks for context
  - **Estimated effort**: 6 hours
  - **Dependencies**: 5.3
  
- [ ] **5.5**: Add RAG CLI commands
  - Create `index` command to create vector DB
  - Create `query-rag` command for semantic search
  - Integrate with existing `interactive` mode
  - **Estimated effort**: 7 hours
  - **Dependencies**: 5.3, 5.4
  
- [ ] **5.6**: Performance optimization
  - Cache embeddings for repeated files
  - Batch processing for large files
  - Optimize query response time
  - **Estimated effort**: 5 hours
  - **Dependencies**: 5.5

**Week 5 Deliverables**:
- Vector DB integration (ChromaDB or FAISS)
- Semantic search capability
- New `index` and `query-rag` commands
- Optimized for files >10MB

**Testing**: 8 unit tests, 4 integration tests

---

## Final Week: Testing & Documentation (Mar 10)
**Focus**: Integration testing, documentation, examples

#### Tasks
- [ ] **6.1**: Comprehensive integration tests
  - Test all 5 strategies end-to-end
  - Test with real files of various sizes
  - Performance benchmarks
  - **Estimated effort**: 8 hours
  
- [ ] **6.2**: Update documentation
  - Add examples to LARGE_FILE_STRATEGIES.md
  - Update CLI usage docs
  - Create tutorial videos/GIFs
  - **Estimated effort**: 6 hours
  
- [ ] **6.3**: Create example scripts
  - CSV analysis example
  - Log processing example
  - RAG query example
  - **Estimated effort**: 4 hours
  
- [ ] **6.4**: Performance optimization
  - Profile token counting overhead
  - Optimize chunking algorithm
  - Reduce memory footprint
  - **Estimated effort**: 6 hours

**Final Deliverables**:
- 37 new unit tests (total)
- 14 integration tests
- Updated documentation with examples
- Performance benchmarks

---

## Success Metrics

### Performance Targets
- [ ] Token estimation accuracy: >95%
- [ ] Chunking overhead: <5 seconds for 5MB file
- [ ] Cost reduction: >80% for large files (via extraction)
- [ ] Cache savings: >85% on subsequent queries
- [ ] RAG query time: <2 seconds for 50MB corpus

### Feature Completeness
- [ ] 5 file types supported (CSV, JSON, logs, code, text)
- [ ] 4 extraction modes (schema, errors, summary, full)
- [ ] 3 caching strategies (auto, manual, off)
- [ ] 2 vector DB backends (ChromaDB, FAISS)

### Quality Metrics
- [ ] Test coverage: >85% for new code
- [ ] Zero critical bugs in production
- [ ] Documentation complete and accurate
- [ ] CLI help text comprehensive

---

## Dependencies & Prerequisites

### External Dependencies
- **New Python packages**:
  - `tiktoken` (token counting)
  - `pandas` (CSV/data processing)
  - `chromadb` or `faiss-cpu` (vector DB)
  - `langchain-text-splitters` (text splitting)
  
- **Provider support**:
  - Anthropic: Prompt caching (already supported)
  - OpenAI: Prompt caching (already supported)
  - Long-context models: Gemini 2.5, Grok 4.1 (already configured)

### Internal Dependencies
- Completed Phase 5 (CLI Interface) ✅
- `llm_abstraction.models.Message` with cache_control ⚠️ (partial)
- Cost tracking infrastructure ✅
- Rich console formatting ✅

---

## Risk Assessment

### High Risk
- **Token estimation accuracy**: Different models have different tokenizers
  - **Mitigation**: Use provider-specific token counting where available
  
- **RAG complexity**: Vector DB adds significant complexity
  - **Mitigation**: Make RAG optional, use simple in-memory fallback

### Medium Risk
- **File type detection**: Edge cases for unusual formats
  - **Mitigation**: Fallback to text processing for unknown types
  
- **Cache invalidation**: Stale cache for updated files
  - **Mitigation**: Use file hash in cache key

### Low Risk
- **Performance overhead**: Token counting adds latency
  - **Mitigation**: Cache token counts, run in background

---

## Resource Requirements

### Development Time
- **Total estimated hours**: 165 hours
- **Working days**: 25 days (5 weeks × 5 days)
- **Hours per day**: ~6.5 hours
- **Contingency**: 15% buffer (25 hours)

### Infrastructure
- **Storage**: ~100MB for vector DB indices (per large file)
- **Memory**: +50MB for in-memory vector search
- **Dependencies**: +5 new Python packages

---

## Testing Strategy

### Unit Tests (37 tests)
- Token estimation: 3 tests
- Chunking: 5 tests
- File extraction: 12 tests (3 per type)
- Model selection: 6 tests
- Caching: 7 tests
- RAG/Vector DB: 8 tests

### Integration Tests (14 tests)
- End-to-end chunking: 2 tests
- File type processing: 4 tests
- Model auto-selection: 2 tests
- Caching workflows: 3 tests
- RAG queries: 3 tests

### Manual Testing
- Test with real files: CSV (10MB), logs (50MB), code (5MB)
- Cost verification with actual API calls
- Performance benchmarks on various file sizes

---

## Migration & Rollout

### Backward Compatibility
- All new features are opt-in (flags/commands)
- Existing CLI commands unchanged
- Default behavior: current file upload (backward compatible)

### Feature Flags
- `--chunked`: Enable chunking (default: auto for >500KB)
- `--extract-mode`: Extraction strategy (default: auto-detect)
- `--auto-select-model`: Model selection (default: user choice)
- `--cache`: Caching strategy (default: auto for >500KB)
- `--rag`: Enable RAG search (default: off)

### Rollout Plan
1. **Week 1-2**: Internal testing with dev team
2. **Week 3**: Beta release to select users
3. **Week 4**: Public release with documentation
4. **Week 5**: Gather feedback, iterate

---

## Post-Phase Activities

### Monitoring
- Track token usage before/after optimization
- Monitor cost savings across users
- Measure cache hit rates
- Track RAG query performance

### Future Enhancements (Phase 8+)
- Multi-file upload and merge
- Binary file support (PDF, images via OCR)
- Real-time streaming for very large files
- Distributed vector DB (Pinecone, Weaviate)
- Smart compression algorithms
- Context window expansion strategies

---

## Stakeholder Communication

### Weekly Updates
- Progress report every Friday
- Demo new features as completed
- Gather user feedback early

### Documentation Updates
- Update LARGE_FILE_STRATEGIES.md weekly
- Maintain TOKEN_LIMIT_QUICK_GUIDE.md
- Add CLI examples to docs/cli-usage.md

---

## Definition of Done

### Per Feature
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Performance benchmarks met

### Phase 7 Complete
- [ ] All 5 core capabilities implemented
- [ ] 51 tests passing (37 unit + 14 integration)
- [ ] Documentation complete with examples
- [ ] Cost reduction >80% demonstrated
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## Appendix

### File Size → Token Mapping
```
128k tokens  ≈ 512 KB   (GPT-4o, Claude Sonnet)
200k tokens  ≈ 800 KB   (o1, Claude Opus)
1M tokens    ≈ 4 MB     (Gemini 2.5)
1.8M tokens  ≈ 7.2 MB   (Grok 4.1)
```

### Cost Optimization Examples
```
2 MB CSV file:
- Direct upload:    500k tokens = $1.25
- Schema extract:   5k tokens   = $0.01 (99% savings)

10 MB log file:
- Direct upload:    Failed (exceeds limit)
- Error extract:    5k tokens   = $0.01
- RAG (10 queries): 50k tokens  = $0.13
```

### CLI Command Summary
```bash
# Automatic chunking
stratifyai interactive --file large.txt --chunked

# Intelligent extraction
stratifyai analyze data.csv --extract-mode schema
stratifyai analyze server.log --extract errors

# Model auto-selection
stratifyai chat --file huge.txt --auto-select-model

# Enhanced caching
stratifyai interactive-cached --file report.pdf

# RAG integration
stratifyai index corpus.txt
stratifyai query-rag "What are the main findings?"
```

---

**Document Version**: 1.0  
**Last Updated**: February 3, 2026  
**Next Review**: Weekly during Phase 7 execution  
**Owner**: Development Team  
**Approvers**: Product, Engineering Leads
