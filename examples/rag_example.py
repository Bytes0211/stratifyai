"""Example: RAG (Retrieval-Augmented Generation) Pipeline

This example demonstrates how to:
1. Index documents into a vector database
2. Query the indexed documents with semantic search
3. Generate responses using retrieved context
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from stratifyai import RAGClient

def example_basic_rag():
    """Basic RAG example: Index a file and query it."""
    print("=" * 70)
    print("Example 1: Basic RAG - Index and Query")
    print("=" * 70)
    
    # Initialize RAG client
    rag = RAGClient()
    
    # Create a sample document
    sample_doc_path = "sample_document.txt"
    with open(sample_doc_path, "w") as f:
        f.write("""
# Python Programming Guide

Python is a high-level, interpreted programming language known for its simplicity and readability.
It was created by Guido van Rossum and first released in 1991.

## Key Features

1. **Easy to Learn**: Python has a simple and straightforward syntax that resembles natural language.

2. **Versatile**: Python can be used for web development, data science, machine learning, automation, and more.

3. **Large Ecosystem**: Python has a vast collection of libraries and frameworks like Django, Flask, NumPy, and pandas.

## Data Types

Python supports various data types:
- Integers: Whole numbers like 1, 42, -5
- Floats: Decimal numbers like 3.14, -0.5
- Strings: Text enclosed in quotes like "hello" or 'world'
- Lists: Ordered collections like [1, 2, 3]
- Dictionaries: Key-value pairs like {"name": "Alice", "age": 30}

## Functions

Functions in Python are defined using the 'def' keyword:

```python
def greet(name):
    return f"Hello, {name}!"
```

## Common Libraries

- **NumPy**: For numerical computations
- **pandas**: For data manipulation and analysis
- **requests**: For making HTTP requests
- **matplotlib**: For data visualization
        """)
    
    print(f"\n✓ Created sample document: {sample_doc_path}")
    
    # Index the document
    print("\n📚 Indexing document...")
    result = rag.index_file(
        file_path=sample_doc_path,
        collection_name="python_docs",
        chunk_size=500,
        overlap=100
    )
    
    print(f"   ✓ Indexed {result.num_chunks} chunks")
    print(f"   ✓ Estimated {result.total_tokens:,} tokens")
    
    # Query the indexed document
    print("\n🔍 Querying: 'What are the key features of Python?'")
    response = rag.query(
        collection_name="python_docs",
        query="What are the key features of Python?",
        provider="openai",
        model="gpt-4o-mini"
    )
    
    print(f"\n💬 Response:")
    print(f"{response.content}\n")
    
    print(f"📊 Stats:")
    print(f"   • Chunks retrieved: {response.num_chunks_retrieved}")
    print(f"   • Cost: ${response.total_cost:.6f}")
    print(f"   • Model: {response.model}")
    
    if response.sources:
        print(f"\n📖 Sources:")
        for source in response.sources:
            print(f"   • {source['file']} (chunk {source['chunk_idx']}, similarity: {source['similarity']:.2%})")
    
    # Cleanup
    rag.delete_collection("python_docs")
    os.remove(sample_doc_path)
    print(f"\n✓ Cleaned up collection and sample file")


def example_directory_indexing():
    """Example: Index all files in a directory."""
    print("\n" + "=" * 70)
    print("Example 2: Index Directory")
    print("=" * 70)
    
    # Create a temporary directory with multiple files
    temp_dir = Path("temp_docs")
    temp_dir.mkdir(exist_ok=True)
    
    # Create sample files
    (temp_dir / "intro.txt").write_text("""
Machine Learning is a subset of artificial intelligence that enables systems to learn from data.
Common algorithms include linear regression, decision trees, and neural networks.
    """)
    
    (temp_dir / "algorithms.txt").write_text("""
Neural networks are inspired by biological neurons. They consist of layers of interconnected nodes.
Deep learning uses neural networks with many layers to learn complex patterns.
    """)
    
    (temp_dir / "applications.txt").write_text("""
