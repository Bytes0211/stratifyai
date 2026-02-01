#!/usr/bin/env python3
"""
Multi-Provider Chatbot - Real-World Example Application

Demonstrates:
- Interactive conversation with history
- Model switching mid-conversation
- Conversation persistence (save/load)
- Cost tracking per conversation
- System message customization

Usage:
    python examples/chatbot.py  # Start new conversation
    python examples/chatbot.py --load chat_history.json  # Resume conversation
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_abstraction import LLMClient, CostTracker
from llm_abstraction.models import Message
from llm_abstraction.exceptions import LLMException

console = Console()


class Chatbot:
    """Interactive multi-provider chatbot with conversation history."""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        system_message: Optional[str] = None,
        budget_limit: float = 1.0
    ):
        """Initialize the chatbot.
        
        Args:
            model: Initial model to use
            system_message: Custom system message
            budget_limit: Budget limit in USD
        """
        self.client = LLMClient()
        self.tracker = CostTracker(budget_limit=budget_limit)
        self.current_model = model
        self.conversation: List[Message] = []
        self.metadata = {
            "started_at": datetime.now().isoformat(),
            "model_switches": 0,
            "total_messages": 0
        }
        
        # Set system message
        default_system = "You are a helpful AI assistant. Be concise but informative."
        self.system_message = system_message or default_system
        self.conversation.append(
            Message(role="system", content=self.system_message)
        )
    
    def chat(self, user_input: str) -> Optional[str]:
        """Send a message and get response.
        
        Args:
            user_input: User's message
            
        Returns:
            Assistant's response or None on error
        """
        # Add user message to conversation
        self.conversation.append(Message(role="user", content=user_input))
        self.metadata["total_messages"] += 1
        
        try:
            # Get response
            response = self.client.chat(
                model=self.current_model,
                messages=self.conversation
            )
            
            # Add assistant response to conversation
            self.conversation.append(
                Message(role="assistant", content=response.content)
            )
            self.metadata["total_messages"] += 1
            
            # Track cost
            self.tracker.record_call(
                model=response.model,
                provider=response.provider,
                usage=response.usage
            )
            
            return response.content
            
        except LLMException as e:
            console.print(f"[red]Error: {e}[/red]")
            # Remove user message on error
            self.conversation.pop()
            self.metadata["total_messages"] -= 1
            return None
    
    def switch_model(self, new_model: str):
        """Switch to a different model.
        
        Args:
            new_model: Model identifier
        """
        old_model = self.current_model
        self.current_model = new_model
        self.metadata["model_switches"] += 1
        console.print(f"[cyan]Switched from {old_model} to {new_model}[/cyan]")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation statistics.
        
        Returns:
            Dictionary with conversation stats
        """
        cost_summary = self.tracker.get_summary()
        
        # Count message types
        user_messages = sum(1 for m in self.conversation if m.role == "user")
        assistant_messages = sum(1 for m in self.conversation if m.role == "assistant")
        
        return {
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_messages": len(self.conversation),
            "current_model": self.current_model,
            "model_switches": self.metadata["model_switches"],
            "total_cost": cost_summary["total_cost"],
            "api_calls": cost_summary["total_calls"],
            "started_at": self.metadata["started_at"]
        }
    
    def save_conversation(self, file_path: Path):
        """Save conversation to JSON file.
        
        Args:
            file_path: Output file path
        """
        data = {
            "model": self.current_model,
            "system_message": self.system_message,
            "conversation": [
                {"role": m.role, "content": m.content}
                for m in self.conversation
            ],
            "metadata": self.metadata,
            "summary": self.get_conversation_summary()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        console.print(f"[green]✓ Conversation saved to {file_path}[/green]")
    
    @classmethod
    def load_conversation(cls, file_path: Path) -> 'Chatbot':
        """Load conversation from JSON file.
        
        Args:
            file_path: Input file path
            
        Returns:
            Chatbot instance with loaded conversation
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        bot = cls(
            model=data["model"],
            system_message=data["system_message"]
        )
        
        # Restore conversation (skip system message as it's already added)
        bot.conversation = [
            Message(role=m["role"], content=m["content"])
            for m in data["conversation"]
        ]
        
        # Restore metadata
        bot.metadata = data.get("metadata", bot.metadata)
        
        console.print(f"[green]✓ Loaded conversation with {len(bot.conversation)} messages[/green]")
        
        return bot


class ChatInterface:
    """Terminal interface for the chatbot."""
    
    def __init__(self, bot: Chatbot):
        """Initialize the interface.
        
        Args:
            bot: Chatbot instance
        """
        self.bot = bot
    
    def display_welcome(self):
        """Display welcome message."""
        console.print(Panel(
            "[bold cyan]StratumAI Chatbot[/bold cyan]\n\n"
            "Commands:\n"
            "  /switch <model>  - Switch to different model\n"
            "  /models          - List available models\n"
            "  /stats           - Show conversation statistics\n"
            "  /save <file>     - Save conversation\n"
            "  /clear           - Clear conversation (keep system message)\n"
            "  /quit            - Exit chatbot\n\n"
            "Just type your message to chat!",
            title="Welcome",
            border_style="cyan"
        ))
    
    def display_message(self, role: str, content: str):
        """Display a chat message.
        
        Args:
            role: Message role (user/assistant)
            content: Message content
        """
        if role == "user":
            console.print(f"\n[bold blue]You:[/bold blue] {content}")
        elif role == "assistant":
            console.print(f"\n[bold green]Assistant:[/bold green]")
            console.print(Markdown(content))
    
    def display_stats(self):
        """Display conversation statistics."""
        summary = self.bot.get_conversation_summary()
        cost_tracker_summary = self.bot.tracker.get_summary()
        
        table = Table(title="Conversation Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("User Messages", str(summary["user_messages"]))
        table.add_row("Assistant Messages", str(summary["assistant_messages"]))
        table.add_row("Total Messages", str(summary["total_messages"]))
        table.add_row("Current Model", summary["current_model"])
        table.add_row("Model Switches", str(summary["model_switches"]))
        table.add_row("Total Cost", f"${summary['total_cost']:.4f}")
        table.add_row("API Calls", str(summary["api_calls"]))
        
        console.print("\n")
        console.print(table)
        
        # Show cost by provider
        if cost_tracker_summary.get("by_provider"):
            console.print("\n[bold]Cost by Provider:[/bold]")
            for provider, cost in cost_tracker_summary["by_provider"].items():
                console.print(f"  - {provider}: ${cost:.4f}")
    
    def list_models(self):
        """List available models."""
        # Sample models from different providers
        models = {
            "OpenAI": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini", "o1", "o3-mini"],
            "Anthropic": ["claude-sonnet-4-5-20250929", "claude-haiku-4"],
            "Google": ["gemini-2.5-flash-lite", "gemini-2.5-pro-latest"],
            "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
            "Groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        }
        
        console.print("\n[bold]Available Models:[/bold]")
        for provider, provider_models in models.items():
            console.print(f"\n[cyan]{provider}:[/cyan]")
            for model in provider_models:
                current = " [green](current)[/green]" if model == self.bot.current_model else ""
                console.print(f"  - {model}{current}")
    
    def handle_command(self, user_input: str) -> bool:
        """Handle special commands.
        
        Args:
            user_input: User input
            
        Returns:
            True if should continue, False to quit
        """
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        
        if command == "/quit":
            if Confirm.ask("\nSave conversation before quitting?"):
                filename = Prompt.ask("Filename", default="chat_history.json")
                self.bot.save_conversation(Path(filename))
            return False
        
        elif command == "/switch":
            if len(parts) < 2:
                console.print("[red]Usage: /switch <model>[/red]")
            else:
                self.bot.switch_model(parts[1])
        
        elif command == "/models":
            self.list_models()
        
        elif command == "/stats":
            self.display_stats()
        
        elif command == "/save":
            filename = parts[1] if len(parts) > 1 else "chat_history.json"
            self.bot.save_conversation(Path(filename))
        
        elif command == "/clear":
            if Confirm.ask("Clear conversation history?"):
                # Keep system message
                system_msg = self.bot.conversation[0]
                self.bot.conversation = [system_msg]
                self.bot.metadata["total_messages"] = 0
                console.print("[green]✓ Conversation cleared[/green]")
        
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
        
        return True
    
    def run(self):
        """Run the chat interface."""
        self.display_welcome()
        
        console.print(f"\n[dim]Current model: {self.bot.current_model}[/dim]")
        console.print(f"[dim]Budget: ${self.bot.tracker.budget_limit:.2f}[/dim]\n")
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                    continue
                
                # Regular chat
                self.display_message("user", user_input)
                
                # Get response
                response = self.bot.chat(user_input)
                if response:
                    self.display_message("assistant", response)
                
                # Check budget
                within_budget, remaining = self.bot.tracker.check_budget()
                if not within_budget:
                    console.print(f"\n[yellow]⚠ Budget exceeded! Overspent by ${abs(remaining):.2f}[/yellow]")
                    if not Confirm.ask("Continue anyway?"):
                        break
            
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Interrupted[/yellow]")
                if Confirm.ask("Save conversation?"):
                    filename = Prompt.ask("Filename", default="chat_history.json")
                    self.bot.save_conversation(Path(filename))
                break
            
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.print("[dim]Type /quit to exit[/dim]")
        
        # Final stats
        console.print("\n")
        self.display_stats()
        console.print("\n[cyan]Goodbye! 👋[/cyan]\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive multi-provider chatbot"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o-mini",
        help="Initial model to use (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--system",
        "-s",
        help="Custom system message"
    )
    parser.add_argument(
        "--budget",
        "-b",
        type=float,
        default=1.0,
        help="Budget limit in USD (default: 1.0)"
    )
    parser.add_argument(
        "--load",
        "-l",
        type=Path,
        help="Load conversation from file"
    )
    
    args = parser.parse_args()
    
    # Create or load chatbot
    if args.load:
        if not args.load.exists():
            console.print(f"[red]Error: File not found: {args.load}[/red]")
            return 1
        bot = Chatbot.load_conversation(args.load)
    else:
        bot = Chatbot(
            model=args.model,
            system_message=args.system,
            budget_limit=args.budget
        )
    
    # Run interface
    interface = ChatInterface(bot)
    interface.run()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
