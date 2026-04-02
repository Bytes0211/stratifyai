# File Attachment Feature

## Overview

StratifyAI CLI supports file attachments in both `chat` and `interactive` modes. This allows you to send file contents to LLMs for analysis, summarization, code review, and more.

## Features

- **Multiple upload methods**: Command-line flag or in-conversation commands
- **Size restrictions**: 5 MB maximum with warnings for large files
- **Safety warnings**: Alerts for files that may consume excessive tokens
- **Flexible usage**: Send files alone or combine with text prompts
- **Visual feedback**: File size, type, and load confirmation

## Usage

### 1. Chat Mode - Interactive Prompt

When using chat mode without specifying all parameters, you'll be prompted for a file after selecting the model:

```bash
# Run chat without arguments - you'll be prompted for everything
python -m cli.stratifyai_cli chat

Select Provider
  1. openai
  2. anthropic
  ...
Choose provider: 1

Available models for openai:
  1. gpt-4o
  2. gpt-4o-mini
  ...
Select model: 2

Temperature (0.0-2.0, default 0.7): 0.7

File Attachment (Optional)
Attach a file to include its content in your message
Max file size: 5 MB | Leave blank to skip

File path (or press Enter to skip): document.txt
✓ Loaded document.txt (15.3 KB, 4,521 chars)

Enter your message:
Message: Summarize this document
```

### 1b. Chat Mode with File Flag

You can also attach a file using the `--file` flag when running with all parameters:

```bash
# File with command-line flag
python -m cli.stratifyai_cli chat --file document.txt -p openai -m gpt-4o-mini

# File with message
python -m cli.stratifyai_cli chat "Summarize this:" --file report.md -p anthropic -m claude-sonnet-4-5-20250929

# Enable caching for large files (Anthropic only)
python -m cli.stratifyai_cli chat --file large_doc.txt --cache-control -p anthropic
```

### 2. Interactive Mode - Interactive Prompt

When starting interactive mode without all parameters, you'll be prompted for a file after model selection:

```bash
# Run interactive mode without arguments
python -m cli.stratifyai_cli interactive

Select Provider
  1. openai
  ...
Choose provider: 1

Available models for openai:
  1. gpt-4o
  ...
Select model: 1

Initial File Context (Optional)
Load a file to provide context for the conversation
Max file size: 5 MB | Leave blank to skip

File path (or press Enter to skip): codebase.py

Loading initial context...
✓ Loaded codebase.py (8.2 KB, 2,145 chars)
File loaded as initial context

StratifyAI Interactive Mode
Provider: openai | Model: gpt-4o | Context: 128,000 tokens
Commands: /file <path> | /attach <path> | /clear | exit

You: What are the main functions in this code?
```

### 2b. Interactive Mode with File Flag

You can also provide a file using the `--file` flag:

```bash
# Start with file context using flag
python -m cli.stratifyai_cli interactive --file codebase.py -p openai -m gpt-4o

# Then ask questions about it
You: What are the main functions in this code?
You: How can I optimize the performance?
```

### 3. In-Conversation Commands

During an interactive session, use special commands to attach files:

#### `/file <path>` - Send file immediately
Loads and sends the file content as a standalone message:

```bash
You: /file data.csv
✓ Loaded data.csv (125.3 KB, 15,234 chars)
[File sent to LLM]
```

#### `/attach <path>` - Stage file for next message
Stages a file to be combined with your next text message:

```bash
You: /attach code.py
✓ File staged - will be attached to your next message

You 📎 code.py: Review this code and suggest improvements
[Sends: "Review this code and suggest improvements" + code.py content]
```

#### `/clear` - Clear staged attachment
Removes any staged file:

```bash
You 📎 document.txt: /clear
Cleared staged file: document.txt

You: Continue without the file
```

## File Size Limits and Warnings

### Maximum Size: 5 MB
Files larger than 5 MB are rejected:

```bash
You: /file huge_file.txt
✗ File too large: 8.45 MB (max 5 MB)
⚠ Large files consume significant tokens and may exceed model context limits
```

### Warning Threshold: 500 KB
Files between 500 KB and 5 MB trigger a confirmation prompt:

```bash
You: /file large_report.md
⚠ Large file detected: 1.2 MB
⚠ This will consume substantial tokens and may incur significant costs
Continue loading this file? [y/N]: 
```

### Why These Limits?

1. **Token Consumption**: Large files consume many tokens
   - Example: 1 MB text ≈ 250,000 tokens ≈ $0.025 - $2.50 depending on model
   
2. **Context Window Limits**: Most models have context limits
   - GPT-4o: 128K tokens (~512 KB text)
   - Claude Sonnet: 200K tokens (~800 KB text)
   - Gemini 2.0 Flash: 1M tokens (~4 MB text)
   
3. **Cost Control**: Prevent accidental expensive API calls
   - 5 MB file with GPT-4o could cost $1.25+ per request

## Error Handling

