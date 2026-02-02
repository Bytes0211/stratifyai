#!/usr/bin/env python3
"""
Code Reviewer - Real-World Example Application

Demonstrates:
- Code analysis with multiple models
- Quality-focused routing for accurate reviews
- Multi-provider comparison
- Streaming responses for better UX
- Structured output with Rich formatting

Usage:
    python examples/code_reviewer.py mycode.py
    python examples/code_reviewer.py --compare mycode.py  # Compare 3 models
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_abstraction import LLMClient, Router, RoutingStrategy
from llm_abstraction.models import Message
from llm_abstraction.exceptions import LLMAbstractionError

console = Console()


class CodeReviewer:
    """Review code using LLMs with quality-focused routing."""
    
    def __init__(self, use_streaming: bool = False):
        """Initialize the code reviewer.
        
        Args:
            use_streaming: Enable streaming for responses
        """
        self.client = LLMClient()
        self.router = Router(
            self.client,
            default_strategy=RoutingStrategy.QUALITY  # Prioritize quality
        )
        self.use_streaming = use_streaming
    
    def load_code(self, file_path: Path) -> tuple[str, str]:
        """Load code from file and detect language.
        
        Args:
            file_path: Path to code file
            
        Returns:
            Tuple of (code_content, language)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Detect language from extension
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust',
                '.cpp': 'cpp',
                '.c': 'c',
                '.rb': 'ruby',
                '.php': 'php',
            }
            language = lang_map.get(file_path.suffix, 'text')
            
            return code, language
            
        except Exception as e:
            console.print(f"[red]Error loading code: {e}[/red]")
            return "", "text"
    
    def create_review_prompt(
        self,
        code: str,
        language: str,
        focus: str = "all"
    ) -> List[Message]:
        """Create review prompt based on focus area.
        
        Args:
            code: Source code to review
            language: Programming language
            focus: Review focus (all, security, performance, style)
            
        Returns:
            List of messages for the LLM
        """
        focus_instructions = {
            "all": "Provide a comprehensive code review covering security, performance, style, and best practices.",
            "security": "Focus on security vulnerabilities and potential exploits.",
            "performance": "Focus on performance issues and optimization opportunities.",
            "style": "Focus on code style, readability, and maintainability."
        }
        
        system_prompt = f"""You are an expert {language} code reviewer with 15+ years of experience.
Provide actionable, specific feedback with code examples where appropriate.
Focus on: {focus_instructions.get(focus, focus_instructions['all'])}

Structure your review as:
1. **Summary**: Brief overview of code quality
2. **Issues Found**: List of specific issues (if any)
3. **Recommendations**: Concrete improvements with code examples
4. **Good Practices**: What the code does well
"""
        
        user_prompt = f"""Please review the following {language} code:

```{language}
{code}
```

Provide a detailed code review."""
        
        return [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
    
    def review(
        self,
        code: str,
        language: str,
        focus: str = "all",
        model: str = None
    ) -> Dict[str, Any]:
        """Review code with specified model or auto-routing.
        
        Args:
            code: Source code
            language: Programming language
            focus: Review focus area
            model: Specific model to use (None for auto-routing)
            
        Returns:
            Review results dictionary
        """
        messages = self.create_review_prompt(code, language, focus)
        
        try:
            if model:
                # Use specific model
                if self.use_streaming:
                    console.print("\n[cyan]Streaming review...[/cyan]\n")
                    full_review = ""
                    for chunk in self.client.chat_stream(model=model, messages=messages):
                        console.print(chunk.content, end="", markup=False)
                        full_review += chunk.content
                    console.print("\n")
                    response = chunk  # Final chunk has full usage
                    response.content = full_review
                else:
                    response = self.client.chat(model=model, messages=messages)
            else:
                # Use router for quality selection
                response = self.router.route(
                    messages=messages,
                    strategy=RoutingStrategy.QUALITY
                )
            
            return {
                "review": response.content,
                "model": response.model,
                "provider": response.provider,
                "tokens": response.usage.total_tokens,
                "cost": response.usage.cost_usd,
                "success": True
            }
            
        except LLMAbstractionError as e:
            console.print(f"[red]Error during review: {e}[/red]")
            return {
                "review": None,
                "error": str(e),
                "success": False
            }
    
    def compare_models(
        self,
        code: str,
        language: str,
        focus: str = "all"
    ) -> List[Dict[str, Any]]:
        """Compare reviews from multiple models.
        
        Args:
            code: Source code
            language: Programming language
            focus: Review focus area
            
        Returns:
            List of review results from different models
        """
        # Select diverse models for comparison
        models = [
            "gpt-4.1",                      # OpenAI flagship
            "claude-sonnet-4-5-20250929",   # Anthropic flagship
            "gemini-2.5-pro-latest",        # Google flagship
        ]
        
        results = []
        
        for model in models:
            console.print(f"\n[bold cyan]Getting review from {model}...[/bold cyan]")
            result = self.review(code, language, focus, model=model)
            results.append(result)
        
        return results
    
    def display_review(
        self,
        result: Dict[str, Any],
        code: str,
        language: str
    ):
        """Display code review with Rich formatting.
        
        Args:
            result: Review result dictionary
            code: Original source code
            language: Programming language
        """
        if not result["success"]:
            console.print(Panel(
                f"[red]Review failed: {result.get('error', 'Unknown error')}[/red]",
                title="Error",
                border_style="red"
            ))
            return
        
        # Display code
        console.print(Panel(
            Syntax(code, language, theme="monokai", line_numbers=True),
            title=f"[bold]Code under review ({language})[/bold]",
            border_style="blue"
        ))
        
        # Display review
        console.print(Panel(
            Markdown(result["review"]),
            title=f"[bold]Code Review by {result['model']}[/bold]",
            border_style="green"
        ))
        
        # Display metadata
        console.print(f"\n[dim]Model: {result['model']} ({result['provider']})[/dim]")
        console.print(f"[dim]Tokens: {result['tokens']:,} | Cost: ${result['cost']:.4f}[/dim]")
    
    def display_comparison(self, results: List[Dict[str, Any]]):
        """Display comparison of multiple reviews.
        
        Args:
            results: List of review results
        """
        # Create comparison table
        table = Table(title="Model Comparison")
        table.add_column("Model", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="yellow")
        table.add_column("Review Length", justify="right")
        
        for result in results:
            if result["success"]:
                table.add_row(
                    result["model"],
                    result["provider"],
                    f"{result['tokens']:,}",
                    f"${result['cost']:.4f}",
                    f"{len(result['review'])} chars"
                )
        
        console.print("\n")
        console.print(table)
        
        # Display individual reviews
        for i, result in enumerate(results, 1):
            if result["success"]:
                console.print(f"\n[bold]Review {i}: {result['model']}[/bold]")
                console.print(Panel(
                    Markdown(result["review"]),
                    border_style="green"
                ))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Review code using AI models"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Code file to review"
    )
    parser.add_argument(
        "--focus",
        choices=["all", "security", "performance", "style"],
        default="all",
        help="Review focus area (default: all)"
    )
    parser.add_argument(
        "--model",
        "-m",
        help="Specific model to use (default: auto-route)"
    )
    parser.add_argument(
        "--compare",
        "-c",
        action="store_true",
        help="Compare reviews from multiple models"
    )
    parser.add_argument(
        "--stream",
        "-s",
        action="store_true",
        help="Enable streaming output"
    )
    
    args = parser.parse_args()
    
    # Validate file
    if not args.file.exists():
        console.print(f"[red]Error: File not found: {args.file}[/red]")
        return 1
    
    # Create reviewer
    reviewer = CodeReviewer(use_streaming=args.stream)
    
    # Load code
    console.print(f"\n[bold]Code Reviewer[/bold]")
    console.print(f"File: {args.file}")
    console.print(f"Focus: {args.focus}\n")
    
    code, language = reviewer.load_code(args.file)
    if not code:
        return 1
    
    # Review or compare
    if args.compare:
        console.print("[cyan]Comparing reviews from 3 different models...[/cyan]")
        results = reviewer.compare_models(code, language, args.focus)
        reviewer.display_comparison(results)
    else:
        result = reviewer.review(code, language, args.focus, args.model)
        reviewer.display_review(result, code, language)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
