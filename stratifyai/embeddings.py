"""Embedding generation for RAG and semantic search.

This module provides abstraction for generating embeddings from text using
various provider APIs (OpenAI, Cohere, etc.).
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import os
from openai import AsyncOpenAI

from .exceptions import ProviderAPIError, AuthenticationError


@dataclass
class EmbeddingResult:
    """Result of an embedding generation request.
    
    Attributes:
        embeddings: List of embedding vectors (each is List[float])
        model: Name of the embedding model used
        total_tokens: Total tokens processed
        cost: Cost of the embedding request in USD
    """
    embeddings: List[List[float]]
    model: str
    total_tokens: int
    cost: float


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.
    
    All embedding provider implementations must inherit from this class
    and implement the generate_embeddings method.
    """
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            model: Optional model name override
            
        Returns:
            EmbeddingResult with embeddings and metadata
            
        Raises:
            ProviderAPIError: If the API request fails
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self, model: str) -> int:
        """Get the dimensionality of embeddings for a given model.
        
        Args:
            model: Model name
            
        Returns:
            Embedding dimension (e.g., 1536 for text-embedding-3-small)
        """
        pass
    
    def generate_embeddings_sync(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """Synchronous wrapper for generate_embeddings."""
        return asyncio.run(self.generate_embeddings(texts, model))


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider implementation.
    
    Supports:
    - text-embedding-3-small (1536 dimensions)
    - text-embedding-3-large (3072 dimensions)
    - text-embedding-ada-002 (1536 dimensions, legacy)
    """
    
    # Embedding costs per 1M tokens (as of Feb 2026)
    EMBEDDING_COSTS = {
        "text-embedding-3-small": 0.020 / 1_000_000,  # $0.020 per 1M tokens
        "text-embedding-3-large": 0.130 / 1_000_000,  # $0.130 per 1M tokens
        "text-embedding-ada-002": 0.100 / 1_000_000,  # $0.100 per 1M tokens (legacy)
    }
    
    # Embedding dimensions by model
    EMBEDDING_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    # Default model
    DEFAULT_MODEL = "text-embedding-3-small"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            
        Raises:
            AuthenticationError: If no API key is provided or found
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> EmbeddingResult:
        """Generate embeddings for a list of texts using OpenAI.
        
        Args:
            texts: List of text strings to embed
            model: Model name (default: text-embedding-3-small)
            
        Returns:
            EmbeddingResult with embeddings and metadata
            
        Raises:
            ProviderAPIError: If the API request fails
            AuthenticationError: If authentication fails
        """
        model = model or self.DEFAULT_MODEL
        
        if model not in self.EMBEDDING_COSTS:
            raise ValueError(
                f"Unknown OpenAI embedding model: {model}. "
                f"Supported models: {list(self.EMBEDDING_COSTS.keys())}"
            )
        
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=model,
                total_tokens=0,
                cost=0.0
            )
        
        try:
            # Call OpenAI API
            response = await self.client.embeddings.create(
                input=texts,
                model=model
            )
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            
            # Calculate cost
            total_tokens = response.usage.total_tokens
            cost = total_tokens * self.EMBEDDING_COSTS[model]
            
            return EmbeddingResult(
                embeddings=embeddings,
                model=model,
                total_tokens=total_tokens,
                cost=cost
            )
            
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                raise AuthenticationError(f"OpenAI authentication failed: {error_msg}")
            else:
                raise ProviderAPIError(f"OpenAI embedding request failed: {error_msg}")
    
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embedding for a single text string.
        
        Convenience method for single text embedding.
        
        Args:
            text: Text string to embed
            model: Model name (default: text-embedding-3-small)
            
        Returns:
            Embedding vector as List[float]
        """
        result = await self.generate_embeddings([text], model=model)
        return result.embeddings[0]
    
    def get_embedding_dimension(self, model: str) -> int:
        """Get the dimensionality of embeddings for a given model.
        
        Args:
            model: Model name
            
        Returns:
            Embedding dimension
            
        Raises:
            ValueError: If model is unknown
        """
        if model not in self.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Unknown OpenAI embedding model: {model}. "
                f"Supported models: {list(self.EMBEDDING_DIMENSIONS.keys())}"
            )
        return self.EMBEDDING_DIMENSIONS[model]


def create_embedding_provider(
    provider: str = "openai",
    api_key: Optional[str] = None
) -> EmbeddingProvider:
    """Factory function to create embedding providers.
    
    Args:
        provider: Provider name (currently only "openai" supported)
        api_key: API key for the provider
        
    Returns:
        EmbeddingProvider instance
        
    Raises:
        ValueError: If provider is unknown
    """
    if provider.lower() == "openai":
        return OpenAIEmbeddingProvider(api_key=api_key)
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            f"Currently supported: openai"
        )