### File Not Found
```bash
You: /file missing.txt
✗ File not found: missing.txt
```

### Non-Text File
```bash
You: /file image.png
✗ Cannot read file: image.png (not a text file)
```

### Permission Denied
```bash
You: /file protected.txt
✗ Error reading file: [Errno 13] Permission denied: 'protected.txt'
```

## Best Practices

### 1. Use Appropriate Models
- **Small files (<10 KB)**: Any model works
- **Medium files (10-100 KB)**: Standard models (GPT-4o-mini, Claude Haiku)
- **Large files (100 KB - 1 MB)**: High-context models (GPT-4o, Claude Sonnet, Gemini Flash)
- **Very large files (1-5 MB)**: Gemini 2.0 Flash (1M context) or split the file

### 2. Enable Caching for Repeated Queries
If asking multiple questions about the same file, use prompt caching (Anthropic):

```bash
python -m cli.stratifyai_cli chat --file large_doc.txt --cache-control -p anthropic -m claude-sonnet-4-5-20250929
```

### 3. Combine Files with Clear Instructions
```bash
# Good: Clear instruction
You: /attach report.md
You 📎 report.md: Extract all action items and create a prioritized list

# Less effective: Vague instruction  
You: /attach report.md
You 📎 report.md: What do you think?
```

### 4. Monitor Costs
Large file uploads can be expensive. Check costs after each request:

```bash
Provider: openai | Model: gpt-4o
Context: 128,000 tokens | Tokens: 45,234 | Cost: $0.1357
```

## Example Workflows

### Code Review
```bash
python -m cli.stratifyai_cli interactive --file src/main.py -p anthropic -m claude-sonnet-4-5-20250929

You: Review this code for:
1. Security vulnerabilities
2. Performance issues
3. Best practice violations
```

### Document Summarization
```bash
python -m cli.stratifyai_cli chat --file quarterly_report.md -p openai -m gpt-4o-mini
"Summarize this report in 3 bullet points"
```

### Data Analysis
```bash
python -m cli.stratifyai_cli interactive -p openai -m gpt-4o

You: /file sales_data.csv
You: What are the top 5 products by revenue?
You: Show monthly trends
```

### Multi-File Analysis
```bash
python -m cli.stratifyai_cli interactive -p anthropic

You: /file config.yaml
You: /file main.py  
You: /file tests.py
You: Are these three files consistent with each other?
```

## Supported File Types

All **text-based files** are supported:

- **Code**: `.py`, `.js`, `.ts`, `.go`, `.java`, `.cpp`, `.c`, `.rs`, etc.
- **Markup**: `.md`, `.html`, `.xml`, `.json`, `.yaml`, `.toml`
- **Documents**: `.txt`, `.csv`, `.log`
- **Config**: `.env`, `.ini`, `.conf`

**Binary files** (images, PDFs, executables) are not supported and will return an error.

## Security Considerations

1. **Never upload files containing secrets**
   - API keys, passwords, tokens will be sent to the LLM provider
   - Sanitize files before uploading

2. **Proprietary code/data**
   - Consider data privacy policies of LLM providers
   - Use local models (Ollama) for sensitive content

3. **File path validation**
   - Paths are expanded with `~` support
   - Files must be readable by current user
   - No directory traversal protection needed (local CLI only)

## Troubleshooting

### Q: File uploads are slow
**A:** Large files take time to:
1. Read from disk
2. Upload to LLM API
3. Process by the model

Consider:
- Splitting large files
- Using faster models for simple queries
- Enabling streaming for immediate feedback

### Q: Getting "context too long" errors
**A:** File exceeds model's context window. Solutions:
1. Use a higher-context model (Gemini 2.0 Flash)
2. Split the file into smaller chunks
3. Summarize the file first, then analyze

### Q: Costs are too high
**A:** Large files consume many tokens. Reduce costs by:
1. Using smaller/cheaper models (gpt-4o-mini, claude-haiku)
2. Enabling prompt caching for repeated queries
3. Processing files in batches
4. Using router with cost-optimized strategy

## Command Reference

### Chat Command
```bash
python -m cli.stratifyai_cli chat [MESSAGE] --file PATH [OPTIONS]

Options:
  --file, -f FILE          Load content from file
  --cache-control          Enable prompt caching (Anthropic)
  --provider, -p TEXT      LLM provider
  --model, -m TEXT         Model name
  --temperature, -t FLOAT  Temperature (0.0-2.0)
  --max-tokens INT         Maximum tokens to generate
  --stream                 Stream response in real-time
```

### Interactive Command
```bash
python -m cli.stratifyai_cli interactive --file PATH [OPTIONS]

Options:
  --file, -f FILE      Load initial context from file
  --provider, -p TEXT  LLM provider  
  --model, -m TEXT     Model name

In-Conversation Commands:
  /file <path>     Load and send file immediately
  /attach <path>   Stage file for next message
  /clear           Clear staged file
  exit, quit, q    Exit interactive mode
```