Machine learning applications include image recognition, natural language processing,
recommendation systems, and autonomous vehicles.
    """)
    
    print(f"\n✓ Created sample directory with 3 files")
    
    # Initialize RAG client
    rag = RAGClient()
    
    # Index all files in the directory
    print("\n📚 Indexing directory...")
    result = rag.index_directory(
        directory_path=str(temp_dir),
        collection_name="ml_docs",
        file_patterns=["*.txt"],
        chunk_size=300
    )
    
    print(f"   ✓ Indexed {result.num_files} files")
    print(f"   ✓ Total chunks: {result.num_chunks}")
    
    # Query the collection
    print("\n🔍 Querying: 'What are neural networks?'")
    response = rag.query(
        collection_name="ml_docs",
        query="What are neural networks?",
        n_results=3
    )
    
    print(f"\n💬 Response:")
    print(f"{response.content}\n")
    
    # Get collection stats
    stats = rag.get_collection_stats("ml_docs")
    print(f"📊 Collection Stats:")
    print(f"   • Total chunks: {stats['num_chunks']}")
    print(f"   • Files indexed: {stats['num_files']}")
    print(f"   • Sample files: {', '.join(stats['sample_files'])}")
    
    # Cleanup
    rag.delete_collection("ml_docs")
    for file in temp_dir.glob("*.txt"):
        file.unlink()
    temp_dir.rmdir()
    print(f"\n✓ Cleaned up collection and temp directory")


def example_retrieval_only():
    """Example: Retrieve relevant chunks without LLM generation."""
    print("\n" + "=" * 70)
    print("Example 3: Retrieval Only (No LLM)")
    print("=" * 70)
    
    # Create sample document
    sample_doc_path = "sample_tech.txt"
    with open(sample_doc_path, "w") as f:
        f.write("""
Docker is a platform for containerizing applications. Containers package code and dependencies together.

Kubernetes is a container orchestration platform. It manages deployment, scaling, and operations of containers.

Terraform is an infrastructure as code tool. It allows you to define and provision infrastructure using declarative config files.
        """)
    
    print(f"\n✓ Created sample document")
    
    # Initialize and index
    rag = RAGClient()
    rag.index_file(
        file_path=sample_doc_path,
        collection_name="tech_docs",
        chunk_size=200
    )
    
    print("✓ Indexed document")
    
    # Retrieve without LLM generation
    print("\n🔍 Retrieving chunks for: 'container management'")
    results = rag.retrieve_only(
        collection_name="tech_docs",
        query="container management",
        n_results=2
    )
    
    print(f"\n📄 Retrieved {len(results)} relevant chunks:\n")
    for i, result in enumerate(results, 1):
        print(f"Chunk {i} (similarity: {1-result.distance:.2%}):")
        print(f"{result.document}\n")
    
    # Cleanup
    rag.delete_collection("tech_docs")
    os.remove(sample_doc_path)
    print("✓ Cleaned up")


def example_list_collections():
    """Example: List and manage collections."""
    print("\n" + "=" * 70)
    print("Example 4: Collection Management")
    print("=" * 70)
    
    rag = RAGClient()
    
    # Create a few collections
    sample_path = "temp.txt"
    with open(sample_path, "w") as f:
        f.write("Sample content for testing.")
    
    print("\n📚 Creating test collections...")
    for name in ["collection_a", "collection_b", "collection_c"]:
        rag.index_file(sample_path, collection_name=name, chunk_size=100)
        print(f"   ✓ Created {name}")
    
    # List all collections
    print("\n📋 Listing all collections:")
    collections = rag.list_collections()
    for col in collections:
        stats = rag.get_collection_stats(col)
        print(f"   • {col}: {stats['num_chunks']} chunks")
    
    # Cleanup all
    print("\n🗑  Deleting collections...")
    for col in collections:
        rag.delete_collection(col)
        print(f"   ✓ Deleted {col}")
    
    os.remove(sample_path)
    print("\n✓ Cleanup complete")


if __name__ == "__main__":
    print("\n🚀 StratifyAI RAG Examples\n")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set your OpenAI API key to run these examples.")
        exit(1)
    
    try:
        # Run examples
        example_basic_rag()
        example_directory_indexing()
        example_retrieval_only()
        example_list_collections()
        
        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
