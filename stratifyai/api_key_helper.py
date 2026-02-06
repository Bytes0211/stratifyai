"""API key management and validation helpers."""

import os
from typing import Dict, Optional, Tuple
from pathlib import Path


class APIKeyHelper:
    """Helper class for managing API keys with user-friendly error messages."""
    
    # Map of provider names to their environment variable keys
    PROVIDER_ENV_KEYS: Dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY",
        "grok": "XAI_API_KEY",  # X.AI official environment variable
        "openrouter": "OPENROUTER_API_KEY",
        "ollama": "OLLAMA_API_KEY",
        "bedrock": "AWS_BEARER_TOKEN_BEDROCK",  # Bedrock bearer token (or AWS_ACCESS_KEY_ID)
    }
    
    # Map of provider names to their API key signup URLs
    PROVIDER_SIGNUP_URLS: Dict[str, str] = {
        "openai": "https://platform.openai.com/api-keys",
        "anthropic": "https://console.anthropic.com/settings/keys",
        "google": "https://makersuite.google.com/app/apikey",
        "deepseek": "https://platform.deepseek.com/api-docs/",
        "groq": "https://console.groq.com/keys",
        "grok": "https://x.ai/api",
        "openrouter": "https://openrouter.ai/keys",
        "ollama": "https://ollama.ai/download",
        "bedrock": "https://docs.aws.amazon.com/bedrock/",
    }
    
    # Friendly provider names for error messages
    PROVIDER_FRIENDLY_NAMES: Dict[str, str] = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google Gemini",
        "deepseek": "DeepSeek",
        "groq": "Groq",
        "grok": "Grok (X.AI)",
        "openrouter": "OpenRouter",
        "ollama": "Ollama",
        "bedrock": "AWS Bedrock",
    }
    
    @classmethod
    def get_api_key(
        cls, 
        provider: str, 
        api_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Get API key for a provider from parameter or environment.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            api_key: Optional API key to use instead of environment variable
            
        Returns:
            API key string or None if not found
        """
        # Use provided key if available
        if api_key:
            return api_key
        
        # Get from environment
        env_key = cls.PROVIDER_ENV_KEYS.get(provider)
        if not env_key:
            return None
        
        return os.getenv(env_key)
    
    @classmethod
    def validate_api_key(
        cls,
        provider: str,
        api_key: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that an API key is available for a provider.
        
        Args:
            provider: Provider name
            api_key: Optional API key to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
            If invalid, error_message contains helpful guidance
        """
        key = cls.get_api_key(provider, api_key)
        
        if key:
            return True, None
        
        # Generate helpful error message
        friendly_name = cls.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        env_key = cls.PROVIDER_ENV_KEYS.get(provider, "API_KEY")
        signup_url = cls.PROVIDER_SIGNUP_URLS.get(provider)
        
        # Special handling for Bedrock (multiple auth methods)
        if provider == "bedrock":
            error_parts = [
                f"❌ Missing API key for {friendly_name}",
                "",
                "AWS Bedrock supports multiple authentication methods:",
                "",
                "Option 1: Bearer token (simplest):",
                f"  export AWS_BEARER_TOKEN_BEDROCK=your-token-here",
                "",
                "Option 2: Access key + secret key:",
                "  export AWS_ACCESS_KEY_ID=your-access-key",
                "  export AWS_SECRET_ACCESS_KEY=your-secret-key",
                "",
                "Option 3: IAM roles (when running on AWS infrastructure)",
                "Option 4: Configure ~/.aws/credentials",
                "",
                f"Get credentials: {signup_url}" if signup_url else "",
            ]
        else:
            error_parts = [
                f"❌ Missing API key for {friendly_name}",
                "",
                "To use this provider, you need to:",
                f"1. Get an API key from: {signup_url}" if signup_url else "",
                f"2. Set the {env_key} environment variable",
                "",
                "Quick setup:",
                f"  export {env_key}=your-api-key-here",
                "",
                "Or add to .env file:",
                f"  {env_key}=your-api-key-here",
                "",
                "Alternative: Pass api_key parameter:",
                f"  client = LLMClient(provider='{provider}', api_key='your-key')",
            ]
        
        # Remove empty strings from parts that had no signup URL
        error_message = "\n".join([p for p in error_parts if p])
        
        return False, error_message
    
    @classmethod
    def check_available_providers(cls) -> Dict[str, bool]:
        """
        Check which providers have API keys configured.
        
        Returns:
            Dictionary mapping provider names to availability (True/False)
        """
        available = {}
        for provider in cls.PROVIDER_ENV_KEYS.keys():
            key = cls.get_api_key(provider)
            available[provider] = key is not None and len(key) > 0
        
        return available
    
    @classmethod
    def get_setup_instructions(cls) -> str:
        """
        Get comprehensive setup instructions for all providers.
        
        Returns:
            Formatted setup instructions string
        """
        available = cls.check_available_providers()
        
        lines = [
            "🔑 StratifyAI API Key Setup",
            "=" * 50,
            "",
            "Available Providers:",
        ]
        
        for provider in sorted(cls.PROVIDER_ENV_KEYS.keys()):
            is_available = available.get(provider, False)
            status = "✓" if is_available else "✗"
            friendly_name = cls.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
            env_key = cls.PROVIDER_ENV_KEYS.get(provider)
            
            lines.append(f"  [{status}] {friendly_name} ({env_key})")
        
        lines.extend([
            "",
            "Setup Instructions:",
            "  1. Copy .env.example to .env: cp .env.example .env",
            "  2. Add your API keys to .env file",
            "  3. Test with: python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini -t 'Hello'",
            "",
            "Get API Keys:",
        ])
        
        for provider in sorted(cls.PROVIDER_SIGNUP_URLS.keys()):
            friendly_name = cls.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
            url = cls.PROVIDER_SIGNUP_URLS.get(provider)
            lines.append(f"  • {friendly_name}: {url}")
        
        lines.extend([
            "",
            "Note: You only need keys for providers you plan to use.",
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def suggest_alternative_providers(
        cls,
        original_provider: str
    ) -> Optional[str]:
        """
        Suggest alternative providers that have API keys configured.
        
        Args:
            original_provider: The provider that failed
            
        Returns:
            Formatted suggestion string or None if no alternatives
        """
        available = cls.check_available_providers()
        
        # Find available alternatives
        alternatives = [
            p for p in available.keys() 
            if available[p] and p != original_provider
        ]
        
        if not alternatives:
            return None
        
        friendly_alternatives = [
            cls.PROVIDER_FRIENDLY_NAMES.get(p, p) 
            for p in alternatives
        ]
        
        suggestion = [
            "",
            "💡 Tip: You have API keys configured for these providers:",
            "  " + ", ".join(friendly_alternatives),
            "",
            "Try using one of them instead, or get an API key for",
            f"{cls.PROVIDER_FRIENDLY_NAMES.get(original_provider, original_provider)}.",
        ]
        
        return "\n".join(suggestion)
    
    @classmethod
    def create_env_file_if_missing(cls) -> bool:
        """
        Create .env file from .env.example if it doesn't exist.
        
        Returns:
            True if created, False if already exists or creation failed
        """
        env_path = Path(".env")
        env_example_path = Path(".env.example")
        
        # Skip if .env already exists
        if env_path.exists():
            return False
        
        # Skip if .env.example doesn't exist
        if not env_example_path.exists():
            return False
        
        try:
            # Copy .env.example to .env
            content = env_example_path.read_text()
            env_path.write_text(content)
            return True
        except Exception:
            return False


# Convenience functions for common use cases

def get_api_key_or_error(provider: str, api_key: Optional[str] = None) -> str:
    """
    Get API key for a provider or raise helpful error.
    
    Args:
        provider: Provider name
        api_key: Optional API key to use
        
    Returns:
        API key string
        
    Raises:
        ValueError: With helpful error message if key not found
    """
    is_valid, error_message = APIKeyHelper.validate_api_key(provider, api_key)
    
    if not is_valid:
        # Add suggestion for alternative providers
        suggestion = APIKeyHelper.suggest_alternative_providers(provider)
        if suggestion:
            error_message += suggestion
        
        raise ValueError(error_message)
    
    return APIKeyHelper.get_api_key(provider, api_key)


def print_setup_instructions() -> None:
    """Print API key setup instructions to console with rich formatting."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    available = APIKeyHelper.check_available_providers()
    
    # Count configured providers
    configured_count = sum(1 for v in available.values() if v)
    total_count = len(available)
    
    # API Key Status Table
    status_table = Table(show_header=True, header_style="bold magenta", title="API Key Status")
    status_table.add_column("Provider", style="cyan")
    status_table.add_column("Status", justify="center")
    status_table.add_column("Environment Variable", style="dim")
    
    for provider in sorted(available.keys()):
        is_available = available[provider]
        status = "[green]✓ Configured[/green]" if is_available else "[yellow]⚠ Missing[/yellow]"
        friendly_name = APIKeyHelper.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider, "N/A")
        
        status_table.add_row(friendly_name, status, env_key)
    
    console.print(status_table)
    
    # Summary
    if configured_count == 0:
        console.print(f"\n[yellow]⚠ No providers configured[/yellow]")
    elif configured_count == total_count:
        console.print(f"\n[green]✓ All {total_count} providers configured![/green]")
    else:
        console.print(f"\n[cyan]{configured_count}/{total_count} providers configured[/cyan]")
    
    # Provider signup URLs table
    console.print("\n[bold magenta]Available Providers[/bold magenta]")
    
    providers_table = Table(show_header=True, header_style="bold magenta")
    providers_table.add_column("Provider", style="cyan")
    providers_table.add_column("Get API Key", style="blue")
    
    for provider in sorted(APIKeyHelper.PROVIDER_SIGNUP_URLS.keys()):
        friendly_name = APIKeyHelper.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        url = APIKeyHelper.PROVIDER_SIGNUP_URLS.get(provider)
        providers_table.add_row(friendly_name, url)
    
    console.print(providers_table)
    
    # Help tip
    console.print("\n[dim]💡 Tip: You only need to configure providers you plan to use[/dim]")


def check_provider_available(provider: str) -> bool:
    """
    Check if a provider has an API key configured.
    
    Args:
        provider: Provider name
        
    Returns:
        True if API key is available, False otherwise
    """
    available = APIKeyHelper.check_available_providers()
    return available.get(provider, False)
