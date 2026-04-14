#!/usr/bin/env python3
"""Interactive script to check available models from provider APIs.

This script prompts for a provider, queries their API, and displays
all valid/active models that are actually available.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import stratifyai
sys.path.insert(0, str(Path(__file__).parent.parent))

from stratifyai.catalog_manager import get_provider_models
from stratifyai.utils.provider_validator import validate_provider_models


def load_env_file():
    """Load .env file from project root."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def check_api_key(provider: str) -> tuple[bool, str]:
    """Check if API key is configured for provider."""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY",
        "grok": "XAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "ollama": None,  # Local, no key needed
        "bedrock": "AWS_ACCESS_KEY_ID",
    }

    env_var = key_map.get(provider)
    if env_var is None:
        return True, "N/A (local)"

    value = os.getenv(env_var)
    if value:
        # Show masked key
        masked = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
        return True, masked
    else:
        return False, f"❌ {env_var} not set"


def print_banner():
    """Print script banner."""
    print("=" * 70)
    print("  Provider Model Checker - Query Live API for Available Models")
    print("=" * 70)
    print()


def select_provider() -> str:
    """Prompt user to select a provider."""
    providers = [
        ("openai", "OpenAI (GPT-4o, GPT-4o-mini, etc.)"),
        ("anthropic", "Anthropic (Claude Sonnet, Haiku, etc.)"),
        ("google", "Google (Gemini 2.5 Pro, Flash, etc.)"),
        ("deepseek", "DeepSeek (Reasoner, Chat, etc.)"),
        ("groq", "Groq (Fast Llama/Mixtral models)"),
        ("grok", "xAI Grok (Grok Beta)"),
        ("openrouter", "OpenRouter (Multi-provider gateway)"),
        ("ollama", "Ollama (Local models)"),
        ("bedrock", "AWS Bedrock (Claude, Llama, etc.)"),
    ]

    print("Available Providers:")
    print()
    for i, (provider_id, description) in enumerate(providers, 1):
        has_key, key_status = check_api_key(provider_id)
        status_icon = "✅" if has_key else "❌"
        print(f"  {i}. {status_icon} {description}")
        if not has_key:
            print(f"      {key_status}")
    print()

    while True:
        try:
            choice = input("Select provider (1-9, or 'q' to quit): ").strip().lower()
            if choice == "q":
                print("Exiting.")
                sys.exit(0)

            index = int(choice) - 1
            if 0 <= index < len(providers):
                return providers[index][0]
            else:
                print(f"❌ Please enter a number between 1 and {len(providers)}")
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q'.")
        except KeyboardInterrupt:
            print("\n\nExiting.")
            sys.exit(0)


def query_provider_models(provider: str):
    """Query provider API for available models."""
    print()
    print("=" * 70)
    print(f"  Querying {provider.upper()} API for available models...")
    print("=" * 70)
    print()

    # Check API key status
    has_key, key_status = check_api_key(provider)
    print(f"API Key Status: {key_status}")
    print()

    if not has_key:
        print("❌ Cannot query API without valid credentials.")
        print("   Please set the required environment variable and try again.")
        return

    # Get catalog models
    catalog_models = get_provider_models(provider)
    model_ids = list(catalog_models.keys())

    print(f"📋 Found {len(model_ids)} models in catalog for {provider}")
    print()

    # Validate against provider API
    print("🔍 Validating models against provider API...")
    result = validate_provider_models(provider, model_ids)

    print()
    print("-" * 70)
    print("  VALIDATION RESULTS")
    print("-" * 70)
    print()

    # Show timing
    print(f"⏱️  Validation Time: {result['validation_time_ms']}ms")
    print()

    # Show error if any
    if result["error"]:
        print(f"⚠️  Validation Warning: {result['error']}")
        print()

    # Show valid models
    valid_models = result["valid_models"]
    invalid_models = result["invalid_models"]

    print(f"✅ VALID MODELS ({len(valid_models)}):")
    print()
    if valid_models:
        for model_id in valid_models:
            metadata = catalog_models.get(model_id, {})
            display_name = metadata.get("display_name", model_id)
            context = metadata.get("context", "N/A")
            cost_in = metadata.get("cost_input", 0)
            cost_out = metadata.get("cost_output", 0)

            print(f"  • {model_id}")
            print(f"    Name: {display_name}")
            print(f"    Context: {context:,} tokens")
            print(f"    Cost: ${cost_in:.2f}/${cost_out:.2f} per 1M tokens")

            # Show capabilities
            capabilities = []
            if metadata.get("supports_vision"):
                capabilities.append("vision")
            if metadata.get("supports_tools"):
                capabilities.append("tools")
            if metadata.get("supports_caching"):
                capabilities.append("caching")
            if metadata.get("reasoning_model"):
                capabilities.append("reasoning")

            if capabilities:
                print(f"    Capabilities: {', '.join(capabilities)}")
            print()
    else:
        print("  (none)")
        print()

    # Show invalid models
    if invalid_models:
        print(f"❌ INVALID/UNAVAILABLE MODELS ({len(invalid_models)}):")
        print()
        print("  These models are in the catalog but NOT available from the API:")
        print()
        for model_id in invalid_models:
            metadata = catalog_models.get(model_id, {})
            display_name = metadata.get("display_name", model_id)
            print(f"  • {model_id}")
            print(f"    Name: {display_name}")
            print("    ⚠️  This model may be deprecated or not yet released")
            print()

    # Summary
    print("-" * 70)
    print(f"Summary: {len(valid_models)} valid, {len(invalid_models)} invalid")
    print("-" * 70)


def main():
    """Main entry point."""
    # Load .env file
    load_env_file()

    # Print banner
    print_banner()

    # Select provider
    provider = select_provider()

    # Query models
    query_provider_models(provider)

    # Ask if user wants to check another provider
    print()
    while True:
        choice = input("Check another provider? (y/n): ").strip().lower()
        if choice in ("y", "yes"):
            print()
            provider = select_provider()
            query_provider_models(provider)
            print()
        elif choice in ("n", "no"):
            print("\n✅ Done!")
            break
        else:
            print("❌ Please enter 'y' or 'n'")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Exiting...")
        sys.exit(0)
