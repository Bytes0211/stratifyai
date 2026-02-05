# example_cli_usage.py
from dotenv import load_dotenv
import subprocess
# Load environment variables
load_dotenv()
# Example: Simple chat via CLI
# Run: stratifyai chat "Explain Python decorators" -p openai -m gpt-4.1-mini
result = subprocess.run(
    ["stratifyai", "chat", "Explain Python decorators", "-p", "openai", "-m", "gpt-4.1-mini"],
    capture_output=True,
    text=True
)
print(result.stdout)
# Example: Using CLI with streaming
# Run: stratifyai chat "Tell me a story" -p openai -m gpt-4.1-mini --stream
subprocess.run(
    ["stratifyai", "chat", "Tell me a story", "-p", "openai", "-m", "gpt-4.1-mini", "--stream"]
)
# Example: Chat with file input
# Run: stratifyai chat "Summarize this:" -f document.txt -p openai -m gpt-4.1-mini
subprocess.run(
    ["stratifyai", "chat", "Summarize this:", "-f", "document.txt", "-p", "openai", "-m", "gpt-4.1-mini"]
)
