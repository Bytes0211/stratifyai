# StratumAI Quick Start Guide

**For Non-Technical Users**

This guide shows you how to use StratumAI without needing to know command-line flags or technical details.

## Starting a Chat Session

Simply run the chat command without any arguments:

```bash
python -m cli.stratumai_cli chat
```

You'll be guided through a series of simple prompts:

### Step 1: Choose Your Provider

```
Select Provider
  1. openai
  2. anthropic
  3. google
  4. deepseek
  5. groq
  6. grok
  7. ollama
  8. openrouter

Choose provider: 
```

**What to do**: Type a number (1-8) and press Enter
- **Recommended for beginners**: Type `1` (OpenAI) or `2` (Anthropic)

### Step 2: Choose Your Model

```
Available models for openai:
  1. gpt-4o
  2. gpt-4o-mini
  3. o1
  4. o1-mini
  5. o3-mini

Select model:
```

**What to do**: Type a number and press Enter
- **Recommended for beginners**: Type `2` (gpt-4o-mini - fast and affordable)
- **For complex tasks**: Type `1` (gpt-4o - more capable)

### Step 3: Set Temperature

```
Temperature (0.0-2.0, default 0.7): 
```

**What to do**: Press Enter to use the default (0.7), or type a number:
- **0.0-0.3**: More focused, deterministic responses
- **0.7**: Balanced (recommended)
- **1.0-2.0**: More creative, varied responses

### Step 4: Attach a File (Optional)

```
File Attachment (Optional)
Attach a file to include its content in your message
Max file size: 5 MB | Leave blank to skip

File path (or press Enter to skip):
```

**What to do**:
- **To skip**: Just press Enter
- **To attach a file**: Type the file path and press Enter
  - Example: `document.txt`
  - Example: `~/Documents/report.pdf`
  - Example: `/home/user/code/main.py`

If you attach a large file (>500 KB), you'll see a warning:

```
⚠ Large file detected: 1.2 MB
⚠ This will consume substantial tokens and may incur significant costs
Continue loading this file? [y/N]:
```

Type `y` and press Enter to continue, or `n` to cancel.

### Step 5: Enter Your Message

```
Enter your message:
Message:
```

**What to do**: Type your question or instruction and press Enter

**Examples**:
- `What is artificial intelligence?`
- `Summarize this document`
- `Explain this code`
- `Write a poem about the ocean`

### Step 6: View the Response

The AI will respond, and you'll see:

```
Provider: openai | Model: gpt-4o-mini
Context: 128,000 tokens | Tokens: 234 | Cost: $0.000047

[AI response here]

Options: [1] Continue conversation  [2] Save & continue  [3] Save & exit  [4] Exit
What would you like to do?:
```

**What to do**: Choose an option:
- Type `1` to ask another question (continues conversation with context)
- Type `2` to save the conversation to a file and continue
- Type `3` to save and exit
- Type `4` to exit without saving

## Starting an Interactive Session

For ongoing conversations with multiple questions:

```bash
python -m cli.stratumai_cli interactive
```

You'll go through the same steps 1-4 above, then enter an interactive chat mode:

```
StratumAI Interactive Mode
Provider: openai | Model: gpt-4o-mini | Context: 128,000 tokens
Commands: /file <path> | /attach <path> | /clear | exit

You: 
```

### Interactive Mode Commands

**Regular messages**: Just type and press Enter
```
You: What is Python?
```

**Load and send a file immediately**:
```
You: /file code.py
```

**Attach a file to your next message**:
```
You: /attach document.txt
You 📎 document.txt: Summarize this
```

**Clear a staged file**:
```
You 📎 document.txt: /clear
```

**Exit**:
```
You: exit
```
(or type `quit`, `q`, or press Ctrl+C)

## Common Use Cases

### 1. Ask a Quick Question

```bash
python -m cli.stratumai_cli chat
```

1. Choose provider: `1` (OpenAI)
2. Choose model: `2` (gpt-4o-mini)
3. Temperature: Press Enter (use default)
4. File: Press Enter (skip)
5. Message: `What is machine learning?`
6. View response, then type `4` to exit

### 2. Analyze a Document

```bash
python -m cli.stratumai_cli chat
```

1. Choose provider: `2` (Anthropic)
2. Choose model: `1` (claude-sonnet)
3. Temperature: Press Enter
4. File: `report.txt`
5. Message: `Summarize the key points in bullet form`

### 3. Review Code

```bash
python -m cli.stratumai_cli interactive
```

1. Choose provider: `2` (Anthropic)
2. Choose model: `1` (claude-sonnet)
3. File: `main.py`
4. Then ask questions:
   - `You: What does this code do?`
   - `You: Are there any bugs?`
   - `You: How can I improve it?`
   - `You: exit`

### 4. Multi-Document Analysis

```bash
python -m cli.stratumai_cli interactive
```

1. Set up your provider and model
2. Skip initial file
3. In the conversation:
   ```
   You: /file config.yaml
   You: /file main.py
   You: Are these two files consistent?
   ```

## Don't Worry About Mistakes!

StratumAI is designed to be forgiving. If you make a mistake:

- **You get 3 tries**: The system gives you up to 3 attempts to enter valid input
- **Helpful messages**: Clear explanations of what went wrong and how to fix it
- **No crashes**: The system won't exit on the first error
- **Safe defaults**: If you can't provide valid input after 3 tries, the system uses sensible defaults

### Example: Entering Letters Instead of Numbers

```
Choose provider: openai
✗ Invalid input. Please enter a number, not letters (e.g., '1' not 'openai')
Try again...

Choose provider: 1
✓ Selected OpenAI
```

### Example: Number Out of Range

```
Select model: 10
✗ Invalid number. Please enter a number between 1 and 5
Try again...

Select model: 2
✓ Selected gpt-4o-mini
```

## Tips for Non-Technical Users

1. **Start simple**: Use OpenAI with gpt-4o-mini for everyday questions
2. **Use defaults**: When in doubt, just press Enter to use the default value
3. **Don't panic if you make a mistake**: You get 3 tries, and the error messages will guide you
4. **File paths**: You can drag and drop files into the terminal to get their paths
5. **Costs**: Keep an eye on the "Cost:" display - gpt-4o-mini is very affordable ($0.00001-0.0001 per request)
6. **Large files**: If prompted about a large file, choose `n` unless you're sure you need it
7. **Interactive mode**: Use this for back-and-forth conversations where the AI needs context from previous messages
8. **Exit anytime**: Press Ctrl+C to exit immediately if you're stuck

## Troubleshooting

### "File not found"
- Check that the file path is correct
- Try using the full path (e.g., `/home/user/document.txt`)
- Make sure the file exists

### "File too large"
- Your file is over 5 MB
- Try splitting it into smaller files
- Or use a summarization tool first

### "Cannot read file (not a text file)"
- The file is binary (image, PDF, executable)
- StratumAI only supports text files
- Convert PDF to text first if needed

### Cost is too high
- Use gpt-4o-mini instead of gpt-4o
- Avoid uploading very large files
- Ask more focused questions

## Need Help?

- Read the full documentation: `docs/file-attachments.md`
- Check available commands: `python -m cli.stratumai_cli --help`
- For interactive mode: `python -m cli.stratumai_cli interactive --help`
