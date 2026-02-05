"""RAG (Retrieval-Augmented Generation) pipeline implementation.

This module provides a complete RAG pipeline that integrates:
- Document chunking and indexing
- Embedding generation
- Vector database storage
- Semantic search
- LLM-based response generation with citations
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

from .embeddings import EmbeddingProvider, create_embedding_provider
from .vectordb import VectorDBClient, SearchResult
from .client import LLMClient
from .models import ChatRequest, Message
from .chunking import chunk_content, get_chunk_metadata
from .exceptions import LLMAbstractionError


@dataclass
class IndexingResult:
    """Result of indexing operation.
    
    Attributes:
        collection_name: Name of the collection
        num_chunks: Number of chunks indexed
        num_files: Number of files indexed
        total_tokens: Total tokens processed for embeddings
        embedding_cost: Cost of embedding generation
    """
    collection_name: str
    num_chunks: int
    num_files: int
    total_tokens: int
    embedding_cost: float


@dataclass
class RAGResponse:
    """Response from RAG query.
    
    Attributes:
        content: Generated response text
        sources: List of source documents used
        model: LLM model used for generation
        total_cost: Total cost (embeddings + generation)
        num_chunks_retrieved: Number of chunks retrieved
    """
    content: str
    sources: List[Dict[str, Any]]
    model: str
    total_cost: float
    num_chunks_retrieved: int


class RAGClient:
    """Client for RAG (Retrieval-Augmented Generation) operations.
    
    Provides a complete pipeline for:
    1. Indexing documents into vector database
    2. Querying with semantic search
    3. Generating responses with LLM using retrieved context
    """
    
    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        llm_client: Optional[LLMClient] = None,
        persist_directory: Optional[str] = None
    ):
        """Initialize RAG client.
        
        Args:
            embedding_provider: Provider for embeddings (default: OpenAI)
            llm_client: LLM client for generation (default: creates new client)
            persist_directory: Directory for vector database (default: ./chroma_db)
        """
        # Initialize embedding provider
        if embedding_provider is None:
            embedding_provider = create_embedding_provider("openai")
        self.embedding_provider = embedding_provider
        
        # Initialize vector database
        self.vectordb = VectorDBClient(
            embedding_provider=embedding_provider,
            persist_directory=persist_directory
        )
        
        # Initialize LLM client
        if llm_client is None:
            llm_client = LLMClient()
        self.llm_client = llm_client
    
    async def index_file(
        self,
        file_path: str,
        collection_name: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> IndexingResult:
        """Index a single file into the vector database.
        
        Args:
            file_path: Path to file to index
            collection_name: Name of collection to store chunks
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            IndexingResult with statistics
        """
        # Read file
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8")
        
        # Chunk content
        chunks = chunk_content(
            content,
            chunk_size=chunk_size,
            overlap=overlap,
            preserve_boundaries=True
        )
        
        # Create metadata for each chunk
        metadatas = [
            {
                "file": str(path.absolute()),
                "filename": path.name,
                "chunk_idx": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]
        
        # Add to vector database (this generates embeddings automatically)
        # Run in thread pool since ChromaDB is sync
        await asyncio.to_thread(
            self.vectordb.add_documents,
            collection_name=collection_name,
            documents=chunks,
            metadatas=metadatas
        )
        
        # Get embedding stats (estimate)
        # Note: actual costs tracked by embedding provider during add_documents
        chunk_metadata = get_chunk_metadata(chunks)
        
        return IndexingResult(
            collection_name=collection_name,
            num_chunks=len(chunks),
            num_files=1,
            total_tokens=chunk_metadata["total_chars"] // 4,  # Rough estimate
            embedding_cost=0.0  # Would need to track from vectordb
        )
    
    async def index_directory(
        self,
        directory_path: str,
        collection_name: str,
        file_patterns: Optional[List[str]] = None,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> IndexingResult:
        """Index all files in a directory.
        
        Args:
            directory_path: Path to directory
            collection_name: Name of collection to store chunks
            file_patterns: List of file patterns (e.g., ["*.txt", "*.md"])
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            IndexingResult with statistics
        """
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise ValueError(f"Invalid directory: {directory_path}")
        
        # Default patterns
        if file_patterns is None:
            file_patterns = ["*.txt", "*.md", "*.py", "*.js", "*.java", "*.cpp"]
        
        # Find all matching files
        files = []
        for pattern in file_patterns:
            files.extend(dir_path.rglob(pattern))
        
        if not files:
            raise LLMAbstractionError(
                f"No files found matching patterns {file_patterns} in {directory_path}"
            )
        
        # Index each file
        total_chunks = 0
        total_tokens = 0
        
        for file_path in files:
            try:
                result = await self.index_file(
                    file_path=str(file_path),
                    collection_name=collection_name,
                    chunk_size=chunk_size,
                    overlap=overlap
                )
                total_chunks += result.num_chunks
                total_tokens += result.total_tokens
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to index {file_path}: {str(e)}")
        
        return IndexingResult(
            collection_name=collection_name,
            num_chunks=total_chunks,
            num_files=len(files),
            total_tokens=total_tokens,
            embedding_cost=0.0
        )
    
    async def query(
        self,
        collection_name: str,
        query: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        n_results: int = 5,
        include_sources: bool = True
    ) -> RAGResponse:
        """Query the RAG system.
        
        Args:
            collection_name: Collection to query
            query: User query
            provider: LLM provider for generation
            model: LLM model for generation
            n_results: Number of chunks to retrieve
            include_sources: Whether to include source citations
            
        Returns:
            RAGResponse with generated content and sources
        """
        # Retrieve relevant chunks (run in thread pool since ChromaDB is sync)
        search_results = await asyncio.to_thread(
            self.vectordb.query,
            collection_name=collection_name,
            query_text=query,
            n_results=n_results
        )
        
        if not search_results:
            raise LLMAbstractionError(
                f"No results found in collection '{collection_name}'. "
                "Ensure the collection exists and has documents."
            )
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        
        for i, result in enumerate(search_results):
            context_parts.append(f"[Source {i+1}]\n{result.document}")
            sources.append({
                "index": i + 1,
                "file": result.metadata.get("filename", "unknown"),
                "chunk_idx": result.metadata.get("chunk_idx", 0),
                "similarity": 1.0 - result.distance  # Convert distance to similarity
            })
        
        context = "\n\n".join(context_parts)
        
        # Build prompt with context
        prompt = f"""Answer the following question using ONLY the information provided in the sources below.
