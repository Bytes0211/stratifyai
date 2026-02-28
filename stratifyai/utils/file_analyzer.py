"""File analysis utilities for detecting file types and estimating token usage."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum

from .token_counter import estimate_tokens, check_token_limit


class FileType(Enum):
    """Supported file types for intelligent processing."""
    CSV = "csv"
    JSON = "json"
    LOG = "log"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    TEXT = "text"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


@dataclass
class FileAnalysis:
    """Results of file analysis."""
    file_path: Path
    file_type: FileType
    file_size_bytes: int
    file_size_mb: float
    content_length: int
    estimated_tokens: int
    exceeds_threshold: bool
    context_window: int
    percentage_used: float
    recommendation: str


def detect_file_type(file_path: Path) -> FileType:
    """
    Detect the type of file based on extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        FileType enum value
    """
    suffix = file_path.suffix.lower()
    
    # Map file extensions to types
    type_mapping = {
        ".csv": FileType.CSV,
        ".json": FileType.JSON,
        ".log": FileType.LOG,
        ".py": FileType.PYTHON,
        ".js": FileType.JAVASCRIPT,
        ".ts": FileType.JAVASCRIPT,
        ".jsx": FileType.JAVASCRIPT,
        ".tsx": FileType.JAVASCRIPT,
        ".java": FileType.JAVA,
        ".go": FileType.GO,
        ".txt": FileType.TEXT,
        ".md": FileType.MARKDOWN,
        ".markdown": FileType.MARKDOWN,
    }
    
    return type_mapping.get(suffix, FileType.UNKNOWN)


def get_recommendation(
    file_type: FileType,
    estimated_tokens: int,
    context_window: int,
    percentage_used: float
) -> str:
    """
    Get processing recommendation based on file analysis.
    
    Args:
        file_type: Detected file type
        estimated_tokens: Estimated token count
        context_window: Model's context window
        percentage_used: Percentage of context window used
        
    Returns:
        Recommendation string
    """
    # File fits comfortably in context
    if percentage_used < 0.5:
        return "✓ File fits well in model context - direct upload recommended"
    
    # File approaching context limit
    elif percentage_used < 0.8:
        return "⚠ File uses >50% of context - consider chunking for better performance"
    
    # File exceeds safe threshold
    else:
        if file_type == FileType.CSV:
            return "⚠ Large CSV detected - use schema extraction (--extract-mode schema) for 99% token reduction"
        elif file_type == FileType.JSON:
            return "⚠ Large JSON detected - use schema extraction (--extract-mode schema) for 95% token reduction"
        elif file_type == FileType.LOG:
            return "⚠ Large log file detected - use error extraction (--extract errors) for 90% token reduction"
        elif file_type in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.JAVA, FileType.GO]:
            return "⚠ Large code file detected - use code extraction (--extract summary) for 80% token reduction"
        elif estimated_tokens > context_window:
            return "✗ File exceeds model context - chunking required (--chunked)"
        else:
            return "⚠ File near context limit - chunking recommended (--chunked) for 90% token reduction"


def analyze_file(
    file_path: Path,
    provider: str = "openai",
    model: str = "gpt-4o",
    threshold: float = 0.8
) -> FileAnalysis:
    """
    Analyze a file and provide recommendations for processing.
    
    Args:
        file_path: Path to the file to analyze
        provider: LLM provider for token estimation
        model: LLM model for context window limits
        threshold: Warning threshold (default 0.8 = 80%)
        
    Returns:
        FileAnalysis object with complete analysis
        
    Raises:
        FileNotFoundError: If file doesn't exist
        
    Examples:
        >>> analysis = analyze_file(Path("data.csv"), "openai", "gpt-4o")
        >>> print(f"Tokens: {analysis.estimated_tokens}")
        >>> print(analysis.recommendation)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file info
    file_size_bytes = file_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # Detect file type
    file_type = detect_file_type(file_path)
    
    # Read file content (with size limit for very large files)
    MAX_READ_SIZE = 10 * 1024 * 1024  # 10MB max for token estimation
    try:
        if file_size_bytes > MAX_READ_SIZE:
            # For very large files, estimate based on sample
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(MAX_READ_SIZE)
            # Extrapolate token count
            sample_tokens = estimate_tokens(sample, provider, model)
            estimated_tokens = int(sample_tokens * (file_size_bytes / len(sample)))
            content_length = file_size_bytes  # Approximate
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content_length = len(content)
            estimated_tokens = estimate_tokens(content, provider, model)
    except UnicodeDecodeError:
        # Binary file - rough estimate based on size
        content_length = file_size_bytes
        estimated_tokens = int(file_size_bytes / 4)  # Very rough estimate
    
    # Check token limits
    exceeds_threshold, context_window, percentage_used = check_token_limit(
        estimated_tokens, provider, model, threshold
    )
    
    # Get recommendation
    recommendation = get_recommendation(
        file_type, estimated_tokens, context_window, percentage_used
    )
    
    return FileAnalysis(
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        file_size_mb=file_size_mb,
        content_length=content_length,
        estimated_tokens=estimated_tokens,
        exceeds_threshold=exceeds_threshold,
        context_window=context_window,
        percentage_used=percentage_used,
        recommendation=recommendation
    )
