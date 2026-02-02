"""StratumAI CLI - Unified LLM interface via terminal."""

import os
import sys
from datetime import datetime
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.spinner import Spinner
from rich.live import Live
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from llm_abstraction import LLMClient, ChatRequest, Message, Router, RoutingStrategy, get_cache_stats
from llm_abstraction.config import MODEL_CATALOG
from llm_abstraction.exceptions import InvalidProviderError, InvalidModelError
from pathlib import Path

# Initialize Typer app and Rich console
app = typer.Typer(
    name="stratumai",
    help="StratumAI - Unified LLM CLI across 8 providers",
    add_completion=True,
)
console = Console()


@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="Message to send to the LLM"),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        envvar="STRATUMAI_PROVIDER",
        help="LLM provider (openai, anthropic, google, deepseek, groq, grok, ollama, openrouter)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        envvar="STRATUMAI_MODEL",
        help="Model name"
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature", "-t",
        min=0.0, max=2.0,
        help="Temperature (0.0-2.0)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None,
        "--max-tokens",
        help="Maximum tokens to generate"
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="Stream response in real-time"
    ),
    system: Optional[str] = typer.Option(
        None,
        "--system", "-s",
        help="System message"
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file", "-f",
        help="Load content from file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    cache_control: bool = typer.Option(
        False,
        "--cache-control",
        help="Enable prompt caching (for supported providers)"
    ),
):
    """Send a chat message to an LLM provider.
    
    Note: For multi-turn conversations with context, use 'stratumai interactive' instead.
    """
    return _chat_impl(message, provider, model, temperature, max_tokens, stream, system, file, cache_control)


