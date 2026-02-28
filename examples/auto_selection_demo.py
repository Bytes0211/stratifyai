"""Demo of Phase 7.3: Automatic Model Selection for File Types.

This example demonstrates how StratifyAI automatically selects the optimal
model based on file type and extraction task.
"""

from pathlib import Path
from stratifyai.utils.model_selector import (
    ModelSelector,
    ExtractionMode,
    select_model_for_file,
)
from stratifyai.router import Router
from stratifyai.utils.file_analyzer import FileType


def demo_model_selector():
    """Demonstrate ModelSelector class."""
    print("=" * 80)
    print("Phase 7.3 Demo: Automatic Model Selection")
    print("=" * 80)
    print()
    
    selector = ModelSelector()
    
    # Example 1: CSV file - should select high-quality model for schema extraction
    print("1. CSV File Auto-Selection")
    print("-" * 40)
    recommendation = selector.select_for_extraction_mode(
        FileType.CSV,
        ExtractionMode.SCHEMA
    )
    print(f"   Provider: {recommendation.provider}")
    print(f"   Model: {recommendation.model}")
    print(f"   Reasoning: {recommendation.reasoning}")
    print(f"   Quality Score: {recommendation.quality_score:.2f}")
    print(f"   Estimated Cost: ${recommendation.estimated_cost_per_1m:.2f}/1M tokens")
    print()
    
    # Example 2: Log file - should select reasoning model for error extraction
    print("2. Log File Auto-Selection")
    print("-" * 40)
    recommendation = selector.select_for_extraction_mode(
        FileType.LOG,
        ExtractionMode.ERRORS
    )
    print(f"   Provider: {recommendation.provider}")
    print(f"   Model: {recommendation.model}")
    print(f"   Reasoning: {recommendation.reasoning}")
    print(f"   Quality Score: {recommendation.quality_score:.2f}")
    print(f"   Estimated Cost: ${recommendation.estimated_cost_per_1m:.2f}/1M tokens")
    print()
    
    # Example 3: Python file - should select code-optimized model
    print("3. Python Code Auto-Selection")
    print("-" * 40)
    recommendation = selector.select_for_extraction_mode(
        FileType.PYTHON,
        ExtractionMode.STRUCTURE
    )
    print(f"   Provider: {recommendation.provider}")
    print(f"   Model: {recommendation.model}")
    print(f"   Reasoning: {recommendation.reasoning}")
    print(f"   Quality Score: {recommendation.quality_score:.2f}")
    print(f"   Estimated Cost: ${recommendation.estimated_cost_per_1m:.2f}/1M tokens")
    print()
    
    # Example 4: Text file - should select fast/cost-effective model
    print("4. Text File Auto-Selection (Summary)")
    print("-" * 40)
    recommendation = selector.select_for_extraction_mode(
        FileType.TEXT,
        ExtractionMode.SUMMARY
    )
    print(f"   Provider: {recommendation.provider}")
    print(f"   Model: {recommendation.model}")
    print(f"   Reasoning: {recommendation.reasoning}")
    print(f"   Quality Score: {recommendation.quality_score:.2f}")
    print(f"   Estimated Cost: ${recommendation.estimated_cost_per_1m:.2f}/1M tokens")
    print()


def demo_router_extraction():
    """Demonstrate Router.route_for_extraction() method."""
    print("=" * 80)
    print("Router Extraction Routing Demo")
    print("=" * 80)
    print()
    
    router = Router()
    
    # Example 1: Schema extraction with quality prioritization
    print("1. Schema Extraction (90% quality weight)")
    print("-" * 40)
    provider, model = router.route_for_extraction(
        file_type=FileType.CSV,
        extraction_mode="schema"
    )
    metadata = router.get_model_info(provider, model)
    print(f"   Selected: {provider}/{model}")
    print(f"   Quality Score: {metadata.quality_score:.2f}")
    print(f"   Strategy: Quality-focused (90% quality, 10% cost)")
    print()
    
    # Example 2: Error extraction with reasoning boost
    print("2. Error Extraction (80% quality weight, reasoning boost)")
    print("-" * 40)
    provider, model = router.route_for_extraction(
        file_type=FileType.LOG,
        extraction_mode="errors"
    )
    metadata = router.get_model_info(provider, model)
    print(f"   Selected: {provider}/{model}")
    print(f"   Quality Score: {metadata.quality_score:.2f}")
    print(f"   Reasoning Model: {metadata.reasoning_model}")
    print()
    
    # Example 3: Summary extraction with balanced weights
    print("3. Summary Extraction (70% quality, 30% cost)")
    print("-" * 40)
    provider, model = router.route_for_extraction(
        file_type=FileType.TEXT,
        extraction_mode="summary"
    )
    metadata = router.get_model_info(provider, model)
    avg_cost = (metadata.cost_per_1m_input + metadata.cost_per_1m_output) / 2
    print(f"   Selected: {provider}/{model}")
    print(f"   Quality Score: {metadata.quality_score:.2f}")
    print(f"   Avg Cost: ${avg_cost:.2f}/1M tokens")
    print()


def demo_cli_usage():
    """Show CLI usage examples."""
    print("=" * 80)
    print("CLI Usage Examples")
    print("=" * 80)
    print()
    
    print("1. Auto-select model for CSV file:")
    print("   stratifyai chat --file data.csv --auto-select")
    print("   → Automatically selects Claude Sonnet for schema extraction")
    print()
    
    print("2. Auto-select with analyze command:")
    print("   stratifyai analyze data.csv")
    print("   → Auto-selects optimal model and shows selection reasoning")
    print()
    
    print("3. Override auto-selection:")
    print("   stratifyai analyze data.csv --provider openai --model gpt-4.5-turbo-20250205")
    print("   → Uses specified provider/model instead of auto-selection")
    print()
    
    print("4. Auto-select for different file types:")
    print("   stratifyai chat --file app.log --auto-select")
    print("   → Selects DeepSeek Reasoner for log error analysis")
    print()
    print("   stratifyai chat --file script.py --auto-select")
    print("   → Selects DeepSeek or Claude for code analysis")
    print()


def main():
    """Run all demos."""
    demo_model_selector()
    print()
    demo_router_extraction()
    print()
    demo_cli_usage()
    
    print("=" * 80)
    print("Benefits of Auto-Selection:")
    print("=" * 80)
    print("✓ CSV/JSON → High-quality models (Claude Sonnet, GPT-4.5)")
    print("✓ Logs → Reasoning models (DeepSeek Reasoner, o1-mini)")
    print("✓ Code → Code-optimized models (DeepSeek, Claude)")
    print("✓ Text → Fast/cost-effective models (Gemini Flash, Groq)")
    print()
    print("Quality Prioritization:")
    print("  • Schema extraction: 90% quality, 10% cost")
    print("  • Error extraction: 80% quality, 20% cost")
    print("  • Structure extraction: 85% quality, 15% cost")
    print("  • Summary: 70% quality, 30% cost")
    print("=" * 80)


if __name__ == "__main__":
    main()