If the answer cannot be found in the sources, say "I cannot answer this based on the provided sources."

Sources:
{context}

Question: {query}

Answer:"""
        
        # Generate response
        messages = [Message(role="user", content=prompt)]
        request = ChatRequest(
            model=model,
            messages=messages,
            temperature=0.3  # Lower temperature for more factual responses
        )
        
        # Create client with specified provider for this request
        client = LLMClient(provider=provider)
        response = await client.chat_completion(request=request)
        
        # Calculate total cost (embedding + generation)
        total_cost = response.usage.cost_usd if response.usage else 0.0
        
        return RAGResponse(
            content=response.content,
            sources=sources if include_sources else [],
            model=response.model,
            total_cost=total_cost,
            num_chunks_retrieved=len(search_results)
        )
    
    def list_collections(self) -> List[str]:
        """List all available collections.
        
        Returns:
            List of collection names
        """
        return self.vectordb.list_collections()
    
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.
        
        Args:
            collection_name: Collection to delete
        """
        self.vectordb.delete_collection(collection_name)
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Dictionary with collection statistics
        """
        count = self.vectordb.get_collection_count(collection_name)
        
        # Get sample documents to extract file info
        sample_docs = self.vectordb.get_documents(
            collection_name=collection_name,
            limit=100
        )
        
        # Extract unique files
        files = set()
        for doc in sample_docs:
            if "filename" in doc["metadata"]:
                files.add(doc["metadata"]["filename"])
        
        return {
            "name": collection_name,
            "num_chunks": count,
            "num_files": len(files),
            "sample_files": list(files)[:10]  # Show up to 10 files
        }
    
    def retrieve_only(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5
    ) -> List[SearchResult]:
        """Retrieve relevant chunks without generating a response.
        
        Useful for testing retrieval quality.
        
        Args:
            collection_name: Collection to query
            query: Query text
            n_results: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        return self.vectordb.query(
            collection_name=collection_name,
            query_text=query,
            n_results=n_results
        )
