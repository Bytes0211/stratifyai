"""Examples demonstrating prompt caching functionality in StratifyAI."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from stratifyai import (
    LLMClient,
    Message,
    ResponseCache,
    cache_response,
    clear_cache,
    get_cache_stats,
)


def example_1_basic_response_caching():
    """Example 1: Basic response caching with decorator."""
    print("=" * 60)
    print("Example 1: Basic Response Caching")
    print("=" * 60)
    
    client = LLMClient()
    
    # First call - makes actual API request
    print("\n1. First API call (no cache)...")
    response1 = client.chat(
        model="gpt-4.1-mini",
        messages=[Message(role="user", content="What is 2+2?")],
        temperature=0.7,
    )
    print(f"Response: {response1.content}")
    print(f"Cost: ${response1.usage.cost_usd:.6f}")
    
    # Second call with same parameters - uses cache
    print("\n2. Second API call (same params - should use cache)...")
    response2 = client.chat(
        model="gpt-4.1-mini",
        messages=[Message(role="user", content="What is 2+2?")],
        temperature=0.7,
    )
    print(f"Response: {response2.content}")
    print(f"Cost: ${response2.usage.cost_usd:.6f}")
    
    # Check cache stats
    stats = get_cache_stats()
    print(f"\nCache Stats: {stats}")


def example_2_custom_cache_with_ttl():
    """Example 2: Custom cache with TTL configuration."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Cache with TTL")
    print("=" * 60)
    
    # Create custom cache with 5-minute TTL
    custom_cache = ResponseCache(ttl=300, max_size=100)
    
    # Use custom cache
    client = LLMClient()
    
    @cache_response(ttl=300, cache_instance=custom_cache)
    def cached_chat(**kwargs):
        return client.chat(**kwargs)
    
    print("\n1. Making API call with custom cache...")
    response = cached_chat(
        model="gpt-4.1-mini",
        messages=[Message(role="user", content="Explain quantum computing")],
        temperature=0.7,
    )
    print(f"Response length: {len(response.content)} chars")
    print(f"Cost: ${response.usage.cost_usd:.6f}")
    
    print("\n2. Making same call again (should use cache)...")
    response2 = cached_chat(
        model="gpt-4.1-mini",
        messages=[Message(role="user", content="Explain quantum computing")],
        temperature=0.7,
    )
    print(f"Response length: {len(response2.content)} chars")
    print(f"Cost: ${response2.usage.cost_usd:.6f}")
    
    # Check custom cache stats
    stats = custom_cache.get_stats()
    print(f"\nCustom Cache Stats: {stats}")


def example_3_prompt_caching_with_cache_control():
    """Example 3: Anthropic/OpenAI prompt caching with cache_control."""
    print("\n" + "=" * 60)
    print("Example 3: Prompt Caching with Cache Control")
    print("=" * 60)
    
    client = LLMClient()
    
    # Large context that you want to cache
    long_context = """
    [Imagine a very long document here - 50,000+ tokens]
    This is a comprehensive guide to machine learning...
    [Many more paragraphs of content...]
    """
    
    # Create messages with cache control
    # The long context message is marked for caching
    messages = [
        Message(
            role="system",
            content=long_context,
            cache_control={"type": "ephemeral"}  # Mark for caching
        ),
        Message(
            role="user",
            content="Based on the guide above, explain neural networks."
        ),
    ]
    
    print("\n1. First call - writes to cache...")
    response1 = client.chat(
        model="gpt-4.1-mini",  # Model that supports caching
        messages=messages,
        temperature=0.7,
    )
    print(f"Response: {response1.content[:100]}...")
    print(f"Cost: ${response1.usage.cost_usd:.6f}")
    
    if response1.usage.cache_creation_tokens > 0:
        print(f"Cache creation tokens: {response1.usage.cache_creation_tokens}")
        print(f"Cost breakdown: {response1.usage.cost_breakdown}")
    
    # Second call with same cached context
    messages_2 = [
        Message(
            role="system",
            content=long_context,
            cache_control={"type": "ephemeral"}
        ),
        Message(
            role="user",
            content="Now explain deep learning."  # Different question
        ),
    ]
    
    print("\n2. Second call - reads from cache...")
    response2 = client.chat(
        model="gpt-4.1-mini",
        messages=messages_2,
        temperature=0.7,
    )
    print(f"Response: {response2.content[:100]}...")
    print(f"Cost: ${response2.usage.cost_usd:.6f}")
    
    if response2.usage.cache_read_tokens > 0:
        print(f"Cache read tokens: {response2.usage.cache_read_tokens}")
        print(f"Cost breakdown: {response2.usage.cost_breakdown}")
        print(f"Cost savings: ${response1.usage.cost_usd - response2.usage.cost_usd:.6f}")


