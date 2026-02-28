"""Content chunking utilities for splitting large files into manageable pieces."""

from typing import List, Optional
import re


def chunk_content(
    content: str,
    chunk_size: int = 50000,
    overlap: int = 500,
    preserve_boundaries: bool = True
) -> List[str]:
    """
    Split content into chunks at natural boundaries.
    
    Splits at paragraph boundaries when possible, falling back to sentence
    boundaries, then character boundaries for very large paragraphs.
    
    Args:
        content: The text content to chunk
        chunk_size: Target size for each chunk in characters (default: 50000)
        overlap: Number of characters to overlap between chunks (default: 500)
        preserve_boundaries: Whether to split at natural boundaries vs fixed positions
        
    Returns:
        List of content chunks
        
    Examples:
        >>> text = "Paragraph 1.\\n\\nParagraph 2.\\n\\nParagraph 3."
        >>> chunks = chunk_content(text, chunk_size=20)
        >>> len(chunks)
        3
    """
    if not content:
        return []
    
    # If content is smaller than chunk_size, return as-is
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    
    if preserve_boundaries:
        # Split at paragraph boundaries first
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk_size
            if len(current_chunk) + len(paragraph) + 2 > chunk_size:
                # If current chunk is not empty, save it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap from previous
                    if overlap > 0 and len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:]
                    else:
                        current_chunk = ""
                
                # If paragraph itself is larger than chunk_size, split it
                if len(paragraph) > chunk_size:
                    sub_chunks = _split_large_paragraph(paragraph, chunk_size, overlap)
                    chunks.extend(sub_chunks[:-1])  # Add all but last
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = paragraph
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
    
    else:
        # Fixed-position chunking (fallback)
        position = 0
        while position < len(content):
            end_position = position + chunk_size
            chunk = content[position:end_position]
            chunks.append(chunk)
            position = end_position - overlap
    
    return chunks


def _split_large_paragraph(paragraph: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split a large paragraph at sentence boundaries.
    
    Args:
        paragraph: The paragraph to split
        chunk_size: Target chunk size
        overlap: Overlap between chunks
        
    Returns:
        List of paragraph chunks
    """
    # Split at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Sentence itself is too large - force split
                current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def get_chunk_metadata(chunks: List[str]) -> dict:
    """
    Get metadata about chunks.
    
    Args:
        chunks: List of content chunks
        
    Returns:
        Dictionary with chunk statistics
    """
    if not chunks:
        return {
            "num_chunks": 0,
            "total_chars": 0,
            "avg_chunk_size": 0,
            "min_chunk_size": 0,
            "max_chunk_size": 0,
        }
    
    chunk_sizes = [len(chunk) for chunk in chunks]
    
    return {
        "num_chunks": len(chunks),
        "total_chars": sum(chunk_sizes),
        "avg_chunk_size": int(sum(chunk_sizes) / len(chunks)),
        "min_chunk_size": min(chunk_sizes),
        "max_chunk_size": max(chunk_sizes),
    }
