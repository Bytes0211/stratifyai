"""Intelligent model selection for file extraction tasks.

This module provides automatic model selection based on file type,
extraction mode, and task requirements, optimizing for quality in
structured data extraction scenarios.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, List, Dict
from pathlib import Path

from .file_analyzer import FileType


class ExtractionMode(Enum):
    """Types of extraction tasks."""
    SCHEMA = "schema"          # CSV/JSON schema extraction
    ERRORS = "errors"          # Log file error extraction
    SUMMARY = "summary"        # General summarization
    STRUCTURE = "structure"    # Code structure extraction


@dataclass
class ModelRecommendation:
    """Model recommendation with reasoning."""
    provider: str
    model: str
    reasoning: str
    quality_score: float
    estimated_cost_per_1m: float


class ModelSelector:
    """Select optimal models for file extraction tasks."""
    
    def __init__(self):
        """Initialize model selector with provider preferences."""
        # Quality-focused models for schema extraction (ordered by preference)
        self.schema_extraction_models = [
            ("anthropic", "claude-3-5-sonnet-20241022", "Best structured output quality"),
            ("openai", "gpt-4.5-turbo-20250205", "Excellent for data analysis"),
            ("anthropic", "claude-sonnet-4-5-20250929", "High quality, latest model"),
            ("google", "gemini-2.5-pro", "Strong structured reasoning"),
        ]
        
        # Reasoning models for error/log analysis
        self.error_extraction_models = [
            ("deepseek", "deepseek-reasoner", "Excellent reasoning for error analysis"),
            ("openai", "o1-mini", "Fast reasoning model"),
            ("openai", "o3-mini", "Advanced reasoning"),
            ("anthropic", "claude-3-5-sonnet-20241022", "Reliable error detection"),
        ]
        
        # Code-optimized models for structure extraction
        self.code_extraction_models = [
            ("deepseek", "deepseek-chat", "Optimized for code understanding"),
            ("anthropic", "claude-3-5-sonnet-20241022", "Strong code analysis"),
            ("openai", "gpt-4.5-turbo-20250205", "Excellent code comprehension"),
            ("google", "gemini-2.5-pro", "Good at code structure"),
        ]
        
        # Fast models for general summarization
        self.summary_models = [
            ("google", "gemini-2.5-flash", "Fast and cost-effective"),
            ("groq", "llama-3.1-70b-versatile", "Very fast inference"),
            ("anthropic", "claude-3-5-haiku-20241022", "Quick, quality summaries"),
            ("openai", "gpt-4.1-mini", "Balanced speed/quality"),
        ]
    
    def select_for_file(
        self,
        file_path: Path,
        extraction_mode: Optional[ExtractionMode] = None,
        excluded_providers: Optional[List[str]] = None,
    ) -> ModelRecommendation:
        """Select optimal model for file extraction.
        
        Args:
            file_path: Path to file being analyzed
            extraction_mode: Specific extraction mode (auto-detected if None)
            excluded_providers: Providers to exclude from selection
            
        Returns:
            ModelRecommendation with selected provider/model and reasoning
            
        Examples:
            >>> selector = ModelSelector()
            >>> rec = selector.select_for_file(Path("data.csv"))
            >>> print(f"{rec.provider}/{rec.model}: {rec.reasoning}")
        """
        from .file_analyzer import detect_file_type
        
        excluded = excluded_providers or []
        file_type = detect_file_type(file_path)
        
        # Auto-detect extraction mode if not specified
        if extraction_mode is None:
            extraction_mode = self._infer_extraction_mode(file_type, file_path)
        
        # Select model list based on extraction mode
        if extraction_mode == ExtractionMode.SCHEMA:
            candidates = self.schema_extraction_models
        elif extraction_mode == ExtractionMode.ERRORS:
            candidates = self.error_extraction_models
        elif extraction_mode == ExtractionMode.STRUCTURE:
            candidates = self.code_extraction_models
        elif extraction_mode == ExtractionMode.SUMMARY:
            candidates = self.summary_models
        else:
            # Fallback to schema extraction models (highest quality)
            candidates = self.schema_extraction_models
        
        # Filter out excluded providers
        available_candidates = [
            (provider, model, reason)
            for provider, model, reason in candidates
            if provider not in excluded
        ]
        
        if not available_candidates:
            # Fallback to any available provider
            all_models = (
                self.schema_extraction_models +
                self.error_extraction_models +
                self.code_extraction_models +
                self.summary_models
            )
            available_candidates = [
                (provider, model, reason)
                for provider, model, reason in all_models
                if provider not in excluded
            ]
        
        if not available_candidates:
            raise ValueError(
                "No available models after filtering excluded providers. "
                f"Excluded: {excluded}"
            )
        
        # Select first available (highest priority)
        provider, model, reasoning = available_candidates[0]
        
        # Get quality score and cost estimates
        quality_score = self._get_quality_score(provider, model)
        estimated_cost = self._get_estimated_cost(provider, model)
        
        # Enhance reasoning with file type
        full_reasoning = f"{reasoning} (for {file_type.value} {extraction_mode.value})"
        
        return ModelRecommendation(
            provider=provider,
            model=model,
            reasoning=full_reasoning,
            quality_score=quality_score,
            estimated_cost_per_1m=estimated_cost,
        )
    
    def select_for_extraction_mode(
        self,
        file_type: FileType,
        extraction_mode: ExtractionMode,
        excluded_providers: Optional[List[str]] = None,
    ) -> ModelRecommendation:
        """Select model based on file type and extraction mode.
        
        Args:
            file_type: Detected file type
            extraction_mode: Type of extraction task
            excluded_providers: Providers to exclude
            
        Returns:
            ModelRecommendation with selected provider/model
        """
        excluded = excluded_providers or []
        
        # Select candidates based on mode
        if extraction_mode == ExtractionMode.SCHEMA:
            candidates = self.schema_extraction_models
        elif extraction_mode == ExtractionMode.ERRORS:
            candidates = self.error_extraction_models
        elif extraction_mode == ExtractionMode.STRUCTURE:
            candidates = self.code_extraction_models
        else:
            candidates = self.summary_models
        
        # Filter and select
        available = [
            (p, m, r) for p, m, r in candidates
            if p not in excluded
        ]
        
        if not available:
            raise ValueError("No available models after filtering")
        
        provider, model, reasoning = available[0]
        
        return ModelRecommendation(
            provider=provider,
            model=model,
            reasoning=f"{reasoning} (for {file_type.value} {extraction_mode.value})",
            quality_score=self._get_quality_score(provider, model),
            estimated_cost_per_1m=self._get_estimated_cost(provider, model),
        )
    
    def _infer_extraction_mode(self, file_type: FileType, file_path: Path) -> ExtractionMode:
        """Infer extraction mode from file type and name.
        
        Args:
            file_type: Detected file type
            file_path: Path to file
            
        Returns:
            Inferred ExtractionMode
        """
        # Map file types to extraction modes
        if file_type == FileType.CSV:
            return ExtractionMode.SCHEMA
        elif file_type == FileType.JSON:
            return ExtractionMode.SCHEMA
        elif file_type == FileType.LOG:
            return ExtractionMode.ERRORS
        elif file_type in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.JAVA, FileType.GO]:
            return ExtractionMode.STRUCTURE
        else:
            # Check filename for hints
            filename_lower = file_path.name.lower()
            if 'log' in filename_lower or 'error' in filename_lower:
                return ExtractionMode.ERRORS
            else:
                return ExtractionMode.SUMMARY
    
    def _get_quality_score(self, provider: str, model: str) -> float:
        """Get quality score for a model.
        
        These are estimated scores based on benchmarks.
        Should match Router's quality_scores.
        """
        quality_scores = {
            # OpenAI
            "gpt-5": 0.98,
            "o3-mini": 0.95,
            "gpt-4.5-turbo-20250205": 0.93,
            "gpt-4.1-turbo": 0.90,
            "gpt-4.1-mini": 0.82,
            "o1-mini": 0.88,
            "o1": 0.96,
            
            # Anthropic
            "claude-sonnet-4-5-20250929": 0.94,
            "claude-3-5-sonnet-20241022": 0.92,
            "claude-3-5-haiku-20241022": 0.80,
            
            # Google
            "gemini-2.5-pro": 0.91,
            "gemini-2.5-flash": 0.85,
            "gemini-2.5-flash-lite": 0.78,
            
            # DeepSeek
            "deepseek-chat": 0.85,
            "deepseek-reasoner": 0.90,
            
            # Groq
            "llama-3.1-70b-versatile": 0.83,
            "llama-3.1-8b-instant": 0.75,
            "mixtral-8x7b-32768": 0.80,
            
            # Grok
            "grok-beta": 0.87,
        }
        
        return quality_scores.get(model, 0.75)
    
    def _get_estimated_cost(self, provider: str, model: str) -> float:
        """Get estimated cost per 1M tokens (average of input/output).
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            Estimated cost per 1M tokens in USD
        """
        # Rough estimates - should match MODEL_CATALOG
        cost_estimates = {
            "gpt-4.5-turbo-20250205": 2.50,
            "claude-3-5-sonnet-20241022": 3.00,
            "claude-sonnet-4-5-20250929": 3.00,
            "gemini-2.5-pro": 1.25,
            "gemini-2.5-flash": 0.15,
            "deepseek-chat": 0.14,
            "deepseek-reasoner": 0.55,
            "o1-mini": 3.00,
            "o3-mini": 1.10,
            "llama-3.1-70b-versatile": 0.08,
            "claude-3-5-haiku-20241022": 1.00,
            "gpt-4.1-mini": 0.15,
        }
        
        return cost_estimates.get(model, 1.0)


def select_model_for_file(
    file_path: Path,
    extraction_mode: Optional[ExtractionMode] = None,
    excluded_providers: Optional[List[str]] = None,
) -> Tuple[str, str, str]:
    """Convenience function to select model for file.
    
    Args:
        file_path: Path to file
        extraction_mode: Optional extraction mode (auto-detected if None)
        excluded_providers: Providers to exclude
        
    Returns:
        Tuple of (provider, model, reasoning)
        
    Examples:
        >>> provider, model, reason = select_model_for_file(Path("data.csv"))
        >>> print(f"Selected {provider}/{model}: {reason}")
    """
    selector = ModelSelector()
    recommendation = selector.select_for_file(file_path, extraction_mode, excluded_providers)
    return recommendation.provider, recommendation.model, recommendation.reasoning
