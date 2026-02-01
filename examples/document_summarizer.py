#!/usr/bin/env python3
"""
Document Summarizer - Real-World Example Application

Demonstrates:
- Batch processing of multiple documents
- Prompt caching for cost optimization
- Cost tracking and budget management
- Error handling and retries
- Progress reporting with Rich

Usage:
    python examples/document_summarizer.py documents/*.txt --output summaries.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_abstraction import LLMClient, Router, RoutingStrategy, CostTracker
from llm_abstraction.models import Message
from llm_abstraction.exceptions import LLMException
from llm_abstraction.caching import cache_response

console = Console()


class DocumentSummarizer:
    """Summarize multiple documents with cost tracking and caching."""
    
    def __init__(
        self,
        budget_limit: float = 5.0,
        use_router: bool = True,
        cache_enabled: bool = True
    ):
        """Initialize the summarizer.
        
        Args:
            budget_limit: Maximum spend in USD
            use_router: Use intelligent routing vs fixed model
            cache_enabled: Enable response caching
        """
        self.client = LLMClient()
        self.tracker = CostTracker(budget_limit=budget_limit)
        self.use_router = use_router
        self.cache_enabled = cache_enabled
        
        if use_router:
            self.router = Router(
                self.client,
                default_strategy=RoutingStrategy.COST  # Optimize for cost
            )
    
    def load_document(self, file_path: Path) -> str:
        """Load document from file.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Document content as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            console.print(f"[red]Error loading {file_path}: {e}[/red]")
            return ""
    
    def summarize_one(
        self,
        content: str,
        max_length: int = 200,
        style: str = "bullet_points"
    ) -> Dict[str, Any]:
        """Summarize a single document.
        
        Args:
            content: Document content
            max_length: Maximum summary length in words
            style: Summary style (bullet_points, paragraph, executive)
            
        Returns:
            Dictionary with summary, model, cost, etc.
        """
        # Prepare prompt based on style
        style_prompts = {
            "bullet_points": "Summarize the following document as bullet points:",
            "paragraph": "Summarize the following document in a concise paragraph:",
            "executive": "Provide an executive summary of the following document:"
        }
        
        prompt = f"""{style_prompts.get(style, style_prompts['bullet_points'])}

Maximum length: {max_length} words

Document:
{content}
"""
        
        messages = [
            Message(role="system", content="You are a professional document summarizer."),
            Message(role="user", content=prompt)
        ]
        
        try:
            # Route or use fixed model
            if self.use_router:
                response = self.router.route(
                    messages=messages,
                    strategy=RoutingStrategy.COST
                )
            else:
                response = self.client.chat(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.3  # Lower temp for factual summaries
                )
            
            # Track cost
            self.tracker.record_call(
                model=response.model,
                provider=response.provider,
                usage=response.usage
            )
            
            # Check budget
            within_budget, remaining = self.tracker.check_budget()
            if not within_budget:
                console.print(f"[yellow]⚠ Budget exceeded! Remaining: ${remaining:.2f}[/yellow]")
            
            return {
                "summary": response.content,
                "model": response.model,
                "provider": response.provider,
                "tokens": response.usage.total_tokens,
                "cost": response.usage.cost_usd,
                "success": True
            }
            
        except LLMException as e:
            console.print(f"[red]Error during summarization: {e}[/red]")
            return {
                "summary": None,
                "error": str(e),
                "success": False
            }
    
    def summarize_batch(
        self,
        file_paths: List[Path],
        max_length: int = 200,
        style: str = "bullet_points"
    ) -> List[Dict[str, Any]]:
        """Summarize multiple documents with progress tracking.
        
        Args:
            file_paths: List of document file paths
            max_length: Maximum summary length
            style: Summary style
            
        Returns:
            List of summary results
        """
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"[cyan]Summarizing {len(file_paths)} documents...",
                total=len(file_paths)
            )
            
            for file_path in file_paths:
                progress.update(task, description=f"[cyan]Processing {file_path.name}...")
                
                # Load document
                content = self.load_document(file_path)
                if not content:
                    results.append({
                        "file": str(file_path),
                        "error": "Failed to load document",
                        "success": False
                    })
                    progress.advance(task)
                    continue
                
                # Summarize
                result = self.summarize_one(content, max_length, style)
                result["file"] = str(file_path)
                result["size_chars"] = len(content)
                results.append(result)
                
                progress.advance(task)
        
        return results
    
    def print_summary_table(self, results: List[Dict[str, Any]]):
        """Print summary results as a Rich table.
        
        Args:
            results: List of summary results
        """
        table = Table(title="Document Summaries")
        table.add_column("File", style="cyan")
        table.add_column("Model", style="green")
        table.add_column("Size", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="yellow")
        table.add_column("Status", justify="center")
        
        for result in results:
            file_name = Path(result["file"]).name
            
            if result["success"]:
                table.add_row(
                    file_name,
                    result.get("model", "N/A"),
                    f"{result.get('size_chars', 0):,} chars",
                    f"{result.get('tokens', 0):,}",
                    f"${result.get('cost', 0):.4f}",
                    "✅"
                )
            else:
                table.add_row(
                    file_name,
                    "N/A",
                    "N/A",
                    "N/A",
                    "$0.0000",
                    "❌"
                )
        
        console.print(table)
    
    def print_cost_summary(self):
        """Print cost tracking summary."""
        summary = self.tracker.get_summary()
        
        console.print("\n[bold cyan]Cost Summary:[/bold cyan]")
        console.print(f"  Total Cost: [yellow]${summary['total_cost']:.4f}[/yellow]")
        console.print(f"  Total Calls: {summary['total_calls']}")
        
        if summary['by_provider']:
            console.print("\n  By Provider:")
            for provider, cost in summary['by_provider'].items():
                console.print(f"    - {provider}: ${cost:.4f}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize multiple documents using StratumAI"
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="Document files to summarize"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file for summaries"
    )
    parser.add_argument(
        "--budget",
        "-b",
        type=float,
        default=5.0,
        help="Budget limit in USD (default: 5.0)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=200,
        help="Maximum summary length in words (default: 200)"
    )
    parser.add_argument(
        "--style",
        choices=["bullet_points", "paragraph", "executive"],
        default="bullet_points",
        help="Summary style (default: bullet_points)"
    )
    parser.add_argument(
        "--no-router",
        action="store_true",
        help="Disable intelligent routing (use fixed model)"
    )
    
    args = parser.parse_args()
    
    # Validate files exist
    file_paths = [f for f in args.files if f.exists() and f.is_file()]
    if not file_paths:
        console.print("[red]Error: No valid files found[/red]")
        return 1
    
    # Create summarizer
    console.print(f"\n[bold]Document Summarizer[/bold]")
    console.print(f"Files: {len(file_paths)}")
    console.print(f"Budget: ${args.budget:.2f}")
    console.print(f"Style: {args.style}")
    console.print(f"Router: {'Enabled' if not args.no_router else 'Disabled'}\n")
    
    summarizer = DocumentSummarizer(
        budget_limit=args.budget,
        use_router=not args.no_router
    )
    
    # Process documents
    results = summarizer.summarize_batch(
        file_paths,
        max_length=args.max_length,
        style=args.style
    )
    
    # Display results
    summarizer.print_summary_table(results)
    summarizer.print_cost_summary()
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]✓ Summaries saved to {args.output}[/green]")
    
    # Print example summary
    if results and results[0].get("success"):
        console.print("\n[bold cyan]Example Summary:[/bold cyan]")
        console.print(f"[dim]File: {Path(results[0]['file']).name}[/dim]")
        console.print(results[0]["summary"])
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