def _chat_impl(
    message: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    stream: bool,
    system: Optional[str],
    file: Optional[Path],
    cache_control: bool,
    _conversation_history: Optional[List[Message]] = None,
):
    """Internal implementation of chat with conversation history support."""
    try:
        # Track if we prompted for provider/model to determine if we should prompt for file
        prompted_for_provider = False
        prompted_for_model = False
        
        # Interactive prompts if not provided
        if not provider:
            prompted_for_provider = True
            console.print("\n[bold cyan]Select Provider[/bold cyan]")
            providers_list = ["openai", "anthropic", "google", "deepseek", "groq", "grok", "ollama", "openrouter"]
            for i, p in enumerate(providers_list, 1):
                console.print(f"  {i}. {p}")
            
            # Retry loop for provider selection
            max_attempts = 3
            for attempt in range(max_attempts):
                provider_choice = Prompt.ask("\nChoose provider", default="1")
                
                try:
                    provider_idx = int(provider_choice) - 1
                    if 0 <= provider_idx < len(providers_list):
                        provider = providers_list[provider_idx]
                        break
                    else:
                        console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                        else:
                            console.print("[yellow]Too many invalid attempts. Using default: openai[/yellow]")
                            provider = "openai"
                except ValueError:
                    console.print(f"[red]✗ Invalid input.[/red] Please enter a number, not letters (e.g., '1' not 'openai')")
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")
                    else:
                        console.print("[yellow]Too many invalid attempts. Using default: openai[/yellow]")
                        provider = "openai"
        
        if not model:
            prompted_for_model = True
            # Show available models for selected provider
            if provider in MODEL_CATALOG:
                console.print(f"\n[bold cyan]Available models for {provider}:[/bold cyan]")
                available_models = list(MODEL_CATALOG[provider].keys())
                for i, m in enumerate(available_models, 1):
                    model_info = MODEL_CATALOG[provider][m]
                    is_reasoning = model_info.get("reasoning_model", False)
                    label = f"  {i}. {m}"
                    if is_reasoning:
                        label += " [yellow](reasoning)[/yellow]"
                    console.print(label)
            
                # Retry loop for model selection
                max_attempts = 3
                model = None
                for attempt in range(max_attempts):
                    model_choice = Prompt.ask("\nSelect model")
                    
                    try:
                        model_idx = int(model_choice) - 1
                        if 0 <= model_idx < len(available_models):
                            model = available_models[model_idx]
                            break
                        else:
                            console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}")
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(f"[red]✗ Invalid input.[/red] Please enter a number, not the model name (e.g., '2' not 'gpt-4o')")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                
                # If still no valid model after retries, exit
                if model is None:
                    console.print(f"[red]Too many invalid attempts. Exiting.[/red]")
                    raise typer.Exit(1)
            else:
                console.print(f"[red]No models found for provider: {provider}[/red]")
                raise typer.Exit(1)
        
        # Check if model has fixed temperature
        if temperature is None:
            model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
            fixed_temp = model_info.get("fixed_temperature")
            
            if fixed_temp is not None:
                temperature = fixed_temp
                console.print(f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]")
            else:
                # Retry loop for temperature input
                max_attempts = 3
                temperature = None
                for attempt in range(max_attempts):
                    temp_input = Prompt.ask(
                        "\n[bold cyan]Temperature[/bold cyan] (0.0-2.0, default 0.7)",
                        default="0.7"
                    )
                    
                    try:
                        temp_value = float(temp_input)
                        if 0.0 <= temp_value <= 2.0:
                            temperature = temp_value
                            break
                        else:
                            console.print("[red]✗ Out of range.[/red] Temperature must be between 0.0 and 2.0")
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(f"[red]✗ Invalid input.[/red] Please enter a number (e.g., '0.7' not '{temp_input}')")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                
                # If still no valid temperature after retries, use default
                if temperature is None:
                    console.print("[yellow]Too many invalid attempts. Using default: 0.7[/yellow]")
                    temperature = 0.7
        
        # Prompt for file if not provided via flag (only in fully interactive mode and non-follow-up messages)
        # Only prompt if we also prompted for provider AND model (fully interactive)
        if not file and _conversation_history is None and prompted_for_provider and prompted_for_model:
            console.print(f"\n[bold cyan]File Attachment (Optional)[/bold cyan]")
            console.print(f"[dim]Attach a file to include its content in your message[/dim]")
            console.print(f"[dim]Max file size: 5 MB | Leave blank to skip[/dim]")
            
            file_path_input = Prompt.ask("\nFile path (or press Enter to skip)", default="")
            
            if file_path_input.strip():
                file = Path(file_path_input.strip()).expanduser()
        
        # Load content from file if provided
        file_content = None
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Get file size for display (only if file exists as Path object)
                try:
                    if isinstance(file, Path) and file.exists():
                        file_size = file.stat().st_size
                        file_size_mb = file_size / (1024 * 1024)
                        file_size_kb = file_size / 1024
                        
                        if file_size_kb < 1:
                            size_str = f"{file_size} bytes"
                        elif file_size_mb < 1:
                            size_str = f"{file_size_kb:.1f} KB"
                        else:
                            size_str = f"{file_size_mb:.2f} MB"
                        
                        console.print(f"[green]✓ Loaded {file.name}[/green] [dim]({size_str}, {len(file_content):,} chars)[/dim]")
                    else:
                        # Fallback for tests or non-Path objects
                        console.print(f"[dim]Loaded content from {file} ({len(file_content)} chars)[/dim]")
                except:
                    # Fallback if stat fails (e.g., in test environments)
                    console.print(f"[dim]Loaded content from {file} ({len(file_content)} chars)[/dim]")
            except Exception as e:
                console.print(f"[red]Error reading file {file}: {e}[/red]")
                raise typer.Exit(1)
        
        if not message and not file_content:
            console.print("\n[bold cyan]Enter your message:[/bold cyan]")
            message = Prompt.ask("Message")
        
        # Build messages - use conversation history if this is a follow-up
        if _conversation_history is None:
            messages = []
            if system:
                messages.append(Message(role="system", content=system))
        else:
            messages = _conversation_history.copy()
        
        # Add file content or message
        if file_content:
            # If both file and message provided, combine them
            content = f"{message}\n\n{file_content}" if message else file_content
            
            # Add cache control for large content if requested
            if cache_control and len(file_content) > 1000:
                messages.append(Message(
                    role="user",
                    content=content,
                    cache_control={"type": "ephemeral"}
                ))
            else:
                messages.append(Message(role="user", content=content))
        else:
            messages.append(Message(role="user", content=message))
        
        # Create client and request
        client = LLMClient(provider=provider)
        request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Execute request
        response_content = ""
        
        # Get model info for context window
        model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
        context_window = model_info.get("context", "N/A")
        
        if stream:
            # Display metadata before streaming
            console.print(f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
            console.print(f"[dim]Context: {context_window:,} tokens[/dim]")
            console.print()  # Newline before streaming
            
            for chunk in client.chat_completion_stream(request):
                print(chunk.content, end="", flush=True)
                response_content += chunk.content
            print()  # Final newline
        else:
            # Show spinner while waiting for response
            with console.status("[cyan]Thinking...", spinner="dots"):
                response = client.chat_completion(request)
                response_content = response.content
            
            # Display metadata before response
            console.print(f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
            
            # Build usage line with cache info if available
            usage_parts = [f"Context: {context_window:,} tokens", f"Tokens: {response.usage.total_tokens}", f"Cost: ${response.usage.cost_usd:.6f}"]
            
            # Add cache statistics if available
            if response.usage.cached_tokens > 0:
                usage_parts.append(f"Cached: {response.usage.cached_tokens:,}")
            if response.usage.cache_creation_tokens > 0:
                usage_parts.append(f"Cache Write: {response.usage.cache_creation_tokens:,}")
            if response.usage.cache_read_tokens > 0:
                usage_parts.append(f"Cache Read: {response.usage.cache_read_tokens:,}")
            
            console.print(f"[dim]{' | '.join(usage_parts)}[/dim]")
            
            # Print response with Rich formatting
            console.print(f"\n{response_content}", style="cyan")
        
        # Add assistant response to history for multi-turn conversation
        messages.append(Message(role="assistant", content=response_content))
        
        # Ask what to do next
        console.print("\n[dim]Options: [1] Continue conversation  [2] Save & continue  [3] Save & exit  [4] Exit[/dim]")
        next_action = Prompt.ask("What would you like to do?", choices=["1", "2", "3", "4"], default="1")
        
        # Handle save requests
        if next_action in ["2", "3"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"response_{timestamp}.md"
            
            filename = Prompt.ask("\nFilename", default=default_filename)
            
            # Ensure .md extension
            if not filename.endswith(".md"):
                filename += ".md"
            
            try:
                with open(filename, "w") as f:
                    f.write(f"# LLM Response\n\n")
                    f.write(f"**Provider:** {provider}\n")
                    f.write(f"**Model:** {model}\n")
                    f.write(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"## Conversation\n\n")
                    
                    # Write full conversation history
                    for msg in messages:
                        if msg.role == "user":
                            f.write(f"**You:** {msg.content}\n\n")
                        elif msg.role == "assistant":
                            f.write(f"**Assistant:** {msg.content}\n\n")
                
                console.print(f"[green]✓ Saved to {filename}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to save: {e}[/red]")
        
        # Exit if requested
        if next_action in ["3", "4"]:
            console.print("[dim]Goodbye![/dim]")
            return
        
        # Continue conversation (options "1" or "2")
        # Suggest interactive mode for better UX
        if _conversation_history is None and len(messages) > 2:
            console.print("\n[dim]Tip: Use 'stratumai interactive' for a better multi-turn conversation experience[/dim]")
        
        # Recursive call with conversation history
        _chat_impl(None, provider, model, temperature, max_tokens, stream, None, None, False, messages)
    
    except InvalidProviderError as e:
        console.print(f"[red]Invalid provider:[/red] {e}")
        raise typer.Exit(1)
    except InvalidModelError as e:
        console.print(f"[red]Invalid model:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def models(
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="Filter by provider"
    ),
):
    """List available models."""
    
    try:
        # Create table
        table = Table(title="Available Models", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan", width=12)
        table.add_column("Model", style="green", width=40)
        table.add_column("Context", justify="right", style="yellow", width=10)
        
        # Populate table
        total_models = 0
        for prov_name, models_dict in MODEL_CATALOG.items():
            if provider and prov_name != provider:
                continue
            
            for model_name, model_info in models_dict.items():
                context = model_info.get("context", 0)
                table.add_row(
                    prov_name,
                    model_name,
                    f"{context:,}" if context else "N/A"
                )
                total_models += 1
        
        # Display table
        console.print(table)
        console.print(f"\n[dim]Total: {total_models} models[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def providers():
    """List all available providers."""
    
    try:
        # Create table
        table = Table(title="Available Providers", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan", width=15)
        table.add_column("Models", justify="right", style="green", width=10)
        table.add_column("Example Model", style="yellow", width=40)
        
        # Populate table
        for prov_name, models_dict in MODEL_CATALOG.items():
            example_model = list(models_dict.keys())[0] if models_dict else "N/A"
            table.add_row(
                prov_name,
                str(len(models_dict)),
                example_model
            )
        
        # Display table
        console.print(table)
        console.print(f"\n[dim]Total: {len(MODEL_CATALOG)} providers[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def route(
    message: str = typer.Argument(..., help="Message to analyze for routing"),
    strategy: str = typer.Option(
        "hybrid",
        "--strategy", "-s",
        help="Routing strategy (cost, quality, latency, hybrid)"
    ),
    execute: bool = typer.Option(
        False,
        "--execute", "-e",
        help="Execute with selected model"
    ),
    max_cost: Optional[float] = typer.Option(
        None,
        "--max-cost",
        help="Maximum cost per 1K tokens"
    ),
    max_latency: Optional[int] = typer.Option(
        None,
        "--max-latency",
        help="Maximum latency in milliseconds"
    ),
):
    """Auto-select best model using router."""
    
    try:
        # Map strategy string to enum
        strategy_map = {
            'cost': RoutingStrategy.COST,
            'quality': RoutingStrategy.QUALITY,
            'latency': RoutingStrategy.LATENCY,
            'hybrid': RoutingStrategy.HYBRID,
        }
        
        if strategy not in strategy_map:
            console.print(f"[red]Invalid strategy:[/red] {strategy}. Use: cost, quality, latency, or hybrid")
            raise typer.Exit(1)
        
        # Create router and route
        router = Router(
            strategy=strategy_map[strategy],
            excluded_providers=['ollama']  # Exclude local models by default
        )
        
        messages = [Message(role="user", content=message)]
        
        # Route with constraints
        provider, model = router.route(
            messages,
            max_cost_per_1k_tokens=max_cost,
            max_latency_ms=max_latency
        )
        
        # Get complexity and model info
        complexity = router._analyze_complexity(messages)
        model_info = router.get_model_info(provider, model)
        
        # Display routing decision
        console.print(f"\n[bold]Routing Decision[/bold]")
        console.print(f"Strategy: [cyan]{strategy}[/cyan]")
        console.print(f"Complexity: [yellow]{complexity:.3f}[/yellow]")
        console.print(f"Selected: [green]{provider}/{model}[/green]")
        console.print(f"Quality: [yellow]{model_info.quality_score:.2f}[/yellow]")
        console.print(f"Latency: [yellow]{model_info.avg_latency_ms:.0f}ms[/yellow]")
        
        # Execute if requested
        if execute or Confirm.ask("\nExecute with this model?", default=True):
            client = LLMClient(provider=provider)
            request = ChatRequest(model=model, messages=messages)
            
            # Show spinner while waiting for response
            with console.status("[cyan]Thinking...", spinner="dots"):
                response = client.chat_completion(request)
            
            # Get model info for context window
            route_model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
            route_context = route_model_info.get("context", "N/A")
            
            console.print(f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
            console.print(f"[dim]Context: {route_context:,} tokens | Tokens: {response.usage.total_tokens} | Cost: ${response.usage.cost_usd:.6f}[/dim]")
            console.print(f"\n{response.content}", style="cyan")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def interactive(
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        envvar="STRATUMAI_PROVIDER",
        help="LLM provider"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        envvar="STRATUMAI_MODEL",
        help="Model name"
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file", "-f",
        help="Load initial context from file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
):
    """Start interactive chat session."""
    
    # File upload constraints
    MAX_FILE_SIZE_MB = 5
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    LARGE_FILE_THRESHOLD_KB = 500
    
    try:
        # Helper function to load file with size validation
        def load_file_content(file_path: Path, warn_large: bool = True) -> Optional[str]:
            """Load file content with size restrictions and warnings."""
            try:
                # Check if file exists
                if not file_path.exists():
                    console.print(f"[red]✗ File not found: {file_path}[/red]")
                    return None
                
                # Check file size
                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                file_size_kb = file_size / 1024
                
                # Enforce size limit
                if file_size > MAX_FILE_SIZE_BYTES:
                    console.print(f"[red]✗ File too large: {file_size_mb:.2f} MB (max {MAX_FILE_SIZE_MB} MB)[/red]")
                    console.print(f"[yellow]⚠ Large files consume significant tokens and may exceed model context limits[/yellow]")
                    return None
                
                # Warn about large files
                if warn_large and file_size > (LARGE_FILE_THRESHOLD_KB * 1024):
                    console.print(f"[yellow]⚠ Large file detected: {file_size_kb:.1f} KB[/yellow]")
                    console.print(f"[yellow]⚠ This will consume substantial tokens and may incur significant costs[/yellow]")
                    
                    if not Confirm.ask("Continue loading this file?", default=False):
                        console.print("[dim]File load cancelled[/dim]")
                        return None
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Display success message
                if file_size_kb < 1:
                    size_str = f"{file_size} bytes"
                elif file_size_mb < 1:
                    size_str = f"{file_size_kb:.1f} KB"
                else:
                    size_str = f"{file_size_mb:.2f} MB"
                
                console.print(f"[green]✓ Loaded {file_path.name}[/green] [dim]({size_str}, {len(content):,} chars)[/dim]")
                return content
                
            except UnicodeDecodeError:
                console.print(f"[red]✗ Cannot read file: {file_path.name} (not a text file)[/red]")
                return None
            except Exception as e:
                console.print(f"[red]✗ Error reading file: {e}[/red]")
                return None
        
        # Prompt for provider and model if not provided
        if not provider:
            console.print("\n[bold cyan]Select Provider[/bold cyan]")
            providers_list = ["openai", "anthropic", "google", "deepseek", "groq", "grok", "ollama", "openrouter"]
            for i, p in enumerate(providers_list, 1):
                console.print(f"  {i}. {p}")
            
            # Retry loop for provider selection
            max_attempts = 3
            for attempt in range(max_attempts):
                provider_choice = Prompt.ask("\nChoose provider", default="1")
                
                try:
                    provider_idx = int(provider_choice) - 1
                    if 0 <= provider_idx < len(providers_list):
                        provider = providers_list[provider_idx]
                        break
                    else:
                        console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                        else:
                            console.print("[yellow]Too many invalid attempts. Using default: openai[/yellow]")
                            provider = "openai"
                except ValueError:
                    console.print(f"[red]✗ Invalid input.[/red] Please enter a number, not letters (e.g., '1' not 'openai')")
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")
                    else:
                        console.print("[yellow]Too many invalid attempts. Using default: openai[/yellow]")
                        provider = "openai"
        
        if not model:
            # Show available models for provider
            if provider in MODEL_CATALOG:
                console.print(f"\n[bold cyan]Available models for {provider}:[/bold cyan]")
                available_models = list(MODEL_CATALOG[provider].keys())
                for i, m in enumerate(available_models, 1):
                    model_info = MODEL_CATALOG[provider][m]
                    is_reasoning = model_info.get("reasoning_model", False)
                    label = f"  {i}. {m}"
                    if is_reasoning:
                        label += " [yellow](reasoning)[/yellow]"
                    console.print(label)
            
                # Retry loop for model selection
                max_attempts = 3
                model = None
                for attempt in range(max_attempts):
                    model_choice = Prompt.ask("\nSelect model")
                    
                    try:
                        model_idx = int(model_choice) - 1
                        if 0 <= model_idx < len(available_models):
                            model = available_models[model_idx]
                            break
                        else:
                            console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}")
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(f"[red]✗ Invalid input.[/red] Please enter a number, not the model name (e.g., '2' not 'gpt-4o')")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                
                # If still no valid model after retries, exit
                if model is None:
                    console.print(f"[red]Too many invalid attempts. Exiting.[/red]")
                    raise typer.Exit(1)
            else:
                console.print(f"[red]No models found for provider: {provider}[/red]")
                raise typer.Exit(1)
        
        # Initialize client
        client = LLMClient(provider=provider)
        messages: List[Message] = []
        
        # Get model info for context window
        model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
        context_window = model_info.get("context", "N/A")
        
        # Prompt for initial file if not provided via flag
        if not file:
            console.print(f"\n[bold cyan]Initial File Context (Optional)[/bold cyan]")
            console.print(f"[dim]Load a file to provide context for the conversation[/dim]")
            console.print(f"[dim]Max file size: {MAX_FILE_SIZE_MB} MB | Leave blank to skip[/dim]")
            
            file_path_input = Prompt.ask("\nFile path (or press Enter to skip)", default="")
            
            if file_path_input.strip():
                file = Path(file_path_input.strip()).expanduser()
        
        # Load initial file if provided
        if file:
            console.print(f"\n[bold cyan]Loading initial context...[/bold cyan]")
            file_content = load_file_content(file, warn_large=True)
            if file_content:
                messages.append(Message(
                    role="user",
                    content=f"[Context from {file.name}]\n\n{file_content}"
                ))
                console.print(f"[dim]File loaded as initial context[/dim]")
        
        # Welcome message
        console.print(f"\n[bold green]StratumAI Interactive Mode[/bold green]")
        console.print(f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{model}[/cyan] | Context: [cyan]{context_window:,} tokens[/cyan]")
        console.print("[dim]Commands: /file <path> | /attach <path> | /clear | exit[/dim]")
        console.print(f"[dim]File size limit: {MAX_FILE_SIZE_MB} MB | Ctrl+C to exit[/dim]\n")
        
        # Conversation loop
        staged_file_content = None  # For /attach command
        staged_file_name = None
        
        while True:
            # Show staged file indicator
            prompt_text = "[bold blue]You[/bold blue]"
            if staged_file_content:
                prompt_text = f"[bold blue]You[/bold blue] [dim]📎 {staged_file_name}[/dim]"
            
            # Get user input
            try:
                user_input = Prompt.ask(prompt_text)
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Exiting...[/dim]")
                break
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[dim]Goodbye![/dim]")
                break
            
            # Handle special commands
            if user_input.startswith('/file '):
                # Load and send file immediately
                file_path_str = user_input[6:].strip()
                file_path = Path(file_path_str).expanduser()
                
                file_content = load_file_content(file_path, warn_large=True)
                if file_content:
                    # Send file content as user message
                    user_input = f"[File: {file_path.name}]\n\n{file_content}"
                    messages.append(Message(role="user", content=user_input))
                else:
                    continue  # Error already displayed, skip to next input
            
            elif user_input.startswith('/attach '):
                # Stage file for next message
                file_path_str = user_input[8:].strip()
                file_path = Path(file_path_str).expanduser()
                
                file_content = load_file_content(file_path, warn_large=True)
                if file_content:
                    staged_file_content = file_content
                    staged_file_name = file_path.name
                    console.print(f"[green]✓ File staged[/green] [dim]- will be attached to your next message[/dim]")
                continue
            
            elif user_input.lower() == '/clear':
                # Clear staged attachment
                if staged_file_content:
                    console.print(f"[yellow]Cleared staged file: {staged_file_name}[/yellow]")
                    staged_file_content = None
                    staged_file_name = None
                else:
                    console.print("[dim]No staged files to clear[/dim]")
                continue
            
            elif user_input.startswith('/'):
                # Unknown command
                console.print(f"[yellow]Unknown command: {user_input.split()[0]}[/yellow]")
                console.print("[dim]Available commands: /file <path>, /attach <path>, /clear[/dim]")
                continue
            
            # Skip empty input (unless there's a staged file)
            if not user_input.strip() and not staged_file_content:
                continue
            
            # Build message content (combine text with staged file if present)
            if staged_file_content:
                if user_input.strip():
                    message_content = f"{user_input}\n\n[Attached: {staged_file_name}]\n\n{staged_file_content}"
                else:
                    message_content = f"[Attached: {staged_file_name}]\n\n{staged_file_content}"
                
                # Clear staged file after use
                staged_file_content = None
                staged_file_name = None
            else:
                message_content = user_input
            
            # Add user message to history
            messages.append(Message(role="user", content=message_content))
            
            # Create request and get response
            request = ChatRequest(model=model, messages=messages)
            
            try:
                # Show spinner while waiting for response
                with console.status("[cyan]Thinking...", spinner="dots"):
                    response = client.chat_completion(request)
                
                # Add assistant message to history
                messages.append(Message(role="assistant", content=response.content))
                
                # Display metadata and response
                console.print(f"\n[bold green]Assistant[/bold green]")
                console.print(f"[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
                
                # Build usage line with cache info
                usage_parts = [f"Context: {context_window:,} tokens", f"Tokens: {response.usage.total_tokens}", f"Cost: ${response.usage.cost_usd:.6f}"]
                
                # Add cache statistics if available
                if response.usage.cached_tokens > 0:
                    usage_parts.append(f"Cached: {response.usage.cached_tokens:,}")
                if response.usage.cache_creation_tokens > 0:
                    usage_parts.append(f"Cache Write: {response.usage.cache_creation_tokens:,}")
                if response.usage.cache_read_tokens > 0:
                    usage_parts.append(f"Cache Read: {response.usage.cache_read_tokens:,}")
                
                console.print(f"[dim]{' | '.join(usage_parts)}[/dim]")
                console.print(f"\n{response.content}", style="cyan")
                console.print()
            
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}\n")
                # Remove failed user message from history
                messages.pop()
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="cache-stats")
def cache_stats():
    """Display cache statistics."""
    
    try:
        stats = get_cache_stats()
        
        console.print("\n[bold cyan]Response Cache Statistics[/bold cyan]\n")
        
        # Create table
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("Cache Size", f"{stats['size']:,} entries")
        table.add_row("Max Size", f"{stats['max_size']:,} entries")
        table.add_row("Total Hits", f"{stats['total_hits']:,}")
        table.add_row("Total Misses", f"{stats['total_misses']:,}")
        
        total_requests = stats['total_hits'] + stats['total_misses']
        if total_requests > 0:
            hit_rate = (stats['total_hits'] / total_requests) * 100
            table.add_row("Hit Rate", f"{hit_rate:.1f}%")
        else:
            table.add_row("Hit Rate", "N/A")
        
        table.add_row("TTL", f"{stats['ttl']} seconds")
        
        console.print(table)
        
        # Cost savings estimation
        if stats['total_hits'] > 0:
            console.print(f"\n[dim]Cache hits save ~{stats['total_hits']} API calls[/dim]")
            console.print(f"[dim]Estimated cost savings: 100% on cached requests[/dim]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error getting cache stats:[/red] {e}")
        raise typer.Exit(1)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
