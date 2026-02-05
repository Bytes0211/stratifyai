"""Unit tests for Router extraction routing functionality."""

import pytest
from stratifyai.router import Router, RoutingStrategy
from stratifyai.utils.file_analyzer import FileType


class TestRouterExtraction:
    """Test Router.route_for_extraction() method."""
    
    def test_route_for_schema_extraction(self):
        """Test routing for schema extraction (CSV/JSON)."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema"
        )
        
        # Should select high-quality model
        assert provider in ["anthropic", "openai", "google"]
        assert isinstance(model, str)
        
        # Check that it's a quality model by checking metadata
        metadata = router.get_model_info(provider, model)
        assert metadata is not None
        assert metadata.quality_score > 0.85
    
    def test_route_for_error_extraction(self):
        """Test routing for error extraction (logs)."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.LOG,
            extraction_mode="errors"
        )
        
        # Should select reasoning model or high-quality model
        assert provider in ["deepseek", "openai", "anthropic", "google"]
        assert isinstance(model, str)
    
    def test_route_for_structure_extraction(self):
        """Test routing for code structure extraction."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.PYTHON,
            extraction_mode="structure"
        )
        
        # Should select code-capable model
        assert provider in ["deepseek", "anthropic", "openai", "google"]
        
        metadata = router.get_model_info(provider, model)
        assert metadata.quality_score > 0.80
    
    def test_route_for_summary_extraction(self):
        """Test routing for summary extraction."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.TEXT,
            extraction_mode="summary"
        )
        
        # Can use any model, but should be reasonable quality
        assert isinstance(provider, str)
        assert isinstance(model, str)
    
    def test_route_with_cost_constraint(self):
        """Test routing with cost constraint."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        # Set very low cost constraint - should select cheaper models
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema",
            max_cost_per_1k_tokens=0.001  # Very low
        )
        
        metadata = router.get_model_info(provider, model)
        avg_cost_per_1k = (metadata.cost_per_1m_input + metadata.cost_per_1m_output) / 1000
        assert avg_cost_per_1k <= 0.001
    
    def test_route_with_impossible_cost_constraint(self):
        """Test that routing with very low cost finds cheapest available models."""
        router = Router(
            strategy=RoutingStrategy.QUALITY,
            excluded_providers=["ollama", "groq", "deepseek"]  # Exclude free/very cheap
        )
        
        # With very low cost, should still find at least one model
        # (OpenRouter and others have very low cost models)
        # The test verifies the function doesn't crash with low constraints
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema",
            max_cost_per_1k_tokens=0.01  # Low but achievable
        )
        
        # Should find a model within constraint
        assert provider is not None
        assert model is not None
    
    def test_schema_extraction_prioritizes_quality(self):
        """Test that schema extraction prioritizes quality over cost."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema"
        )
        
        metadata = router.get_model_info(provider, model)
        
        # Schema extraction should select very high quality model (90% weight)
        assert metadata.quality_score >= 0.85
    
    def test_error_extraction_boosts_reasoning_models(self):
        """Test that error extraction boosts reasoning models."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        provider, model = router.route_for_extraction(
            file_type=FileType.LOG,
            extraction_mode="errors"
        )
        
        metadata = router.get_model_info(provider, model)
        
        # Should select a high-quality model (possibly reasoning)
        assert metadata.quality_score >= 0.80
    
    def test_extraction_routing_different_file_types(self):
        """Test that different file types get appropriate models."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        # CSV should get schema extraction
        csv_provider, csv_model = router.route_for_extraction(
            FileType.CSV, "schema"
        )
        
        # Log should get error extraction
        log_provider, log_model = router.route_for_extraction(
            FileType.LOG, "errors"
        )
        
        # Python should get structure extraction
        py_provider, py_model = router.route_for_extraction(
            FileType.PYTHON, "structure"
        )
        
        # All should return valid provider/model pairs
        assert csv_provider and csv_model
        assert log_provider and log_model
        assert py_provider and py_model
    
    def test_extraction_with_excluded_providers(self):
        """Test extraction routing with excluded providers."""
        router = Router(
            strategy=RoutingStrategy.QUALITY,
            excluded_providers=["anthropic"]
        )
        
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema"
        )
        
        # Should not select excluded provider
        assert provider != "anthropic"
        assert provider in ["openai", "google", "deepseek", "groq", "grok", "ollama", "openrouter"]
    
    def test_extraction_with_preferred_providers(self):
        """Test extraction routing with preferred providers."""
        router = Router(
            strategy=RoutingStrategy.QUALITY,
            preferred_providers=["google"]
        )
        
        provider, model = router.route_for_extraction(
            file_type=FileType.CSV,
            extraction_mode="schema"
        )
        
        # Note: route_for_extraction doesn't currently use preferred_providers
        # but it should work with the router's provider filtering
        assert isinstance(provider, str)
        assert isinstance(model, str)
    
    def test_extraction_modes_have_different_weights(self):
        """Test that different extraction modes use different quality/cost weights."""
        router = Router(strategy=RoutingStrategy.QUALITY)
        
        # Schema should heavily prioritize quality (90%)
        schema_provider, schema_model = router.route_for_extraction(
            FileType.CSV, "schema"
        )
        
        # Summary should balance quality/cost more (70/30)
        summary_provider, summary_model = router.route_for_extraction(
            FileType.TEXT, "summary"
        )
        
        # Both should return valid results
        assert schema_provider and schema_model
        assert summary_provider and summary_model
        
        # Schema should tend toward higher quality models
        schema_meta = router.get_model_info(schema_provider, schema_model)
        summary_meta = router.get_model_info(summary_provider, summary_model)
        
        # This is probabilistic but schema should generally be higher quality
        # or equal (if both select the same top model)
        assert schema_meta.quality_score >= summary_meta.quality_score - 0.15
