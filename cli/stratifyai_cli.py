"""StratifyAI CLI - Unified LLM interface via terminal."""

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

from stratifyai import LLMClient, ChatRequest, Message, Router, RoutingStrategy, get_cache_stats
from stratifyai.caching import get_cache_entries, clear_cache
from stratifyai.config import MODEL_CATALOG, PROVIDER_ENV_VARS
from stratifyai.exceptions import InvalidProviderError, InvalidModelError, AuthenticationError
from stratifyai.summarization import summarize_file
from stratifyai.utils.file_analyzer import analyze_file
from pathlib import Path

# Initialize Typer app and Rich console
app = typer.Typer(
    name="stratifyai",
    help="StratifyAI - Unified LLM CLI across 9 providers",
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
        help="LLM provider (openai, anthropic, google, deepseek, groq, grok, ollama, openrouter, bedrock)"
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
    chunked: bool = typer.Option(
        False,
        "--chunked",
        help="Enable smart chunking and summarization for large files"
    ),
    chunk_size: int = typer.Option(
        50000,
        "--chunk-size",
        help="Chunk size in characters (default: 50000)"
    ),
    auto_select: bool = typer.Option(
        False,
        "--auto-select",
        help="Automatically select optimal model based on file type"
    ),
):
    """Send a chat message to an LLM provider.
    
    Note: For multi-turn conversations with context, use 'stratifyai interactive' instead.
    """
    return _chat_impl(message, provider, model, temperature, max_tokens, stream, system, file, cache_control, chunked, chunk_size, auto_select=auto_select)


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
    chunked: bool = False,
    chunk_size: int = 50000,
    auto_select: bool = False,
    _conversation_history: Optional[List[Message]] = None,
):
    """Internal implementation of chat with conversation history support."""
    try:
        # Auto-select model based on file type if enabled
        if auto_select and file and not (provider and model):
            from stratifyai.utils.model_selector import select_model_for_file
            
            try:
                auto_provider, auto_model, reasoning = select_model_for_file(file)
                provider = auto_provider
                model = auto_model
                console.print(f"\n[cyan]🤖 Auto-selected:[/cyan] {provider}/{model}")
                console.print(f"[dim]   Reason: {reasoning}[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]⚠ Auto-selection failed: {e}[/yellow]")
                console.print("[dim]Falling back to manual selection...[/dim]\n")
        
        # Track if we prompted for provider/model to determine if we should prompt for file
        prompted_for_provider = False
        prompted_for_model = False
        
        # Interactive prompts if not provided
        if not provider:
            prompted_for_provider = True
            console.print("\n[bold cyan]Select Provider[/bold cyan]")
            providers_list = ["openai", "anthropic", "google", "deepseek", "groq", "grok", "ollama", "openrouter", "bedrock"]
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
                        
                        # Analyze file if chunking enabled
                        if chunked:
                            analysis = analyze_file(str(file), provider or "openai", model or "gpt-4o")
                            console.print(f"[cyan]File Analysis:[/cyan]")
                            console.print(f"  Type: {analysis.file_type.value}")
                            console.print(f"  Tokens: ~{analysis.estimated_tokens:,}")
                            console.print(f"  Recommendation: {analysis.recommendation}")
                            
                            if analysis.warning:
                                console.print(f"[yellow]⚠ {analysis.warning}[/yellow]")
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
            # Check if chunking is needed
            if chunked:
                console.print(f"\n[cyan]Chunking and summarizing file...[/cyan]")
                
                # Create client for summarization
                client = LLMClient(provider=provider)
                
                # Summarize file
                result = summarize_file(
                    file_content,
                    client,
                    chunk_size=chunk_size,
                    model=model,  # Use selected model for summarization
                    context=f"Analyzing file: {file.name if isinstance(file, Path) else 'uploaded file'}" if message is None else message,
                    show_progress=True
                )
                
                # Show reduction stats
                console.print(f"[green]✓ Summarization complete[/green]")
                console.print(f"[dim]Original: {result['original_length']:,} chars | Summary: {result['summary_length']:,} chars | Reduction: {result['reduction_percentage']}%[/dim]")
                
                # Use summary as content
                content = f"{message}\n\nFile Summary:\n{result['summary']}" if message else f"File Summary:\n{result['summary']}"
            else:
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
                response = client.chat_completion_sync(request)
                response_content = response.content
            
            # Display metadata before response
            console.print(f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
            
            # Build usage line with token breakdown and cache info
            usage_parts = [
                f"Context: {context_window:,} tokens",
                f"In: {response.usage.prompt_tokens:,}",
                f"Out: {response.usage.completion_tokens:,}",
                f"Total: {response.usage.total_tokens:,}",
                f"Cost: ${response.usage.cost_usd:.6f}"
            ]
            
            # Add latency if available
            if response.latency_ms is not None:
                usage_parts.append(f"Latency: {response.latency_ms:.0f}ms")
            
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
            console.print("\n[dim]Tip: Use 'stratifyai interactive' for a better multi-turn conversation experience[/dim]")
        
        # Recursive call with conversation history
        _chat_impl(None, provider, model, temperature, max_tokens, stream, None, None, False, chunked, chunk_size, False, messages)
    
    except InvalidProviderError as e:
        console.print(f"[red]Invalid provider:[/red] {e}")
        raise typer.Exit(1)
    except InvalidModelError as e:
        console.print(f"[red]Invalid model:[/red] {e}")
        raise typer.Exit(1)
    except AuthenticationError as e:
        console.print(f"\n[red]✗ Authentication Failed[/red]")
        console.print(f"[yellow]Provider:[/yellow] {e.provider}")
        console.print(f"[yellow]Issue:[/yellow] API key is missing or invalid\n")
        
        # Get environment variable name for the provider
        env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")
        
        console.print("[bold cyan]How to fix:[/bold cyan]")
        console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
        console.print(f"     export {env_var}=\"your-api-key-here\"")
        console.print(f"\n  2. Or add to your [green].env[/green] file in the project root:")
        console.print(f"     {env_var}=your-api-key-here\n")
        
        # Provider-specific instructions
        if e.provider == "openai":
            console.print("[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]")
        elif e.provider == "anthropic":
            console.print("[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]")
        elif e.provider == "google":
            console.print("[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]")
        elif e.provider == "deepseek":
            console.print("[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]")
        elif e.provider == "groq":
            console.print("[dim]Get your API key from: https://console.groq.com/keys[/dim]")
        elif e.provider == "grok":
            console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
        elif e.provider == "openrouter":
            console.print("[dim]Get your API key from: https://openrouter.ai/keys[/dim]")
        elif e.provider == "ollama":
            console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")
        
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
    capability: Optional[List[str]] = typer.Option(
        None,
        "--capability", "-c",
        help="Required capability (vision, tools, reasoning). Can be specified multiple times."
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
        
        # Validate capabilities
        valid_capabilities = ["vision", "tools", "reasoning"]
        if capability:
            for cap in capability:
                if cap not in valid_capabilities:
                    console.print(f"[red]Invalid capability:[/red] {cap}. Use: vision, tools, or reasoning")
                    raise typer.Exit(1)
        
        # Route with constraints
        provider, model = router.route(
            messages,
            required_capabilities=capability,
            max_cost_per_1k_tokens=max_cost,
            max_latency_ms=max_latency
        )
        
        # Get complexity and model info
        complexity = router._analyze_complexity(messages)
        model_info = router.get_model_info(provider, model)
        
        # Display routing decision
        console.print(f"\n[bold]Routing Decision[/bold]")
        console.print(f"Strategy: [cyan]{strategy}[/cyan]")
        if capability:
            console.print(f"Required: [magenta]{', '.join(capability)}[/magenta]")
        console.print(f"Complexity: [yellow]{complexity:.3f}[/yellow]")
        console.print(f"Selected: [green]{provider}/{model}[/green]")
        if model_info.capabilities:
            console.print(f"Capabilities: [magenta]{', '.join(model_info.capabilities)}[/magenta]")
        console.print(f"Quality: [yellow]{model_info.quality_score:.2f}[/yellow]")
        console.print(f"Latency: [yellow]{model_info.avg_latency_ms:.0f}ms[/yellow]")
        
        # Execute if requested
        if execute or Confirm.ask("\nExecute with this model?", default=True):
            client = LLMClient(provider=provider)
            request = ChatRequest(model=model, messages=messages)
            
            # Show spinner while waiting for response
            with console.status("[cyan]Thinking...", spinner="dots"):
                response = client.chat_completion_sync(request)
            
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
        # Helper function to load file with size validation and intelligent extraction
        def load_file_content(file_path: Path, warn_large: bool = True) -> Optional[str]:
            """Load file content with size restrictions, warnings, and intelligent extraction."""
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
                
                # Check if file type supports intelligent extraction
                extension = file_path.suffix.lower()
                supports_extraction = extension in ['.csv', '.json', '.log', '.py'] or 'log' in file_path.name.lower()
                
                # For large files that support extraction, offer schema extraction
                if supports_extraction and file_size > (LARGE_FILE_THRESHOLD_KB * 1024):
                    console.print(f"[cyan]💡 Large {extension} file detected: {file_size_kb:.1f} KB[/cyan]")
                    console.print("[cyan]This file supports intelligent extraction for efficient LLM processing[/cyan]")
                    
                    use_extraction = Confirm.ask(
                        "Extract schema/structure instead of loading full file? (Recommended)",
                        default=True
                    )
                    
                    if use_extraction:
                        try:
                            from stratifyai.utils.csv_extractor import analyze_csv_file
                            from stratifyai.utils.json_extractor import analyze_json_file
                            from stratifyai.utils.log_extractor import extract_log_summary
                            from stratifyai.utils.code_extractor import analyze_code_file
                            
                            if extension == '.csv':
                                result = analyze_csv_file(file_path)
                                content = result['schema_text']
                                reduction = result['token_reduction_pct']
                                console.print(f"[green]✓ Extracted CSV schema[/green] [dim]({reduction:.1f}% token reduction)[/dim]")
                            elif extension == '.json':
                                result = analyze_json_file(file_path)
                                content = result.get('schema_text', str(result))
                                reduction = result.get('token_reduction_pct', 0)
                                console.print(f"[green]✓ Extracted JSON schema[/green] [dim]({reduction:.1f}% token reduction)[/dim]")
                            elif extension in ['.log', '.txt'] and 'log' in file_path.name.lower():
                                result = extract_log_summary(file_path)
                                content = result['summary_text']
                                reduction = result['token_reduction_pct']
                                console.print(f"[green]✓ Extracted log summary[/green] [dim]({reduction:.1f}% token reduction)[/dim]")
                            elif extension == '.py':
                                result = analyze_code_file(file_path)
                                content = result['structure_text']
                                reduction = result['token_reduction_pct']
                                console.print(f"[green]✓ Extracted code structure[/green] [dim]({reduction:.1f}% token reduction)[/dim]")
                            else:
                                # Fallback to raw content
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                console.print(f"[green]✓ Loaded {file_path.name}[/green] [dim]({file_size_kb:.1f} KB, {len(content):,} chars)[/dim]")
                            
                            return content
                        except Exception as e:
                            console.print(f"[yellow]⚠ Extraction failed: {e}[/yellow]")
                            console.print("[dim]Falling back to loading full file...[/dim]")
                            # Fall through to normal loading
                
                # Warn about large files (if not using extraction)
                if warn_large and file_size > (LARGE_FILE_THRESHOLD_KB * 1024):
                    console.print(f"[yellow]⚠ Large file detected: {file_size_kb:.1f} KB[/yellow]")
                    console.print(f"[yellow]⚠ This will consume substantial tokens and may incur significant costs[/yellow]")
                    
                    if not Confirm.ask("Continue loading full file?", default=False):
                        console.print("[dim]File load cancelled[/dim]")
                        return None
                
                # Read file content normally
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
            providers_list = ["openai", "anthropic", "google", "deepseek", "groq", "grok", "ollama", "openrouter", "bedrock"]
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
            # Validate and display curated models for all providers
            from stratifyai.utils.provider_validator import get_validated_interactive_models
            
            # Show spinner while validating
            with console.status(f"[cyan]Validating {provider} models...", spinner="dots"):
                validation_data = get_validated_interactive_models(provider)
            
            validation_result = validation_data["validation_result"]
            validated_models = validation_data["models"]
            
            # Show validation result
            if validation_result["error"]:
                console.print(f"[yellow]⚠ {validation_result['error']}[/yellow]")
                console.print("[dim]Showing curated models (availability not confirmed)[/dim]")
            else:
                console.print(f"[green]✓ Validated {len(validated_models)} models[/green] [dim]({validation_result['validation_time_ms']}ms)[/dim]")
                
                # Show any unavailable models
                if validation_result["invalid_models"]:
                    invalid_display = []
                    for inv_model in validation_result["invalid_models"]:
                        # Get display name if available
                        invalid_display.append(inv_model.split("/")[-1].split(":")[0])
                    console.print(f"[yellow]⚠ Unavailable: {', '.join(invalid_display)}[/yellow]")
            
            # Build display list
            console.print(f"\n[bold cyan]Available {provider} models:[/bold cyan]")
            
            # Get interactive models config for fallback
            from stratifyai.config import (
                INTERACTIVE_OPENAI_MODELS, INTERACTIVE_ANTHROPIC_MODELS,
                INTERACTIVE_GOOGLE_MODELS, INTERACTIVE_DEEPSEEK_MODELS,
                INTERACTIVE_GROQ_MODELS, INTERACTIVE_GROK_MODELS,
                INTERACTIVE_OPENROUTER_MODELS, INTERACTIVE_OLLAMA_MODELS,
                INTERACTIVE_BEDROCK_MODELS,
            )
            
            interactive_configs = {
                "openai": INTERACTIVE_OPENAI_MODELS,
                "anthropic": INTERACTIVE_ANTHROPIC_MODELS,
                "google": INTERACTIVE_GOOGLE_MODELS,
                "deepseek": INTERACTIVE_DEEPSEEK_MODELS,
                "groq": INTERACTIVE_GROQ_MODELS,
                "grok": INTERACTIVE_GROK_MODELS,
                "openrouter": INTERACTIVE_OPENROUTER_MODELS,
                "ollama": INTERACTIVE_OLLAMA_MODELS,
                "bedrock": INTERACTIVE_BEDROCK_MODELS,
            }
            
            fallback_config = interactive_configs.get(provider, {})
            
            # Use validated models, or fall back to interactive config
            if validated_models:
                available_models = list(validated_models.keys())
                model_metadata = validated_models
            elif fallback_config:
                available_models = list(fallback_config.keys())
                model_metadata = fallback_config
            else:
                console.print(f"[red]No models configured for provider: {provider}[/red]")
                raise typer.Exit(1)
            
            # Display with friendly names and descriptions
            current_category = None
            for i, m in enumerate(available_models, 1):
                meta = model_metadata.get(m, {})
                display_name = meta.get("display_name", m)
                description = meta.get("description", "")
                category = meta.get("category", "")
                
                # Show category header if changed
                if category and category != current_category:
                    console.print(f"  [dim]── {category} ──[/dim]")
                    current_category = category
                
                label = f"  {i}. {display_name}"
                if description:
                    label += f" [dim]- {description}[/dim]"
                console.print(label)
            
            # Retry loop for model selection (shared by all providers)
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
        
        # Initialize client
        client = LLMClient(provider=provider)
        messages: List[Message] = []
        
        # Get model info for context window
        model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
        context_window = model_info.get("context", "N/A")
        
        # Set conversation history limit (reserve 80% for history, 20% for response)
        # Use api_max_input if available (API limit), otherwise use context window
        api_max_input = model_info.get("api_max_input")
        if api_max_input and isinstance(api_max_input, int) and api_max_input > 0:
            # Use API input limit (e.g., Anthropic's 200k limit for Claude Opus 4.5)
            max_history_tokens = int(api_max_input * 0.8)
        elif isinstance(context_window, int) and context_window > 0:
            # Fall back to context window
            max_history_tokens = int(context_window * 0.8)
        else:
            # Default to 128k context window if unknown
            max_history_tokens = int(128000 * 0.8)
        
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
        console.print(f"\n[bold green]StratifyAI Interactive Mode[/bold green]")
        
        # Display context info with API limit warning if applicable
        if api_max_input and api_max_input < context_window:
            console.print(f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{model}[/cyan] | Context: [cyan]{context_window:,} tokens[/cyan] [yellow](API limit: {api_max_input:,})[/yellow]")
        else:
            console.print(f"Provider: [cyan]{provider}[/cyan] | Model: [cyan]{model}[/cyan] | Context: [cyan]{context_window:,} tokens[/cyan]")
        
        console.print("[dim]Commands: /file <path> | /attach <path> | /clear | /save [path] | /provider | /help | exit[/dim]")
        console.print(f"[dim]File size limit: {MAX_FILE_SIZE_MB} MB | Ctrl+C to exit[/dim]\n")
        
        # Conversation loop
        staged_file_content = None  # For /attach command
        staged_file_name = None
        last_response = None  # Track last assistant response for /save command
        
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
            
            elif user_input.startswith('/save'):
                # Save last response to file
                if last_response is None:
                    console.print("[yellow]⚠ No response to save yet[/yellow]")
                    console.print("[dim]Send a message first to get a response, then use /save[/dim]")
                    continue
                
                # Parse filename from command or prompt for it
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    save_path = Path(parts[1].strip()).expanduser()
                else:
                    # Prompt for filename
                    default_name = f"response_{provider}_{model.split('-')[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    filename = Prompt.ask("Save as", default=default_name)
                    save_path = Path(filename).expanduser()
                
                try:
                    # Ensure parent directory exists
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Prepare content with metadata
                    content = f"""# AI Response

**Provider:** {provider}  
**Model:** {model}  
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Tokens:** {last_response.usage.total_tokens:,} (In: {last_response.usage.prompt_tokens:,}, Out: {last_response.usage.completion_tokens:,})  
**Cost:** ${last_response.usage.cost_usd:.6f}

---

{last_response.content}
"""
                    
                    # Write to file
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    file_size = save_path.stat().st_size
                    console.print(f"[green]✓ Response saved to:[/green] {save_path}")
                    console.print(f"[dim]  Size: {file_size:,} bytes ({len(last_response.content):,} chars)[/dim]")
                
                except Exception as e:
                    console.print(f"[red]✗ Error saving file: {e}[/red]")
                
                continue
            
            elif user_input.lower() == '/provider':
                # Switch provider and model
                console.print("\n[bold cyan]Switch Provider and Model[/bold cyan]")
                console.print("[dim]Your conversation history will be preserved[/dim]\n")
                
                # Show available providers
                console.print("[bold cyan]Available providers:[/bold cyan]")
                providers_list = list(MODEL_CATALOG.keys())
                for i, p in enumerate(providers_list, 1):
                    current_marker = " [green](current)[/green]" if p == provider else ""
                    console.print(f"  {i}. {p}{current_marker}")
                
                # Get provider selection
                max_attempts = 3
                new_provider = None
                for attempt in range(max_attempts):
                    provider_choice = Prompt.ask("\nSelect provider")
                    try:
                        provider_idx = int(provider_choice) - 1
                        if 0 <= provider_idx < len(providers_list):
                            new_provider = providers_list[provider_idx]
                            break
                        else:
                            console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}")
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(f"[red]✗ Invalid input.[/red] Please enter a number")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                
                if new_provider is None:
                    console.print("[yellow]Provider not changed[/yellow]")
                    continue
                
                # Validate and display ALL models for the selected provider
                from stratifyai.utils.provider_validator import get_validated_interactive_models
                
                with console.status(f"[cyan]Validating {new_provider} models...", spinner="dots"):
                    validation_data = get_validated_interactive_models(new_provider, all_models=True)
                
                validation_result = validation_data["validation_result"]
                validated_models = validation_data["models"]
                
                # Show validation result
                if validation_result["error"]:
                    console.print(f"[yellow]⚠ {validation_result['error']}[/yellow]")
                    console.print("[dim]Showing all models (availability not confirmed)[/dim]")
                    # Fall back to MODEL_CATALOG if validation fails
                    available_models = list(MODEL_CATALOG[new_provider].keys())
                    model_metadata = MODEL_CATALOG[new_provider]
                else:
                    console.print(f"[green]✓ Validated {len(validated_models)} models[/green] [dim]({validation_result['validation_time_ms']}ms)[/dim]")
                    available_models = list(validated_models.keys())
                    model_metadata = validated_models
                
                # Show available models for new provider
                console.print(f"\n[bold cyan]Current valid models for {new_provider}:[/bold cyan]")
                for i, m in enumerate(available_models, 1):
                    meta = model_metadata.get(m, {})
                    is_reasoning = meta.get("reasoning_model", False)
                    current_marker = " [green](current)[/green]" if m == model and new_provider == provider else ""
                    label = f"  {i}. {m}{current_marker}"
                    if is_reasoning:
                        label += " [yellow](reasoning)[/yellow]"
                    console.print(label)
                
                # Get model selection
                new_model = None
                for attempt in range(max_attempts):
                    model_choice = Prompt.ask("\nSelect model")
                    try:
                        model_idx = int(model_choice) - 1
                        if 0 <= model_idx < len(available_models):
                            new_model = available_models[model_idx]
                            break
                        else:
                            console.print(f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}")
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(f"[red]✗ Invalid input.[/red] Please enter a number")
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                
                if new_model is None:
                    console.print("[yellow]Provider and model not changed[/yellow]")
                    continue
                
                # Update provider and model
                provider = new_provider
                model = new_model
                client = LLMClient(provider=provider)  # Reinitialize client
                
                # Update context window info
                model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
                context_window = model_info.get("context", "N/A")
                api_max_input = model_info.get("api_max_input")
                
                # Update history limit
                if api_max_input and isinstance(api_max_input, int) and api_max_input > 0:
                    max_history_tokens = int(api_max_input * 0.8)
                elif isinstance(context_window, int) and context_window > 0:
                    max_history_tokens = int(context_window * 0.8)
                else:
                    max_history_tokens = int(128000 * 0.8)
                
                console.print(f"\n[green]✓ Switched to:[/green] [cyan]{provider}[/cyan] | [cyan]{model}[/cyan] | [dim]Context: {context_window:,} tokens[/dim]")
                console.print("[dim]Conversation history preserved[/dim]\n")
                continue
            
            elif user_input.lower() == '/help':
                # Display help information
                console.print("\n[bold cyan]Available Commands:[/bold cyan]")
                console.print("  [green]/file <path>[/green]   - Load and send file immediately")
                console.print("  [green]/attach <path>[/green] - Stage file for next message")
                console.print("  [green]/clear[/green]         - Clear staged attachments")
                console.print("  [green]/save [path][/green]   - Save last response to file (markdown format)")
                console.print("  [green]/provider[/green]      - Switch provider and model")
                console.print("  [green]/help[/green]          - Show this help message")
                console.print("  [green]exit, quit, q[/green]  - Exit interactive mode")
                console.print(f"\n[bold cyan]Session Info:[/bold cyan]")
                console.print(f"  Provider: [cyan]{provider}[/cyan]")
                console.print(f"  Model: [cyan]{model}[/cyan]")
                console.print(f"  Context: [cyan]{context_window:,} tokens[/cyan]")
                console.print(f"  File size limit: [cyan]{MAX_FILE_SIZE_MB} MB[/cyan]")
                if staged_file_content:
                    console.print(f"  Staged file: [yellow]📎 {staged_file_name}[/yellow]")
                if last_response:
                    console.print(f"  Last response: [green]✓ Available to save[/green]")
                console.print()
                continue
            
            elif user_input.startswith('/'):
                # Unknown command
                console.print(f"[yellow]Unknown command: {user_input.split()[0]}[/yellow]")
                console.print("[dim]Available commands: /file, /attach, /clear, /save, /provider, /help | Type 'exit' to quit[/dim]")
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
            
            # Truncate conversation history if needed to prevent token limit errors
            # Rough approximation: 1 token ≈ 4 characters
            total_chars = sum(len(msg.content) for msg in messages)
            estimated_tokens = total_chars // 4
            
            if estimated_tokens > max_history_tokens:
                # Keep system messages and remove oldest user/assistant pairs
                system_messages = [msg for msg in messages if msg.role == "system"]
                conversation_messages = [msg for msg in messages if msg.role != "system"]
                
                # Calculate how many messages to keep
                while len(conversation_messages) > 2:  # Keep at least the latest user message
                    # Remove oldest pair (user + assistant)
                    if len(conversation_messages) >= 2:
                        conversation_messages = conversation_messages[2:]
                    
                    # Recalculate tokens
                    total_chars = sum(len(msg.content) for msg in system_messages + conversation_messages)
                    estimated_tokens = total_chars // 4
                    
                    if estimated_tokens <= max_history_tokens:
                        break
                
                # Rebuild messages list
                messages = system_messages + conversation_messages
                
                # Notify user of truncation
                console.print(f"[yellow]⚠ Conversation history truncated (estimated {estimated_tokens:,} tokens)[/yellow]")
            
            # Create request and get response
            request = ChatRequest(model=model, messages=messages)
            
            try:
                # Show spinner while waiting for response
                with console.status("[cyan]Thinking...", spinner="dots"):
                    response = client.chat_completion_sync(request)
                
                # Add assistant message to history
                messages.append(Message(role="assistant", content=response.content))
                
                # Store last response for /save command
                last_response = response
                
                # Display metadata and response
                console.print(f"\n[bold green]Assistant[/bold green]")
                console.print(f"[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]")
                
                # Build usage line with token breakdown and cache info
                usage_parts = [
                    f"Context: {context_window:,} tokens",
                    f"In: {response.usage.prompt_tokens:,}",
                    f"Out: {response.usage.completion_tokens:,}",
                    f"Total: {response.usage.total_tokens:,}",
                    f"Cost: ${response.usage.cost_usd:.6f}"
                ]
                
                # Add latency if available
                if response.latency_ms is not None:
                    usage_parts.append(f"Latency: {response.latency_ms:.0f}ms")
                
                # Add cache statistics if available
                if response.usage.cached_tokens > 0:
                    usage_parts.append(f"Cached: {response.usage.cached_tokens:,}")
                if response.usage.cache_creation_tokens > 0:
                    usage_parts.append(f"Cache Write: {response.usage.cache_creation_tokens:,}")
                if response.usage.cache_read_tokens > 0:
                    usage_parts.append(f"Cache Read: {response.usage.cache_read_tokens:,}")
                
                console.print(f"[dim]{' | '.join(usage_parts)}[/dim]")
                console.print(f"\n{response.content}", style="cyan")
                console.print("[dim]💡 Tip: Use /save to save this response to a file[/dim]\n")
            
            except AuthenticationError as e:
                console.print(f"\n[red]✗ Authentication Failed[/red]")
                console.print(f"[yellow]Provider:[/yellow] {e.provider}")
                console.print(f"[yellow]Issue:[/yellow] API key is missing or invalid\n")
                
                # Get environment variable name for the provider
                env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")
                
                console.print("[bold cyan]How to fix:[/bold cyan]")
                console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
                console.print(f"     export {env_var}=\"your-api-key-here\"")
                console.print(f"\n  2. Or add to your [green].env[/green] file in the project root:")
                console.print(f"     {env_var}=your-api-key-here\n")
                
                # Provider-specific instructions
                if e.provider == "openai":
                    console.print("[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]")
                elif e.provider == "anthropic":
                    console.print("[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]")
                elif e.provider == "google":
                    console.print("[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]")
                elif e.provider == "deepseek":
                    console.print("[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]")
                elif e.provider == "groq":
                    console.print("[dim]Get your API key from: https://console.groq.com/keys[/dim]")
                elif e.provider == "grok":
                    console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
                elif e.provider == "openrouter":
                    console.print("[dim]Get your API key from: https://openrouter.ai/keys[/dim]")
                elif e.provider == "ollama":
                    console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")
                
                # Remove failed user message from history
                messages.pop()
                console.print("[dim]You can continue the conversation after fixing the API key issue.\n[/dim]")
            
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}\n")
                # Remove failed user message from history
                messages.pop()
    
    except AuthenticationError as e:
        console.print(f"\n[red]✗ Authentication Failed[/red]")
        console.print(f"[yellow]Provider:[/yellow] {e.provider}")
        console.print(f"[yellow]Issue:[/yellow] API key is missing or invalid\n")
        
        # Get environment variable name for the provider
        env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")
        
        console.print("[bold cyan]How to fix:[/bold cyan]")
        console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
        console.print(f"     export {env_var}=\"your-api-key-here\"")
        console.print(f"\n  2. Or add to your [green].env[/green] file in the project root:")
        console.print(f"     {env_var}=your-api-key-here\n")
        
        # Provider-specific instructions
        if e.provider == "openai":
            console.print("[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]")
        elif e.provider == "anthropic":
            console.print("[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]")
        elif e.provider == "google":
            console.print("[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]")
        elif e.provider == "deepseek":
            console.print("[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]")
        elif e.provider == "groq":
            console.print("[dim]Get your API key from: https://console.groq.com/keys[/dim]")
        elif e.provider == "grok":
            console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
        elif e.provider == "openrouter":
            console.print("[dim]Get your API key from: https://openrouter.ai/keys[/dim]")
        elif e.provider == "ollama":
            console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")
        
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def analyze(
    file: Path = typer.Argument(
        ...,
        help="File to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="LLM provider for future LLM-enhanced extraction"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Model name for future LLM-enhanced extraction"
    ),
):
    """Analyze file and extract structure/schema for efficient LLM processing.
    
    Supports CSV, JSON, log files, and Python code. Reduces token usage by 80-99%.
    If --provider and --model are not specified, the optimal model is auto-selected.
    """
    try:
        from stratifyai.utils.csv_extractor import analyze_csv_file
        from stratifyai.utils.json_extractor import analyze_json_file
        from stratifyai.utils.log_extractor import extract_log_summary
        from stratifyai.utils.code_extractor import analyze_code_file
        from stratifyai.utils.model_selector import select_model_for_file
        
        # Auto-select model if not specified
        if not provider or not model:
            try:
                auto_provider, auto_model, reasoning = select_model_for_file(file)
                provider = provider or auto_provider
                model = model or auto_model
                console.print(f"\n[cyan]🤖 Auto-selected model:[/cyan] {provider}/{model}")
                console.print(f"[dim]   Reason: {reasoning}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Auto-selection info: {e}[/yellow]")
        
        # Detect file type
        extension = file.suffix.lower()
        
        console.print(f"\n[bold cyan]Analyzing File:[/bold cyan] {file}\n")
        
        try:
            if extension == '.csv':
                result = analyze_csv_file(file)
                console.print("[bold green]CSV Schema Analysis[/bold green]\n")
                console.print(result['schema_text'])
                console.print(f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%")
                console.print(f"[dim]Original: {result['original_size_bytes']:,} bytes → Schema: {result['schema_size_bytes']:,} bytes[/dim]")
            
            elif extension == '.json':
                result = analyze_json_file(file)
                console.print("[bold green]JSON Schema Analysis[/bold green]\n")
                console.print(result)
                console.print(f"\n[bold]Token Reduction:[/bold] {result.get('token_reduction_pct', 0):.1f}%")
            
            elif extension in ['.log', '.txt'] and 'log' in file.name.lower():
                result = extract_log_summary(file)
                console.print("[bold green]Log File Analysis[/bold green]\n")
                console.print(result['summary_text'])
                console.print(f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%")
                console.print(f"[dim]Original: {result['original_size_bytes']:,} bytes → Summary: {result['summary_size_bytes']:,} bytes[/dim]")
            
            elif extension == '.py':
                result = analyze_code_file(file)
                console.print("[bold green]Python Code Structure Analysis[/bold green]\n")
                console.print(result['structure_text'])
                console.print(f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%")
                console.print(f"[dim]Original: {result['original_size_bytes']:,} bytes → Structure: {result['structure_size_bytes']:,} bytes[/dim]")
            
            else:
                console.print(f"[yellow]File type not supported for intelligent extraction: {extension}[/yellow]")
                console.print("[dim]Supported types: .csv, .json, .log, .py[/dim]")
                raise typer.Exit(1)
            
            console.print(f"\n[green]✓ Analysis complete[/green]")
            console.print(f"[dim]Recommendation: Use extracted schema/structure for LLM analysis[/dim]\n")
        
        except Exception as e:
            console.print(f"[red]Error analyzing file:[/red] {e}")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="cache-stats")
def cache_stats(
    detailed: bool = typer.Option(
        False,
        "--detailed", "-d",
        help="Show detailed cache entry information"
    )
):
    """Display cache statistics with cost savings analytics."""
    
    try:
        stats = get_cache_stats()
        
        console.print("\n[bold cyan]📊 Response Cache Statistics[/bold cyan]\n")
        
        # Create main stats table
        table = Table(title="Cache Metrics", show_header=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("Cache Size", f"{stats['size']:,} / {stats['max_size']:,} entries")
        table.add_row("Total Hits", f"{stats['total_hits']:,}")
        table.add_row("Total Misses", f"{stats['total_misses']:,}")
        table.add_row("Total Requests", f"{stats['total_requests']:,}")
        
        # Hit rate with visual indicator
        hit_rate = stats.get('hit_rate', 0.0)
        if hit_rate >= 75:
            hit_rate_str = f"[green]{hit_rate:.1f}%[/green] 🎯"
        elif hit_rate >= 50:
            hit_rate_str = f"[yellow]{hit_rate:.1f}%[/yellow] ⚠️"
        else:
            hit_rate_str = f"[red]{hit_rate:.1f}%[/red] 📉"
        table.add_row("Hit Rate", hit_rate_str)
        
        table.add_row("TTL (Time-to-Live)", f"{stats['ttl']:,} seconds")
        
        console.print(table)
        
        # Cost savings section
        cost_saved = stats.get('total_cost_saved', 0.0)
        if cost_saved > 0 or stats['total_hits'] > 0:
            console.print("\n[bold green]💰 Cost Savings Analysis[/bold green]")
            console.print(f"\n[green]✓[/green] Total Cost Saved: [bold green]${cost_saved:.4f}[/bold green]")
            console.print(f"[dim]   ({stats['total_hits']:,} cached responses avoided API calls)[/dim]")
            
            if stats['total_hits'] > 0:
                avg_savings_per_hit = cost_saved / stats['total_hits']
                console.print(f"[dim]   Average savings per hit: ${avg_savings_per_hit:.6f}[/dim]")
        
        # Detailed entry view
        if detailed and stats['size'] > 0:
            console.print("\n[bold cyan]📝 Cache Entries (Top 10 by hits)[/bold cyan]\n")
            
            entries = get_cache_entries()[:10]  # Top 10
            
            entry_table = Table(show_header=True)
            entry_table.add_column("Provider", style="cyan")
            entry_table.add_column("Model", style="magenta")
            entry_table.add_column("Hits", justify="right", style="yellow")
            entry_table.add_column("Cost Saved", justify="right", style="green")
            entry_table.add_column("Age", justify="right", style="blue")
            entry_table.add_column("Expires In", justify="right", style="red")
            
            for entry in entries:
                age_str = f"{entry['age_seconds']}s"
                expires_str = f"{entry['expires_in']}s"
                cost_str = f"${entry['cost_saved']:.4f}" if entry['cost_saved'] > 0 else "-"
                
                entry_table.add_row(
                    entry['provider'],
                    entry['model'],
                    str(entry['hits']),
                    cost_str,
                    age_str,
                    expires_str
                )
            
            console.print(entry_table)
        
        # Usage tip
        if not detailed and stats['size'] > 0:
            console.print("\n[dim]💡 Tip: Use --detailed flag to see cache entry information[/dim]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error getting cache stats:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="cache-clear")
def cache_clear(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Skip confirmation prompt"
    )
):
    """Clear all cache entries."""
    
    try:
        stats = get_cache_stats()
        
        if stats['size'] == 0:
            console.print("\n[yellow]Cache is already empty.[/yellow]\n")
            return
        
        # Show what will be cleared
        console.print(f"\n[yellow]⚠️  About to clear:[/yellow]")
        console.print(f"   - {stats['size']:,} cache entries")
        console.print(f"   - {stats['total_hits']:,} total hits")
        if stats.get('total_cost_saved', 0) > 0:
            console.print(f"   - ${stats['total_cost_saved']:.4f} saved cost data")
        
        # Confirm unless --force
        if not force:
            confirm = Confirm.ask("\nAre you sure you want to clear the cache?", default=False)
            if not confirm:
                console.print("\n[dim]Cache clear cancelled.[/dim]\n")
                return
        
        # Clear cache
        clear_cache()
        console.print("\n[green]✓ Cache cleared successfully[/green]\n")
        
    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def setup():
    """
    Interactive API key setup wizard.
    
    Shows which providers have API keys configured and provides
    links to get API keys for providers you want to use.
    """
    from stratifyai.api_key_helper import (
        APIKeyHelper,
        print_setup_instructions
    )
    
    console.print("\n[bold cyan]🔑 StratifyAI Setup Wizard[/bold cyan]\n")
    
    # Create .env from .env.example if needed
    if APIKeyHelper.create_env_file_if_missing():
        console.print("[green]✓[/green] Created .env file from .env.example")
        console.print("[dim]  Edit .env to add your API keys[/dim]\n")
    elif not Path(".env").exists():
        console.print("[yellow]⚠[/yellow]  .env file not found")
        console.print("[dim]  Create one by copying .env.example[/dim]\n")
    
    # Show current status
    print_setup_instructions()
    
    # Instructions
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Edit .env file and add API keys for providers you want to use")
    console.print("  2. Run [green]stratifyai check-keys[/green] to verify your setup")
    console.print("  3. Test with: [cyan]stratifyai chat -p openai -m gpt-4o-mini 'Hello'[/cyan]\n")


@app.command(name="check-keys")
def check_keys():
    """
    Check which providers have API keys configured.
    
    Displays a status report showing which providers are ready to use
    and which ones need API keys.
    """
    from stratifyai.api_key_helper import APIKeyHelper
    
    available = APIKeyHelper.check_available_providers()
    
    console.print("\n[bold cyan]🔑 API Key Status[/bold cyan]\n")
    
    # Count configured providers
    configured_count = sum(1 for v in available.values() if v)
    total_count = len(available)
    
    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Environment Variable", style="dim")
    
    for provider in sorted(available.keys()):
        is_available = available[provider]
        status = "[green]✓ Configured[/green]" if is_available else "[red]✗ Missing[/red]"
        friendly_name = APIKeyHelper.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider, "N/A")
        
        table.add_row(friendly_name, status, env_key)
    
    console.print(table)
    
    # Summary
    if configured_count == 0:
        console.print(f"\n[yellow]⚠ No providers configured[/yellow]")
        console.print("[dim]Run [cyan]stratifyai setup[/cyan] to get started[/dim]\n")
    elif configured_count == total_count:
        console.print(f"\n[green]✓ All {total_count} providers configured![/green]\n")
    else:
        console.print(f"\n[cyan]{configured_count}/{total_count} providers configured[/cyan]\n")
    
    # Help tip
    if configured_count < total_count:
        console.print("[dim]💡 Tip: Run [cyan]stratifyai setup[/cyan] to see how to configure missing providers[/dim]\n")


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
