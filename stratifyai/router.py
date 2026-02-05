"""Intelligent model router for selecting optimal LLM providers."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re

from .config import MODEL_CATALOG
from .models import Message
from .utils.file_analyzer import FileType


class RoutingStrategy(str, Enum):
    """Routing strategy types."""
    COST = "cost"
    QUALITY = "quality"
    LATENCY = "latency"
    HYBRID = "hybrid"


@dataclass
class ModelMetadata:
    """Metadata for a specific model."""
    provider: str
    model: str
    quality_score: float  # 0.0 - 1.0
    cost_per_1m_input: float  # USD per 1M tokens
    cost_per_1m_output: float  # USD per 1M tokens
    avg_latency_ms: float  # Average response time in milliseconds
    context_window: int  # Maximum context tokens
    capabilities: List[str]  # e.g., ["reasoning", "vision", "tools"]
    reasoning_model: bool = False
    supports_streaming: bool = True


class Router:
    """Intelligent model router for selecting optimal providers."""
    
    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.HYBRID,
        preferred_providers: Optional[List[str]] = None,
        excluded_providers: Optional[List[str]] = None,
    ):
        """
        Initialize router.
        
        Args:
            strategy: Routing strategy to use
            preferred_providers: List of preferred providers (prioritized)
            excluded_providers: List of providers to exclude
        """
        self.strategy = strategy
        self.preferred_providers = preferred_providers or []
        self.excluded_providers = excluded_providers or []
        self._load_model_metadata()
    
    def _load_model_metadata(self) -> None:
        """Load model metadata from MODEL_CATALOG."""
        self.model_metadata: Dict[str, ModelMetadata] = {}
        
        # Quality scores (estimated based on benchmarks)
        # These are rough estimates - should be updated with real benchmark data
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
            
            # OpenRouter (using same as original providers)
            "anthropic/claude-3-5-sonnet": 0.92,
            "openai/gpt-4-turbo": 0.90,
            
            # Ollama (local models)
            "llama3.2": 0.70,
            "mistral": 0.68,
            "codellama": 0.72,
        }
        
        # Average latency (ms) - rough estimates
        latency_estimates = {
            # OpenAI
            "gpt-5": 3500,
            "o3-mini": 8000,
            "gpt-4.5-turbo-20250205": 2500,
            "gpt-4.1-turbo": 2000,
            "gpt-4.1-mini": 800,
            "o1-mini": 5000,
            "o1": 10000,
            
            # Anthropic
            "claude-sonnet-4-5-20250929": 2800,
            "claude-3-5-sonnet-20241022": 2200,
            "claude-3-5-haiku-20241022": 1200,
            
            # Google
            "gemini-2.5-pro": 2000,
            "gemini-2.5-flash": 1000,
            "gemini-2.5-flash-lite": 600,
            
            # DeepSeek
            "deepseek-chat": 1500,
            "deepseek-reasoner": 6000,
            
            # Groq (known for speed)
            "llama-3.1-70b-versatile": 400,
            "llama-3.1-8b-instant": 200,
            "mixtral-8x7b-32768": 350,
            
            # Grok
            "grok-beta": 2500,
            
            # OpenRouter
            "anthropic/claude-3-5-sonnet": 2500,
            "openai/gpt-4-turbo": 2200,
            
            # Ollama (local, very fast)
            "llama3.2": 100,
            "mistral": 120,
            "codellama": 110,
        }
        
        # Build metadata from MODEL_CATALOG
        for provider, models in MODEL_CATALOG.items():
            # Skip if provider is excluded
            if provider in self.excluded_providers:
                continue
                
            for model_name, model_info in models.items():
                key = f"{provider}/{model_name}"
                
                # Extract capabilities
                capabilities = []
                if model_info.get("supports_vision"):
                    capabilities.append("vision")
                if model_info.get("supports_tools"):
                    capabilities.append("tools")
                if model_info.get("reasoning_model"):
                    capabilities.append("reasoning")
                
                self.model_metadata[key] = ModelMetadata(
                    provider=provider,
                    model=model_name,
                    quality_score=quality_scores.get(model_name, 0.75),
                    cost_per_1m_input=model_info.get("cost_input", 0.0),
                    cost_per_1m_output=model_info.get("cost_output", 0.0),
                    avg_latency_ms=latency_estimates.get(model_name, 2000),
                    context_window=model_info.get("context", 8192),
                    capabilities=capabilities,
                    reasoning_model=model_info.get("reasoning_model", False),
                    supports_streaming=True,
                )
    
    def route(
        self,
        messages: List[Message],
        required_capabilities: Optional[List[str]] = None,
        max_cost_per_1k_tokens: Optional[float] = None,
        max_latency_ms: Optional[float] = None,
        min_context_window: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Select the best model for the given request.
        
        Args:
            messages: Conversation messages
            required_capabilities: Required model capabilities (e.g., ["vision", "tools"])
            max_cost_per_1k_tokens: Maximum acceptable cost per 1k tokens
            max_latency_ms: Maximum acceptable latency in milliseconds
            min_context_window: Minimum required context window
        
        Returns:
            Tuple of (provider, model) for the selected model
        """
        # Analyze prompt complexity
        complexity = self._analyze_complexity(messages)
        
        # Filter models by requirements
        candidates = self._filter_candidates(
            required_capabilities,
            max_cost_per_1k_tokens,
            max_latency_ms,
            min_context_window,
        )
        
        if not candidates:
            raise ValueError(
                "No models meet the specified requirements. "
                "Consider relaxing constraints."
            )
        
        # Select model based on strategy
        if self.strategy == RoutingStrategy.COST:
            selected_key = self._select_by_cost(candidates)
        elif self.strategy == RoutingStrategy.QUALITY:
            selected_key = self._select_by_quality(candidates, complexity)
        elif self.strategy == RoutingStrategy.LATENCY:
            selected_key = self._select_by_latency(candidates)
        elif self.strategy == RoutingStrategy.HYBRID:
            selected_key = self._select_hybrid(candidates, complexity)
        else:
            selected_key = list(candidates.keys())[0]
        
        metadata = self.model_metadata[selected_key]
        return metadata.provider, metadata.model
    
    def _analyze_complexity(self, messages: List[Message]) -> float:
        """
        Analyze prompt complexity (0.0 - 1.0).
        
        Higher complexity scores indicate more difficult tasks requiring
        better models.
        
        Args:
            messages: Conversation messages
        
        Returns:
            Complexity score from 0.0 (simple) to 1.0 (complex)
        """
        # Combine all message content
        text = " ".join(msg.content for msg in messages)
        
        # Initialize score
        complexity_score = 0.0
        
        # 1. Check for reasoning keywords (40% weight)
        reasoning_keywords = [
            r'\banalyze\b', r'\bexplain\b', r'\breasoning\b', r'\bproof\b',
            r'\bstep by step\b', r'\bcomplex\b', r'\bcalculate\b',
            r'\bderive\b', r'\bsolve\b', r'\bprove\b', r'\bthink\b',
            r'\bcompare\b', r'\bevaluate\b', r'\bdetailed\b',
        ]
        
        reasoning_matches = sum(
            1 for pattern in reasoning_keywords
            if re.search(pattern, text.lower())
        )
        complexity_score += min(reasoning_matches / len(reasoning_keywords), 1.0) * 0.4
        
        # 2. Length-based complexity (20% weight)
        # Longer prompts often indicate more complex tasks
        text_length = len(text)
        length_score = min(text_length / 2000, 1.0)  # Normalize to 2000 chars
        complexity_score += length_score * 0.2
        
        # 3. Check for code/technical content (20% weight)
        code_indicators = [
            r'```', r'function\s+\w+', r'class\s+\w+', r'def\s+\w+',
            r'import\s+\w+', r'\/\/.*', r'\/\*.*\*\/', r'\bcode\b',
        ]
        
        code_matches = sum(
            1 for pattern in code_indicators
            if re.search(pattern, text, re.IGNORECASE)
        )
        complexity_score += min(code_matches / len(code_indicators), 1.0) * 0.2
        
        # 4. Multi-turn conversation (10% weight)
        # More messages can indicate more complex context
        message_count = len(messages)
        conversation_score = min(message_count / 10, 1.0)
        complexity_score += conversation_score * 0.1
        
        # 5. Mathematical content (10% weight)
        math_indicators = [
            r'\d+\s*[+\-*/]\s*\d+', r'\bequation\b', r'\bformula\b',
            r'\bcalculus\b', r'\balgebra\b', r'\bintegral\b',
        ]
        
        math_matches = sum(
            1 for pattern in math_indicators
            if re.search(pattern, text, re.IGNORECASE)
        )
        complexity_score += min(math_matches / len(math_indicators), 1.0) * 0.1
        
        return min(complexity_score, 1.0)
    
    def _filter_candidates(
        self,
        required_capabilities: Optional[List[str]],
        max_cost_per_1k: Optional[float],
        max_latency_ms: Optional[float],
        min_context_window: Optional[int],
    ) -> Dict[str, ModelMetadata]:
        """Filter models based on requirements."""
        candidates = {}
        
        for key, meta in self.model_metadata.items():
            # Check capabilities
            if required_capabilities:
                if not all(cap in meta.capabilities for cap in required_capabilities):
                    continue
            
            # Check cost constraint
            if max_cost_per_1k:
                avg_cost_per_1k = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 1000
                if avg_cost_per_1k > max_cost_per_1k:
                    continue
            
            # Check latency constraint
            if max_latency_ms and meta.avg_latency_ms > max_latency_ms:
                continue
            
            # Check context window constraint
            if min_context_window and meta.context_window < min_context_window:
                continue
            
            candidates[key] = meta
        
        # Prioritize preferred providers
        if self.preferred_providers:
            prioritized = {}
            for key, meta in candidates.items():
                if meta.provider in self.preferred_providers:
                    prioritized[key] = meta
            if prioritized:
                return prioritized
        
        return candidates
    
    def _select_by_cost(self, candidates: Dict[str, ModelMetadata]) -> str:
        """Select cheapest model."""
        def cost_score(meta: ModelMetadata) -> float:
            # Average cost per 1M tokens (input + output weighted equally)
            return (meta.cost_per_1m_input + meta.cost_per_1m_output) / 2
        
        return min(candidates.keys(), key=lambda k: cost_score(candidates[k]))
    
    def _select_by_quality(
        self,
        candidates: Dict[str, ModelMetadata],
        complexity: float
    ) -> str:
        """
        Select highest quality model.
        
        For high complexity tasks, prioritize models with reasoning capabilities.
        """
        def quality_score(meta: ModelMetadata) -> float:
            base_score = meta.quality_score
            
            # Boost reasoning models for complex tasks
            if complexity > 0.6 and meta.reasoning_model:
                base_score += 0.05
            
            return base_score
        
        return max(candidates.keys(), key=lambda k: quality_score(candidates[k]))
    
    def _select_by_latency(self, candidates: Dict[str, ModelMetadata]) -> str:
        """Select fastest model."""
        return min(candidates.keys(), key=lambda k: candidates[k].avg_latency_ms)
    
    def _select_hybrid(
        self,
        candidates: Dict[str, ModelMetadata],
        complexity: float
    ) -> str:
        """
        Hybrid selection balancing cost, quality, and latency.
        
        Adjusts weights based on task complexity:
        - Low complexity: Prioritize cost (60%) and speed (30%), quality (10%)
        - High complexity: Prioritize quality (60%) and cost (30%), speed (10%)
        """
        scores = {}
        
        # Adjust weights based on complexity
        quality_weight = 0.1 + (complexity * 0.5)  # 0.1 to 0.6
        cost_weight = 0.6 - (complexity * 0.3)     # 0.6 to 0.3
        latency_weight = 0.3 - (complexity * 0.2)  # 0.3 to 0.1
        
        for key, meta in candidates.items():
            # Quality score (0-1, higher is better)
            quality_score = meta.quality_score
            
            # Cost score (0-1, lower cost is better)
            # Normalize to typical range: $0.001 to $0.050 per 1k tokens
            avg_cost_per_1k = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 1000
            cost_score = max(0, 1 - (avg_cost_per_1k / 0.050))
            
            # Latency score (0-1, lower latency is better)
            # Normalize to typical range: 100ms to 10000ms
            latency_score = max(0, 1 - (meta.avg_latency_ms / 10000))
            
            # Calculate weighted score
            scores[key] = (
                quality_weight * quality_score +
                cost_weight * cost_score +
                latency_weight * latency_score
            )
        
        return max(scores, key=scores.get)
    
    def get_model_info(self, provider: str, model: str) -> Optional[ModelMetadata]:
        """Get metadata for a specific model."""
        key = f"{provider}/{model}"
        return self.model_metadata.get(key)
    
    def route_for_extraction(
        self,
        file_type: FileType,
        extraction_mode: str = "schema",
        max_cost_per_1k_tokens: Optional[float] = None,
    ) -> Tuple[str, str]:
        """
        Select the best model for file extraction tasks.
        
        Prioritizes quality over cost/latency for extraction tasks,
        with task-specific optimizations.
        
        Args:
            file_type: Type of file being extracted
            extraction_mode: Mode of extraction ("schema", "errors", "structure", "summary")
            max_cost_per_1k_tokens: Optional cost constraint
        
        Returns:
            Tuple of (provider, model) optimized for extraction
        """
        # Define extraction-specific quality weights
        if extraction_mode == "schema":
            quality_weight = 0.90
            cost_weight = 0.10
        elif extraction_mode == "errors":
            quality_weight = 0.80
            cost_weight = 0.20
        elif extraction_mode == "structure":
            quality_weight = 0.85
            cost_weight = 0.15
        else:  # summary
            quality_weight = 0.70
            cost_weight = 0.30
        
        # Filter candidates
        candidates = {}
        for key, meta in self.model_metadata.items():
            # Apply cost constraint if specified
            if max_cost_per_1k_tokens:
                avg_cost_per_1k = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 1000
                if avg_cost_per_1k > max_cost_per_1k_tokens:
                    continue
            
            candidates[key] = meta
        
        if not candidates:
            raise ValueError(
                "No models meet cost constraints. "
                "Consider increasing max_cost_per_1k_tokens."
            )
        
        # Score candidates with extraction-focused weights
        scores = {}
        for key, meta in candidates.items():
            # Quality score (0-1, higher is better)
            quality_score = meta.quality_score
            
            # Boost for reasoning models on error extraction
            if extraction_mode == "errors" and meta.reasoning_model:
                quality_score += 0.05
            
            # Cost score (0-1, lower cost is better)
            avg_cost_per_1k = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 1000
            cost_score = max(0, 1 - (avg_cost_per_1k / 0.050))
            
            # Calculate weighted score (no latency for extraction)
            scores[key] = (
                quality_weight * quality_score +
                cost_weight * cost_score
            )
        
        # Select highest scoring model
        best_key = max(scores, key=scores.get)
        metadata = self.model_metadata[best_key]
        return metadata.provider, metadata.model
    
    def get_fallback_chain(
        self,
        messages: List[Message],
        count: int = 3,
        required_capabilities: Optional[List[str]] = None,
        max_cost_per_1k_tokens: Optional[float] = None,
        max_latency_ms: Optional[float] = None,
        min_context_window: Optional[int] = None,
        exclude_models: Optional[List[str]] = None,
    ) -> List[Tuple[str, str]]:
        """
        Get a ranked list of fallback models for resilient routing.
        
        Returns models ranked by the current strategy, allowing automatic
        fallback if the primary model fails.
        
        Args:
            messages: Conversation messages (used for complexity analysis)
            count: Number of fallback models to return (default: 3)
            required_capabilities: Required model capabilities
            max_cost_per_1k_tokens: Maximum acceptable cost
            max_latency_ms: Maximum acceptable latency
            min_context_window: Minimum required context window
            exclude_models: Models to exclude from results
        
        Returns:
            List of (provider, model) tuples ranked by strategy
        
        Example:
            >>> router = Router(strategy=RoutingStrategy.HYBRID)
            >>> fallbacks = router.get_fallback_chain(messages, count=3)
            >>> # Returns: [("openai", "gpt-4o"), ("anthropic", "claude-3-5-sonnet"), ...]
        """
        # Analyze complexity for scoring
        complexity = self._analyze_complexity(messages)
        
        # Filter candidates
        candidates = self._filter_candidates(
            required_capabilities,
            max_cost_per_1k_tokens,
            max_latency_ms,
            min_context_window,
        )
        
        # Exclude specified models
        if exclude_models:
            candidates = {
                k: v for k, v in candidates.items()
                if v.model not in exclude_models
            }
        
        if not candidates:
            return []
        
        # Score all candidates based on strategy
        scores = self._score_candidates(candidates, complexity)
        
        # Sort by score (descending) and return top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        result = []
        for key, _ in ranked[:count]:
            meta = self.model_metadata[key]
            result.append((meta.provider, meta.model))
        
        return result
    
    def _score_candidates(
        self,
        candidates: Dict[str, ModelMetadata],
        complexity: float,
    ) -> Dict[str, float]:
        """
        Score all candidates based on current routing strategy.
        
        Args:
            candidates: Filtered model candidates
            complexity: Task complexity score (0.0 - 1.0)
        
        Returns:
            Dictionary mapping model keys to scores
        """
        scores = {}
        
        for key, meta in candidates.items():
            if self.strategy == RoutingStrategy.COST:
                # Lower cost = higher score
                avg_cost = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 2
                scores[key] = max(0, 1 - (avg_cost / 100))  # Normalize to $100/1M
                
            elif self.strategy == RoutingStrategy.QUALITY:
                scores[key] = meta.quality_score
                if complexity > 0.6 and meta.reasoning_model:
                    scores[key] += 0.05
                    
            elif self.strategy == RoutingStrategy.LATENCY:
                # Lower latency = higher score
                scores[key] = max(0, 1 - (meta.avg_latency_ms / 10000))
                
            else:  # HYBRID
                # Dynamic weights based on complexity
                quality_weight = 0.1 + (complexity * 0.5)
                cost_weight = 0.6 - (complexity * 0.3)
                latency_weight = 0.3 - (complexity * 0.2)
                
                quality_score = meta.quality_score
                avg_cost = (meta.cost_per_1m_input + meta.cost_per_1m_output) / 1000
                cost_score = max(0, 1 - (avg_cost / 0.050))
                latency_score = max(0, 1 - (meta.avg_latency_ms / 10000))
                
                scores[key] = (
                    quality_weight * quality_score +
                    cost_weight * cost_score +
                    latency_weight * latency_score
                )
        
        return scores
    
    def list_models(
        self,
        required_capabilities: Optional[List[str]] = None,
    ) -> List[Tuple[str, str, ModelMetadata]]:
        """
        List all available models with their metadata.
        
        Args:
            required_capabilities: Filter by required capabilities
        
        Returns:
            List of (provider, model, metadata) tuples
        """
        results = []
        
        for key, meta in self.model_metadata.items():
            # Check capabilities
            if required_capabilities:
                if not all(cap in meta.capabilities for cap in required_capabilities):
                    continue
            
            results.append((meta.provider, meta.model, meta))
        
        return results
