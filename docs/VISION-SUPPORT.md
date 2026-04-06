# Vision Support Guide

StratifyAI supports image-aware requests across vision-capable providers such as OpenAI GPT-4o, Anthropic Claude vision models, Google Gemini vision models, and compatible Bedrock offerings.

## Supported Workflows

- **Web UI uploads** for images and text attachments
- **REST API requests** using `file_name` and `file_content`
- **Smart chunking** for large text files when `chunked=true`

## REST API Example

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Authorization: Bearer $STRATIFYAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Describe the attached image."}
    ],
    "file_name": "diagram.png",
    "file_content": "<base64-or-text-payload>"
  }'
```

## File Limits

- Oversized attachment payloads are rejected before processing.
- Text attachments can also be combined with `chunked=true` and `chunk_size` for summarization-first workflows.
- If a model does not support images, the API returns a provider-specific validation error.

## Best Practices

1. Use a **vision-capable model** when sending images.
2. Keep attachments focused; large documents work best with smart chunking enabled.
3. Prefer the Svelte web UI for interactive uploads and previews.
4. Check `catalog/models.json` for the latest vision-capable models.

## Related Docs

- `docs/GETTING-STARTED.md`
- `docs/API-REFERENCE.md`
- `examples/README.md`
