"""Unit tests for model selector functionality."""

import pytest
from pathlib import Path
from stratifyai.utils.model_selector import (
    ModelSelector,
    ExtractionMode,
    ModelRecommendation,
    select_model_for_file,
)
from stratifyai.utils.file_analyzer import FileType


class TestModelSelector:
    """Test ModelSelector class."""
    
    def test_init(self):
        """Test selector initialization."""
        selector = ModelSelector()
        
        # Check that model lists are populated
        assert len(selector.schema_extraction_models) > 0
        assert len(selector.error_extraction_models) > 0
        assert len(selector.code_extraction_models) > 0
        assert len(selector.summary_models) > 0
    
    def test_select_for_csv_file(self, tmp_path):
        """Test model selection for CSV files."""
        selector = ModelSelector()
        
        # Create temporary CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n1,2\n")
        
        recommendation = selector.select_for_file(csv_file)
        
        # Should select high-quality model for schema extraction
        assert recommendation.provider in ["anthropic", "openai", "google"]
        assert recommendation.model in [
            "claude-3-5-sonnet-20241022",
            "gpt-4.5-turbo-20250205",
            "claude-sonnet-4-5-20250929",
            "gemini-2.5-pro",
        ]
        assert "schema" in recommendation.reasoning.lower()
        assert recommendation.quality_score > 0.8
    
    def test_select_for_json_file(self, tmp_path):
        """Test model selection for JSON files."""
        selector = ModelSelector()
        
        # Create temporary JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        
        recommendation = selector.select_for_file(json_file)
        
        # Should select high-quality model for schema extraction
        assert recommendation.provider in ["anthropic", "openai", "google"]
        assert "schema" in recommendation.reasoning.lower()
    
    def test_select_for_log_file(self, tmp_path):
        """Test model selection for log files."""
        selector = ModelSelector()
        
        # Create temporary log file
        log_file = tmp_path / "app.log"
        log_file.write_text("ERROR: Something went wrong\n")
        
        recommendation = selector.select_for_file(log_file)
        
        # Should select reasoning model for error extraction
        assert recommendation.provider in ["deepseek", "openai", "anthropic"]
        assert "error" in recommendation.reasoning.lower()
    
    def test_select_for_python_file(self, tmp_path):
        """Test model selection for Python files."""
        selector = ModelSelector()
        
        # Create temporary Python file
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo():\n    pass\n")
        
        recommendation = selector.select_for_file(py_file)
        
        # Should select code-optimized model
        assert recommendation.provider in ["deepseek", "anthropic", "openai", "google"]
        assert "structure" in recommendation.reasoning.lower()
    
    def test_select_with_excluded_providers(self, tmp_path):
        """Test model selection with excluded providers."""
        selector = ModelSelector()
        
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n1,2\n")
        
        # Exclude anthropic (normally first choice for CSV)
        recommendation = selector.select_for_file(
            csv_file,
            excluded_providers=["anthropic"]
        )
        
        # Should not select anthropic
        assert recommendation.provider != "anthropic"
        assert recommendation.provider in ["openai", "google"]
    
    def test_select_for_extraction_mode_schema(self):
        """Test selection for schema extraction mode."""
        selector = ModelSelector()
        
        recommendation = selector.select_for_extraction_mode(
            FileType.CSV,
            ExtractionMode.SCHEMA
        )
        
        # Should prioritize quality for schema extraction
        assert recommendation.quality_score >= 0.90
        assert recommendation.provider in ["anthropic", "openai", "google"]
    
    def test_select_for_extraction_mode_errors(self):
        """Test selection for error extraction mode."""
        selector = ModelSelector()
        
        recommendation = selector.select_for_extraction_mode(
            FileType.LOG,
            ExtractionMode.ERRORS
        )
        
        # Should select reasoning model
        assert recommendation.provider in ["deepseek", "openai", "anthropic"]
    
    def test_select_for_extraction_mode_structure(self):
        """Test selection for structure extraction mode."""
        selector = ModelSelector()
        
        recommendation = selector.select_for_extraction_mode(
            FileType.PYTHON,
            ExtractionMode.STRUCTURE
        )
        
        # Should select code-optimized model
        assert recommendation.provider in ["deepseek", "anthropic", "openai", "google"]
    
    def test_select_for_extraction_mode_summary(self):
        """Test selection for summary extraction mode."""
        selector = ModelSelector()
        
        recommendation = selector.select_for_extraction_mode(
            FileType.TEXT,
            ExtractionMode.SUMMARY
        )
        
        # Should select fast/cost-effective model
        assert recommendation.provider in ["google", "groq", "anthropic", "openai"]
    
    def test_infer_extraction_mode_csv(self, tmp_path):
        """Test extraction mode inference for CSV."""
        selector = ModelSelector()
        csv_file = tmp_path / "data.csv"
        csv_file.touch()
        
        mode = selector._infer_extraction_mode(FileType.CSV, csv_file)
        assert mode == ExtractionMode.SCHEMA
    
    def test_infer_extraction_mode_json(self, tmp_path):
        """Test extraction mode inference for JSON."""
        selector = ModelSelector()
        json_file = tmp_path / "data.json"
        json_file.touch()
        
        mode = selector._infer_extraction_mode(FileType.JSON, json_file)
        assert mode == ExtractionMode.SCHEMA
    
    def test_infer_extraction_mode_log(self, tmp_path):
        """Test extraction mode inference for log files."""
        selector = ModelSelector()
        log_file = tmp_path / "app.log"
        log_file.touch()
        
        mode = selector._infer_extraction_mode(FileType.LOG, log_file)
        assert mode == ExtractionMode.ERRORS
    
    def test_infer_extraction_mode_python(self, tmp_path):
        """Test extraction mode inference for Python."""
        selector = ModelSelector()
        py_file = tmp_path / "script.py"
        py_file.touch()
        
        mode = selector._infer_extraction_mode(FileType.PYTHON, py_file)
        assert mode == ExtractionMode.STRUCTURE
    
    def test_fallback_when_all_providers_excluded(self, tmp_path):
        """Test that selection fails gracefully when all providers excluded."""
        selector = ModelSelector()
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n")
        
        all_providers = ["anthropic", "openai", "google", "deepseek", "groq", "grok", "ollama", "openrouter"]
        
        with pytest.raises(ValueError, match="No available models"):
            selector.select_for_file(csv_file, excluded_providers=all_providers)
    
    def test_quality_scores(self):
        """Test quality score retrieval."""
        selector = ModelSelector()
        
        # Test known models
        assert selector._get_quality_score("anthropic", "claude-3-5-sonnet-20241022") == 0.92
        assert selector._get_quality_score("openai", "gpt-4.5-turbo-20250205") == 0.93
        assert selector._get_quality_score("deepseek", "deepseek-reasoner") == 0.90
        
        # Test unknown model (should return default)
        assert selector._get_quality_score("unknown", "unknown-model") == 0.75
    
    def test_cost_estimates(self):
        """Test cost estimate retrieval."""
        selector = ModelSelector()
        
        # Test known models
        assert selector._get_estimated_cost("anthropic", "claude-3-5-sonnet-20241022") > 0
        assert selector._get_estimated_cost("google", "gemini-2.5-flash") < 1.0
        
        # Test unknown model (should return default)
        assert selector._get_estimated_cost("unknown", "unknown-model") == 1.0


class TestSelectModelForFile:
    """Test convenience function."""
    
    def test_select_model_for_csv(self, tmp_path):
        """Test convenience function for CSV."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n1,2\n")
        
        provider, model, reasoning = select_model_for_file(csv_file)
        
        assert provider in ["anthropic", "openai", "google"]
        assert isinstance(model, str)
        assert isinstance(reasoning, str)
        assert "schema" in reasoning.lower()
    
    def test_select_model_with_mode(self, tmp_path):
        """Test convenience function with explicit mode."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Some text content")
        
        provider, model, reasoning = select_model_for_file(
            txt_file,
            extraction_mode=ExtractionMode.SUMMARY
        )
        
        assert provider in ["google", "groq", "anthropic", "openai"]
        assert "summary" in reasoning.lower()
    
    def test_select_model_with_exclusions(self, tmp_path):
        """Test convenience function with excluded providers."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n")
        
        provider, model, reasoning = select_model_for_file(
            csv_file,
            excluded_providers=["anthropic"]
        )
        
        assert provider != "anthropic"
