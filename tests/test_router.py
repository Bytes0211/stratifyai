"""Unit tests for router module."""

import pytest
from stratifyai.router import Router, RoutingStrategy, ModelMetadata
from stratifyai.models import Message


class TestRouter:
    """Test Router class."""
    
    def test_router_initialization(self):
        """Test router initializes correctly."""
        router = Router()
        assert router.strategy == RoutingStrategy.HYBRID
        assert len(router.model_metadata) > 0
    
    def test_router_with_strategy(self):
        """Test router with different strategies."""
        for strategy in RoutingStrategy:
            router = Router(strategy=strategy)
            assert router.strategy == strategy
    
    def test_router_with_excluded_providers(self):
        """Test router excludes specified providers."""
        router = Router(excluded_providers=["ollama"])
        
        # Check that no Ollama models are loaded
        for key, meta in router.model_metadata.items():
            assert meta.provider != "ollama"
    
    def test_router_with_preferred_providers(self):
        """Test router prioritizes preferred providers."""
        router = Router(preferred_providers=["openai"])
        
        messages = [Message(role="user", content="Hello")]
        provider, model = router.route(messages)
        
        # Should select from preferred provider
        assert provider == "openai"


class TestComplexityAnalysis:
    """Test complexity analysis algorithm."""
    
    def test_simple_prompt_low_complexity(self):
        """Test simple prompts have low complexity."""
        router = Router()
        messages = [Message(role="user", content="Say hello")]
        
        complexity = router._analyze_complexity(messages)
        assert 0.0 <= complexity <= 0.3
    
    def test_reasoning_prompt_high_complexity(self):
        """Test reasoning prompts have higher complexity."""
        router = Router()
        messages = [
            Message(
                role="user",
                content="Analyze the following proof step by step and explain your reasoning in detail"
            )
        ]
        
        complexity = router._analyze_complexity(messages)
        assert complexity > 0.15
    
    def test_code_prompt_moderate_complexity(self):
        """Test code prompts have moderate complexity."""
        router = Router()
        messages = [
            Message(
                role="user",
                content="```python\ndef function():\n    pass\n```\nReview this code"
            )
        ]
        
        complexity = router._analyze_complexity(messages)
        assert complexity > 0.05
    
    def test_long_prompt_increases_complexity(self):
        """Test longer prompts increase complexity."""
        router = Router()
        
        short = [Message(role="user", content="Hi")]
        long = [Message(role="user", content="A" * 3000)]
        
        short_complexity = router._analyze_complexity(short)
        long_complexity = router._analyze_complexity(long)
        
        assert long_complexity > short_complexity
    
    def test_math_prompt_complexity(self):
        """Test mathematical prompts have higher complexity."""
        router = Router()
        messages = [
            Message(
                role="user",
                content="Solve the equation 3x + 5 = 20 and calculate the integral"
            )
        ]
        
        complexity = router._analyze_complexity(messages)
        assert complexity > 0.08
    
    def test_multi_turn_conversation_complexity(self):
        """Test multi-turn conversations increase complexity."""
        router = Router()
        
        single = [Message(role="user", content="Hello")]
        multi = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
            Message(role="user", content="How are you?"),
            Message(role="assistant", content="Good"),
            Message(role="user", content="Great!"),
        ]
        
        single_complexity = router._analyze_complexity(single)
        multi_complexity = router._analyze_complexity(multi)
        
        assert multi_complexity > single_complexity


