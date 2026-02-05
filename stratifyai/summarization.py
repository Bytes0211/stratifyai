"""Progressive summarization utilities for large files."""

from typing import List, Optional
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .client import LLMClient
from .models import ChatRequest, Message
from .chunking import chunk_content, get_chunk_metadata


def summarize_chunk(
    chunk: str,
    client: LLMClient,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1000,
    context: Optional[str] = None
) -> str:
    """
    Summarize a single chunk of content.
    
    Uses a cheaper model for cost efficiency.
    
    Args:
        chunk: The content chunk to summarize
        client: LLMClient instance (already configured with provider)
        model: Model to use for summarization (default: gpt-4o-mini for cost)
        max_tokens: Maximum tokens for summary
        context: Optional context about the overall document
        
    Returns:
        Summary of the chunk
    """
    # Build prompt
    if context:
        prompt = f"""Summarize the following section from a larger document.

Context: {context}

Section to summarize:
{chunk}

Provide a concise summary that preserves key information."""
    else:
        prompt = f"""Summarize the following text concisely, preserving key information:

{chunk}"""
    
    # Create request
    request = ChatRequest(
        model=model,
        messages=[Message(role="user", content=prompt)],
        max_tokens=max_tokens
    )
    
    # Get summary
    response = client.chat_completion(request)
    return response.content


def summarize_chunks_progressive(
    chunks: List[str],
    client: LLMClient,
    model: str = "gpt-4o-mini",
    context: Optional[str] = None,
    show_progress: bool = True
) -> str:
    """
    Progressively summarize multiple chunks.
    
    Each chunk is summarized individually, then all summaries are combined.
    
    Args:
        chunks: List of content chunks
        client: LLMClient instance
        model: Model to use for summarization
        context: Optional context about the overall document
        show_progress: Whether to show progress bar
        
    Returns:
        Combined summary of all chunks
    """
    if not chunks:
        return ""
    
    if len(chunks) == 1:
        return summarize_chunk(chunks[0], client, model, context=context)
    
    summaries = []
    
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task(
                f"[cyan]Summarizing {len(chunks)} chunks...",
                total=len(chunks)
            )
            
            for i, chunk in enumerate(chunks, 1):
                summary = summarize_chunk(
                    chunk,
                    client,
                    model,
                    context=f"{context} (Part {i}/{len(chunks)})" if context else f"Part {i}/{len(chunks)}"
                )
                summaries.append(f"**Part {i}/{len(chunks)}:**\n{summary}")
                progress.update(task, advance=1)
    else:
        for i, chunk in enumerate(chunks, 1):
            summary = summarize_chunk(
                chunk,
                client,
                model,
                context=f"{context} (Part {i}/{len(chunks)})" if context else f"Part {i}/{len(chunks)}"
            )
            summaries.append(f"**Part {i}/{len(chunks)}:**\n{summary}")
    
    # Combine summaries
    combined = "\n\n".join(summaries)
    
    # If combined summaries are still very long, summarize the summaries
    if len(combined) > 10000:  # Arbitrary threshold
        final_summary = summarize_chunk(
            combined,
            client,
            model,
            context="Combined summaries of document sections"
        )
        return f"**Overall Summary:**\n{final_summary}\n\n**Detailed Summaries:**\n{combined}"
    
    return combined


def summarize_file(
    content: str,
    client: LLMClient,
    chunk_size: int = 50000,
    model: str = "gpt-4o-mini",
    context: Optional[str] = None,
    show_progress: bool = True
) -> dict:
    """
    Summarize a large file using progressive chunking.
    
    Args:
        content: Full file content
        client: LLMClient instance
        chunk_size: Size of chunks in characters
        model: Model to use for summarization
        context: Optional context about the document
        show_progress: Whether to show progress
        
    Returns:
        Dictionary with summary and metadata
    """
    # Chunk the content
    chunks = chunk_content(content, chunk_size=chunk_size)
    metadata = get_chunk_metadata(chunks)
    
    # Summarize chunks
    summary = summarize_chunks_progressive(
        chunks,
        client,
        model=model,
        context=context,
        show_progress=show_progress
    )
    
    return {
        "summary": summary,
        "original_length": len(content),
        "summary_length": len(summary),
        "reduction_percentage": round((1 - len(summary) / len(content)) * 100, 1),
        "num_chunks": metadata["num_chunks"],
        "chunk_metadata": metadata
    }
