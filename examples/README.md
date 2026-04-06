# Examples Guide

Use the examples below in this order for the quickest ramp-up.

## Recommended Learning Order

| Step | File | Focus |
|------|------|-------|
| 1 | `chatbot.py` | Basic multi-provider chat flow |
| 2 | `router_example.py` | Automatic model routing |
| 3 | `caching_examples.py` | Response caching and cost savings |
| 4 | `document_summarizer.py` | Large-file summarization workflows |
| 5 | `auto_selection_demo.py` | File-aware model selection |
| 6 | `rag_example.py` | Retrieval-augmented generation |
| 7 | `web_server.py` | Serving StratifyAI behind a web app |
| 8 | `performance_benchmark.py` | Load profiles and performance testing |
| 9 | `code_reviewer.py` | Practical review-oriented prompt workflow |

## Quick Runs

```bash
python examples/chatbot.py
python examples/router_example.py
python examples/rag_example.py
```

## Notes

- Update any example model constants from `catalog/models.json` if provider offerings change.
- Run `stratifyai check-keys` before examples that call external providers.
- For the web UI and API server flow, see `docs/GETTING-STARTED.md`.