class TestRoutingStrategies:
    """Test different routing strategies."""
    
    def test_cost_strategy_selects_cheapest(self):
        """Test COST strategy selects cheapest model."""
        router = Router(strategy=RoutingStrategy.COST)
        messages = [Message(role="user", content="Hello")]
        
        provider, model = router.route(messages)
        
        # Should select a cheap model (Groq, Gemini Flash, or local)
        assert provider in ["groq", "google", "ollama", "deepseek"]
    
    def test_quality_strategy_selects_best(self):
        """Test QUALITY strategy selects highest quality model."""
        router = Router(strategy=RoutingStrategy.QUALITY, excluded_providers=["ollama"])
        messages = [Message(role="user", content="Hello")]
        
        provider, model = router.route(messages)
        
        # Should select a high-quality model
        assert provider in ["openai", "anthropic", "google"]
    
    def test_latency_strategy_selects_fastest(self):
        """Test LATENCY strategy selects fastest model."""
        router = Router(strategy=RoutingStrategy.LATENCY)
        messages = [Message(role="user", content="Hello")]
        
        provider, model = router.route(messages)
        
        # Should select fast models (Groq or Ollama)
        assert provider in ["groq", "ollama"]
    
    def test_hybrid_strategy_balances_factors(self):
        """Test HYBRID strategy balances cost, quality, and latency."""
        router = Router(strategy=RoutingStrategy.HYBRID, excluded_providers=["ollama"])
        
        # Simple task should favor cost/speed
        simple_messages = [Message(role="user", content="Say hi")]
        provider1, model1 = router.route(simple_messages)
        
        # Complex task should favor quality
        complex_messages = [
            Message(
                role="user",
                content="Analyze this complex mathematical proof step by step with detailed reasoning"
            )
        ]
        provider2, model2 = router.route(complex_messages)
        
        # Providers may differ based on complexity
        # For simple tasks, might select cheaper/faster models
        # For complex tasks, might select higher quality models
        assert provider1 in ["openai", "anthropic", "google", "groq", "deepseek", "grok"]
        # Complex tasks should prefer higher quality providers, but Groq can also be selected due to speed
        assert provider2 in ["openai", "anthropic", "google", "deepseek", "groq"]


class TestRoutingConstraints:
    """Test routing with constraints."""
    
    def test_max_cost_constraint(self):
        """Test routing with maximum cost constraint."""
        router = Router()
        messages = [Message(role="user", content="Hello")]
        
        # Set very low cost limit
        provider, model = router.route(messages, max_cost_per_1k_tokens=0.001)
        
        # Should select very cheap or free model
        assert provider in ["ollama", "groq", "deepseek", "google"]
    
    def test_max_latency_constraint(self):
        """Test routing with maximum latency constraint."""
        router = Router()
        messages = [Message(role="user", content="Hello")]
        
        # Set low latency limit
        provider, model = router.route(messages, max_latency_ms=500)
        
        # Should select fast models
        assert provider in ["groq", "ollama", "google"]
    
    def test_min_context_window_constraint(self):
        """Test routing with minimum context window constraint."""
        router = Router()
        messages = [Message(role="user", content="Hello")]
        
        # Require large context window
        provider, model = router.route(messages, min_context_window=100000)
        
        # Should select models with large context windows
        assert provider in ["openai", "anthropic", "google", "groq"]
    
    def test_required_capabilities_vision(self):
        """Test routing with vision capability requirement."""
        router = Router(excluded_providers=["ollama"])
        messages = [Message(role="user", content="Describe this image")]
        
        provider, model = router.route(messages, required_capabilities=["vision"])
        
        # Should select model with vision support
        meta = router.get_model_info(provider, model)
        assert "vision" in meta.capabilities
    
    def test_required_capabilities_tools(self):
        """Test routing with tools capability requirement."""
        router = Router(excluded_providers=["ollama"])
        messages = [Message(role="user", content="Call a function")]
        
        provider, model = router.route(messages, required_capabilities=["tools"])
        
        # Should select model with tools support
        meta = router.get_model_info(provider, model)
        assert "tools" in meta.capabilities
    
    def test_required_capabilities_reasoning(self):
        """Test routing with reasoning capability requirement."""
        router = Router(excluded_providers=["ollama", "groq"])
        messages = [Message(role="user", content="Solve this complex problem")]
        
        provider, model = router.route(messages, required_capabilities=["reasoning"])
        
        # Should select reasoning model
        meta = router.get_model_info(provider, model)
        assert "reasoning" in meta.capabilities
    
    def test_no_models_meet_constraints_raises_error(self):
        """Test that impossible constraints raise an error."""
        router = Router()
        messages = [Message(role="user", content="Hello")]
        
        # Impossible constraint: ultra-low cost AND ultra-high quality
        with pytest.raises(ValueError, match="No models meet the specified requirements"):
            router.route(
                messages,
                max_cost_per_1k_tokens=0.00001,
                required_capabilities=["vision", "tools", "reasoning"]
            )


