"""Vector database integration for RAG and semantic search.

This module provides abstraction for storing and retrieving document embeddings
using ChromaDB (with potential support for other vector databases).
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .embeddings import EmbeddingProvider
from .exceptions import LLMAbstractionError


@dataclass
class SearchResult:
    """Result from a semantic search query.
    
    Attributes:
        document: The matched document text
        metadata: Document metadata (file, chunk_idx, etc.)
        distance: Distance score (lower = more similar)
        doc_id: Unique document ID
    """
    document: str
    metadata: Dict[str, Any]
    distance: float
    doc_id: str


class VectorDBClient:
    """Client for vector database operations using ChromaDB.
    
    Provides document storage, retrieval, and semantic search capabilities.
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        persist_directory: Optional[str] = None
    ):
        """Initialize vector database client.
        
        Args:
            embedding_provider: Provider for generating embeddings
            persist_directory: Directory to persist database (default: ./chroma_db)
            
        Raises:
            LLMAbstractionError: If ChromaDB is not installed
        """
        if not CHROMADB_AVAILABLE:
            raise LLMAbstractionError(
                "ChromaDB is not installed. Install with: pip install chromadb"
            )
        
        self.embedding_provider = embedding_provider
        self.persist_directory = persist_directory or "./chroma_db"
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
    
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new collection.
        
        Args:
            name: Collection name
            metadata: Optional collection metadata
            
        Returns:
            Collection name
            
        Raises:
            LLMAbstractionError: If collection already exists
        """
        try:
            self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )
            return name
        except Exception as e:
            if "already exists" in str(e).lower():
                raise LLMAbstractionError(
                    f"Collection '{name}' already exists. Use get_collection() or delete it first."
                )
            raise LLMAbstractionError(f"Failed to create collection: {str(e)}")
    
    def get_collection(self, name: str):
        """Get an existing collection.
        
        Args:
            name: Collection name
            
        Returns:
            ChromaDB collection object
            
        Raises:
            LLMAbstractionError: If collection doesn't exist
        """
        try:
            return self.client.get_collection(name=name)
        except Exception as e:
            raise LLMAbstractionError(
                f"Collection '{name}' not found. Create it with create_collection()."
            )
    
    def get_or_create_collection(self, name: str):
        """Get existing collection or create if it doesn't exist.
        
        Args:
            name: Collection name
            
        Returns:
            ChromaDB collection object
        """
        return self.client.get_or_create_collection(name=name)
    
    def list_collections(self) -> List[str]:
        """List all collections.
        
        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [col.name for col in collections]
    
    def delete_collection(self, name: str) -> None:
        """Delete a collection.
        
        Args:
            name: Collection name
        """
        try:
            self.client.delete_collection(name=name)
        except Exception as e:
            raise LLMAbstractionError(f"Failed to delete collection: {str(e)}")
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to a collection.
        
        Args:
            collection_name: Collection name
            documents: List of document texts
            metadatas: Optional list of metadata dicts (one per document)
            ids: Optional list of document IDs (generated if not provided)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Get or create collection
        collection = self.get_or_create_collection(collection_name)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Add timestamp to metadata
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        for metadata in metadatas:
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.now().isoformat()
        
        # Generate embeddings
        embedding_result = self.embedding_provider.generate_embeddings(documents)
        
        # Add to collection
        collection.add(
            documents=documents,
            embeddings=embedding_result.embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Query collection with semantic search.
        
        Args:
            collection_name: Collection name
            query_text: Query text
            n_results: Number of results to return (default: 5)
            where: Optional metadata filter
            
        Returns:
            List of SearchResult objects
        """
        collection = self.get_collection(collection_name)
        
        # Generate query embedding
        query_embedding = self.embedding_provider.generate_embedding(query_text)
        
        # Query collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        # Parse results
        search_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                search_results.append(
                    SearchResult(
                        document=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        distance=results["distances"][0][i] if results["distances"] else 0.0,
                        doc_id=results["ids"][0][i]
                    )
                )
        
        return search_results
    
    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Number of documents
        """
        collection = self.get_collection(collection_name)
        return collection.count()
    
    def delete_documents(
        self,
        collection_name: str,
        ids: List[str]
    ) -> None:
        """Delete documents from a collection by ID.
        
        Args:
            collection_name: Collection name
            ids: List of document IDs to delete
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids)
    
    def update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Update documents in a collection.
        
        Args:
            collection_name: Collection name
            ids: List of document IDs to update
            documents: Optional new document texts
            metadatas: Optional new metadatas
        """
        collection = self.get_collection(collection_name)
        
        update_kwargs = {"ids": ids}
        
        if documents is not None:
            # Generate new embeddings
            embedding_result = self.embedding_provider.generate_embeddings(documents)
            update_kwargs["documents"] = documents
            update_kwargs["embeddings"] = embedding_result.embeddings
        
        if metadatas is not None:
            update_kwargs["metadatas"] = metadatas
        
        collection.update(**update_kwargs)
    
    def get_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve documents from a collection.
        
        Args:
            collection_name: Collection name
            ids: Optional list of document IDs to retrieve
            where: Optional metadata filter
            limit: Maximum number of documents to return
            
        Returns:
            List of documents with metadata
        """
        collection = self.get_collection(collection_name)
        
        get_kwargs = {}
        if ids is not None:
            get_kwargs["ids"] = ids
        if where is not None:
            get_kwargs["where"] = where
        if limit is not None:
            get_kwargs["limit"] = limit
        
        results = collection.get(**get_kwargs)
        
        # Format results
        documents = []
        if results["documents"]:
            for i in range(len(results["documents"])):
                documents.append({
                    "id": results["ids"][i],
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        
        return documents
