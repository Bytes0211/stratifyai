"""Example usage of the Router for intelligent model selection."""

import sys
from pathlib import Path
from dotenv import load_dotenv
    
# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from stratifyai import LLMClient, Message, ChatRequest, Router, RoutingStrategy


def basic_routing_example():
    """Basic router usage with different strategies."""
    print("=== Basic Router Usage ===\n")
    
    # Create router with different strategies
    strategies = [
        RoutingStrategy.COST,
        RoutingStrategy.QUALITY,
        RoutingStrategy.LATENCY,
        RoutingStrategy.HYBRID,
    ]
    
    messages = [Message(role="user", content="What is the capital of France?")]
    
    for strategy in strategies:
        router = Router(strategy=strategy, excluded_providers=["ollama"])
        provider, model = router.route(messages)
        print(f"{strategy.value.upper():10} → {provider:12} / {model}")
    
    print()


def complexity_based_routing():
    """Demonstrate complexity-based routing."""
    print("=== Complexity-Based Routing ===\n")
    
    router = Router(strategy=RoutingStrategy.HYBRID, excluded_providers=["ollama"])
    
    # Simple query
    simple_messages = [Message(role="user", content="Say hello")]
    provider1, model1 = router.route(simple_messages)
    complexity1 = router._analyze_complexity(simple_messages)
    print(f"Simple query (complexity={complexity1:.3f}):")
    print(f"  → {provider1} / {model1}\n")
    
    # Complex query
    complex_messages = [
        Message(
            role="user",
            content=(
                "Analyze the following mathematical proof step by step, "
                "explaining each reasoning step in detail and calculating "
                "the final result."
            )
        )
    ]
    provider2, model2 = router.route(complex_messages)
    complexity2 = router._analyze_complexity(complex_messages)
    print(f"Complex query (complexity={complexity2:.3f}):")
    print(f"  → {provider2} / {model2}\n")


def constrained_routing():
    """Demonstrate routing with constraints."""
    print("=== Routing with Constraints ===\n")
    
    router = Router(excluded_providers=["ollama"])
    messages = [Message(role="user", content="Hello")]
    
    # Cost constraint
    provider, model = router.route(messages, max_cost_per_1k_tokens=0.002)
    meta = router.get_model_info(provider, model)
    avg_cost = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 2000
    print(f"Max cost $0.002/1k tokens → {provider}/{model} (${avg_cost:.4f}/1k)")
    
    # Latency constraint
    provider, model = router.route(messages, max_latency_ms=1000)
    meta = router.get_model_info(provider, model)
    print(f"Max latency 1000ms → {provider}/{model} ({meta.avg_latency_ms:.0f}ms)")
    
    # Capability constraint
    provider, model = router.route(messages, required_capabilities=["vision"])
    meta = router.get_model_info(provider, model)
    print(f"Vision capability → {provider}/{model} (caps: {', '.join(meta.capabilities)})")
    
    print()


def preferred_providers_example():
    """Demonstrate preferred provider routing."""
    print("=== Preferred Providers ===\n")
    
    messages = [Message(role="user", content="Hello")]
    
    # Prefer OpenAI
    router1 = Router(preferred_providers=["openai"])
    provider1, model1 = router1.route(messages)
    print(f"Prefer OpenAI → {provider1}/{model1}")
    
    # Prefer Anthropic
    router2 = Router(preferred_providers=["anthropic"])
    provider2, model2 = router2.route(messages)
    print(f"Prefer Anthropic → {provider2}/{model2}")
    
    # Exclude expensive providers
    router3 = Router(excluded_providers=["openai", "anthropic"])
    provider3, model3 = router3.route(messages)
    print(f"Exclude OpenAI/Anthropic → {provider3}/{model3}")
    
    print()


def list_available_models():
    """List all available models with metadata."""
    print("=== Available Models ===\n")
    
    router = Router()
    
    # List all models
    print("All models:")
    models = router.list_models()
    print(f"  Total: {len(models)} models\n")
    
    # List vision-capable models
    print("Vision-capable models:")
    vision_models = router.list_models(required_capabilities=["vision"])
    for provider, model, meta in vision_models[:5]:  # Show first 5
        print(f"  {provider:12} / {model:30} (quality: {meta.quality_score:.2f})")
    print(f"  ... and {len(vision_models) - 5} more\n")
    
    # List reasoning models
    print("Reasoning models:")
    reasoning_models = router.list_models(required_capabilities=["reasoning"])
    for provider, model, meta in reasoning_models:
        print(f"  {provider:12} / {model:30} (quality: {meta.quality_score:.2f})")
    
    print()


def integrated_example():
    """Full example: route, then use LLMClient."""
    print("=== Integrated Router + LLMClient Example ===\n")
    
    # Create router
    router = Router(
        strategy=RoutingStrategy.COST,
        excluded_providers=["ollama"]
    )
    
    # Prepare messages
    messages = [Message(role="user", content="Say 'Hello, World!' in French")]
    
    # Route to best model
    provider, model = router.route(messages)
    print(f"Router selected: {provider}/{model}")
    
    # Use LLMClient with selected provider/model
    client = LLMClient(provider=provider)
    request = ChatRequest(model=model, messages=messages, max_tokens=20)
    
    try:
        response = client.chat_completion(request)
        print(f"Response: {response.content}")
        print(f"Cost: ${response.usage.cost_usd:.6f}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()


def main():
    """Run all examples."""
    examples = [
        ("Basic Routing", basic_routing_example),
        ("Complexity-Based Routing", complexity_based_routing),
        ("Constrained Routing", constrained_routing),
        ("Preferred Providers", preferred_providers_example),
        ("Available Models", list_available_models),
        ("Integrated Example", integrated_example),
    ]
    
    for title, func in examples:
        try:
            func()
        except Exception as e:
            print(f"Error in {title}: {e}\n")
    
    print("\n✓ Router examples complete!")


if __name__ == "__main__":
    main()