class TestRouterHelperMethods:
    """Test router helper methods."""
    
    def test_get_model_info(self):
        """Test getting model metadata."""
        router = Router()
        
        meta = router.get_model_info("openai", "gpt-4.1-mini")
        assert meta is not None
        assert meta.provider == "openai"
        assert meta.model == "gpt-4.1-mini"
        assert 0.0 <= meta.quality_score <= 1.0
        assert meta.cost_per_1m_input >= 0.0
        assert meta.avg_latency_ms > 0.0
    
    def test_get_model_info_nonexistent(self):
        """Test getting info for nonexistent model."""
        router = Router()
        
        meta = router.get_model_info("fake", "model")
        assert meta is None
    
    def test_list_models(self):
        """Test listing all models."""
        router = Router()
        
        models = router.list_models()
        assert len(models) > 0
        
        # Check structure
        for provider, model, meta in models:
            assert isinstance(provider, str)
            assert isinstance(model, str)
            assert isinstance(meta, ModelMetadata)
    
    def test_list_models_with_capability_filter(self):
        """Test listing models with capability filter."""
        router = Router()
        
        vision_models = router.list_models(required_capabilities=["vision"])
        
        # All returned models should have vision capability
        for provider, model, meta in vision_models:
            assert "vision" in meta.capabilities
        
        # Should have some vision-capable models
        assert len(vision_models) > 0


class TestRouterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_messages(self):
        """Test routing with empty messages list."""
        router = Router()
        messages = []
        
        # Should still work, complexity should be very low
        complexity = router._analyze_complexity(messages)
        assert complexity == 0.0
        
        # Routing should still work
        provider, model = router.route(messages)
        assert provider is not None
        assert model is not None
    
    def test_very_long_prompt(self):
        """Test routing with very long prompt."""
        router = Router()
        messages = [Message(role="user", content="A" * 100000)]
        
        # Should handle without error
        provider, model = router.route(messages)
        assert provider is not None
        assert model is not None
    
    def test_special_characters_in_prompt(self):
        """Test routing with special characters."""
        router = Router()
        messages = [
            Message(
                role="user",
                content="!@#$%^&*()_+-=[]{}|;':\",./<>?"
            )
        ]
        
        # Should handle without error
        provider, model = router.route(messages)
        assert provider is not None
        assert model is not None
    
    def test_unicode_in_prompt(self):
        """Test routing with unicode characters."""
        router = Router()
        messages = [
            Message(
                role="user",
                content="你好世界 🌍 Привет мир"
            )
        ]
        
        # Should handle without error
        provider, model = router.route(messages)
        assert provider is not None
        assert model is not None


class TestQualityScoresAndLatency:
    """Test quality scores and latency estimates are reasonable."""
    
    def test_all_quality_scores_in_range(self):
        """Test all quality scores are between 0 and 1."""
        router = Router()
        
        for key, meta in router.model_metadata.items():
            assert 0.0 <= meta.quality_score <= 1.0, \
                f"Quality score for {key} out of range: {meta.quality_score}"
    
    def test_all_latencies_positive(self):
        """Test all latency estimates are positive."""
        router = Router()
        
        for key, meta in router.model_metadata.items():
            assert meta.avg_latency_ms > 0, \
                f"Latency for {key} should be positive: {meta.avg_latency_ms}"
    
    def test_reasoning_models_have_higher_quality(self):
        """Test reasoning models generally have higher quality scores."""
        router = Router()
        
        reasoning_scores = []
        non_reasoning_scores = []
        
        for key, meta in router.model_metadata.items():
            if meta.reasoning_model:
                reasoning_scores.append(meta.quality_score)
            else:
                non_reasoning_scores.append(meta.quality_score)
        
        # Average reasoning model quality should be higher
        if reasoning_scores and non_reasoning_scores:
            avg_reasoning = sum(reasoning_scores) / len(reasoning_scores)
            avg_non_reasoning = sum(non_reasoning_scores) / len(non_reasoning_scores)
            assert avg_reasoning >= avg_non_reasoning
    
    def test_local_models_have_low_latency(self):
        """Test local (Ollama) models have lower latency."""
        router = Router()
        
        local_latencies = []
        remote_latencies = []
        
        for key, meta in router.model_metadata.items():
            if meta.provider == "ollama":
                local_latencies.append(meta.avg_latency_ms)
            else:
                remote_latencies.append(meta.avg_latency_ms)
        
        # Average local latency should be lower than remote
        if local_latencies and remote_latencies:
            avg_local = sum(local_latencies) / len(local_latencies)
            avg_remote = sum(remote_latencies) / len(remote_latencies)
            assert avg_local < avg_remote
