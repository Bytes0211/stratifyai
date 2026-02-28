"""CSV/DataFrame schema extraction for intelligent file analysis.

This module extracts compact schema information from CSV files to reduce
token usage by 99%+ while preserving essential structure information.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


@dataclass
class ColumnSchema:
    """Schema information for a single column."""
    name: str
    dtype: str
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any]
    numeric_stats: Optional[Dict[str, float]] = None


@dataclass
class CSVSchema:
    """Complete schema information for a CSV file."""
    file_path: str
    row_count: int
    column_count: int
    columns: List[ColumnSchema]
    memory_usage_mb: float
    
    def to_text(self) -> str:
        """Convert schema to human-readable text representation.
        
        Returns:
            Formatted schema description
        """
        lines = [
            f"CSV File: {self.file_path}",
            f"Dimensions: {self.row_count:,} rows × {self.column_count} columns",
            f"Memory: {self.memory_usage_mb:.2f} MB",
            "",
            "Column Schema:"
        ]
        
        for col in self.columns:
            # Basic info
            lines.append(f"\n  {col.name} ({col.dtype})")
            lines.append(f"    - Null: {col.null_count:,} ({col.null_percentage:.1f}%)")
            lines.append(f"    - Unique: {col.unique_count:,}")
            
            # Numeric stats if available
            if col.numeric_stats:
                stats = col.numeric_stats
                lines.append(f"    - Range: {stats['min']:.2f} to {stats['max']:.2f}")
                lines.append(f"    - Mean: {stats['mean']:.2f}, Median: {stats['median']:.2f}")
                lines.append(f"    - Std: {stats['std']:.2f}")
            
            # Sample values
            samples_str = ", ".join(str(v) for v in col.sample_values[:5])
            lines.append(f"    - Samples: {samples_str}")
        
        return "\n".join(lines)


def extract_csv_schema(
    file_path: Path,
    sample_size: int = 5,
    max_rows: Optional[int] = None
) -> CSVSchema:
    """Extract schema information from a CSV file.
    
    Args:
        file_path: Path to CSV file
        sample_size: Number of sample values to extract per column
        max_rows: Maximum number of rows to read (None = all)
        
    Returns:
        CSVSchema object with extracted information
        
    Raises:
        FileNotFoundError: If file doesn't exist
        pd.errors.EmptyDataError: If CSV is empty
        pd.errors.ParserError: If CSV is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    # Read CSV
    df = pd.read_csv(file_path, nrows=max_rows)
    
    if df.empty:
        raise pd.errors.EmptyDataError(f"CSV file is empty: {file_path}")
    
    # Extract column schemas
    columns = []
    for col_name in df.columns:
        col_data = df[col_name]
        
        # Basic stats
        null_count = col_data.isna().sum()
        null_pct = (null_count / len(df)) * 100
        unique_count = col_data.nunique()
        
        # Sample values (exclude nulls)
        non_null_values = col_data.dropna()
        if len(non_null_values) > 0:
            sample_values = non_null_values.sample(
                min(sample_size, len(non_null_values)),
                random_state=42
            ).tolist()
        else:
            sample_values = []
        
        # Numeric statistics if applicable
        numeric_stats = None
        if pd.api.types.is_numeric_dtype(col_data):
            try:
                numeric_stats = {
                    'min': float(col_data.min()),
                    'max': float(col_data.max()),
                    'mean': float(col_data.mean()),
                    'median': float(col_data.median()),
                    'std': float(col_data.std())
                }
            except (ValueError, TypeError):
                # Handle edge cases (e.g., all NaN)
                pass
        
        columns.append(ColumnSchema(
            name=col_name,
            dtype=str(col_data.dtype),
            null_count=int(null_count),
            null_percentage=float(null_pct),
            unique_count=int(unique_count),
            sample_values=sample_values,
            numeric_stats=numeric_stats
        ))
    
    # Memory usage
    memory_bytes = df.memory_usage(deep=True).sum()
    memory_mb = memory_bytes / (1024 * 1024)
    
    return CSVSchema(
        file_path=str(file_path),
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        memory_usage_mb=memory_mb
    )


def estimate_token_reduction(original_size: int, schema_size: int) -> float:
    """Estimate token reduction percentage.
    
    Args:
        original_size: Size of original CSV in characters
        schema_size: Size of extracted schema in characters
        
    Returns:
        Reduction percentage (0-100)
    """
    if original_size == 0:
        return 0.0
    
    reduction = ((original_size - schema_size) / original_size) * 100
    return max(0.0, min(100.0, reduction))


def analyze_csv_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a CSV file and return comprehensive information.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Dictionary with schema and metadata
    """
    schema = extract_csv_schema(file_path)
    schema_text = schema.to_text()
    
    # Calculate original size
    original_size = file_path.stat().st_size
    schema_size = len(schema_text)
    
    reduction = estimate_token_reduction(original_size, schema_size)
    
    return {
        'schema': schema,
        'schema_text': schema_text,
        'original_size_bytes': original_size,
        'schema_size_bytes': schema_size,
        'token_reduction_pct': reduction,
        'recommended_action': 'Use schema for LLM analysis instead of full CSV'
    }