def example_4_cache_management():
    """Example 4: Cache management and monitoring."""
    print("\n" + "=" * 60)
    print("Example 4: Cache Management")
    print("=" * 60)
    
    client = LLMClient()
    
    # Make several cached calls
    print("\n1. Making multiple API calls...")
    for i in range(5):
        response = client.chat(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content=f"What is {i+1} + {i+1}?")],
            temperature=0.7,
        )
        print(f"   Call {i+1}: {response.content[:50]}...")
    
    # Check cache stats
    stats = get_cache_stats()
    print(f"\n2. Cache Statistics:")
    print(f"   - Cache size: {stats['size']} entries")
    print(f"   - Max size: {stats['max_size']}")
    print(f"   - Total hits: {stats['total_hits']}")
    print(f"   - TTL: {stats['ttl']} seconds")
    
    # Clear cache
    print("\n3. Clearing cache...")
    clear_cache()
    
    stats_after = get_cache_stats()
    print(f"   Cache size after clear: {stats_after['size']}")


def example_5_cost_comparison():
    """Example 5: Cost comparison with and without caching."""
    print("\n" + "=" * 60)
    print("Example 5: Cost Comparison")
    print("=" * 60)
    
    client = LLMClient()
    
    # Simulate a scenario with repeated queries
    queries = [
        "What is machine learning?",
        "What is deep learning?",
        "What is machine learning?",  # Repeat
        "What is neural network?",
        "What is deep learning?",  # Repeat
    ]
    
    total_cost_with_cache = 0.0
    cache_hits = 0
    
    print("\nMaking API calls with caching enabled:")
    for i, query in enumerate(queries, 1):
        # Get cache stats before
        stats_before = get_cache_stats()
        
        response = client.chat(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content=query)],
            temperature=0.7,
        )
        
        # Get cache stats after
        stats_after = get_cache_stats()
        
        # Check if this was a cache hit
        was_cache_hit = stats_after["total_hits"] > stats_before["total_hits"]
        if was_cache_hit:
            cache_hits += 1
        
        total_cost_with_cache += response.usage.cost_usd
        
        print(f"{i}. {query[:40]:<40} | Cost: ${response.usage.cost_usd:.6f} | "
              f"{'[CACHE HIT]' if was_cache_hit else '[API CALL]'}")
    
    print(f"\n{'='*60}")
    print(f"Total cost with caching: ${total_cost_with_cache:.6f}")
    print(f"Cache hits: {cache_hits}/{len(queries)}")
    print(f"Cache hit rate: {(cache_hits/len(queries))*100:.1f}%")
    
    # Estimate cost without caching (would be higher since all calls are API calls)
    estimated_cost_without_cache = total_cost_with_cache * (len(queries) / (len(queries) - cache_hits))
    savings = estimated_cost_without_cache - total_cost_with_cache
    print(f"Estimated savings: ${savings:.6f} ({(savings/estimated_cost_without_cache)*100:.1f}%)")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("StratifyAI Prompt Caching Examples")
    print("=" * 60)
    
    # Clear cache before starting
    clear_cache()
    
    # Run examples
    try:
        example_1_basic_response_caching()
        example_2_custom_cache_with_ttl()
        example_3_prompt_caching_with_cache_control()
        example_4_cache_management()
        example_5_cost_comparison()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Note: These examples require API keys to be set:")
        print("  - OPENAI_API_KEY for OpenAI models")
        print("  - ANTHROPIC_API_KEY for Anthropic models")


if __name__ == "__main__":
    main()
