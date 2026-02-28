"""Log file error extraction for intelligent file analysis.

This module extracts errors, warnings, and patterns from log files to reduce
token usage by 90%+ while preserving critical information.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter
from datetime import datetime


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: Optional[str]
    level: str  # ERROR, WARN, INFO, DEBUG, etc.
    message: str
    line_number: int


@dataclass
class LogSummary:
    """Summary of log file analysis."""
    file_path: str
    total_lines: int
    errors: List[LogEntry]
    warnings: List[LogEntry]
    error_patterns: Dict[str, int]
    warning_patterns: Dict[str, int]
    timestamp_range: Optional[tuple[str, str]]
    
    def to_text(self) -> str:
        """Convert summary to human-readable text.
        
        Returns:
            Formatted log summary
        """
        lines = [
            f"Log File: {self.file_path}",
            f"Total Lines: {self.total_lines:,}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
        ]
        
        if self.timestamp_range:
            lines.append(f"Time Range: {self.timestamp_range[0]} to {self.timestamp_range[1]}")
        
        # Error patterns
        if self.error_patterns:
            lines.append("\nTop Error Patterns:")
            for pattern, count in sorted(self.error_patterns.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  [{count}×] {pattern}")
        
        # Warning patterns
        if self.warning_patterns:
            lines.append("\nTop Warning Patterns:")
            for pattern, count in sorted(self.warning_patterns.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  [{count}×] {pattern}")
        
        # Recent errors (last 5)
        if self.errors:
            lines.append("\nRecent Errors:")
            for entry in self.errors[-5:]:
                ts = entry.timestamp or "??:??:??"
                lines.append(f"  [Line {entry.line_number}] {ts} - {entry.message[:100]}")
        
        # Recent warnings (last 5)
        if self.warnings:
            lines.append("\nRecent Warnings:")
            for entry in self.warnings[-5:]:
                ts = entry.timestamp or "??:??:??"
                lines.append(f"  [Line {entry.line_number}] {ts} - {entry.message[:100]}")
        
        return "\n".join(lines)


# Common log patterns
LOG_LEVEL_PATTERNS = [
    (r'\b(ERROR|FATAL|CRITICAL)\b', 'ERROR'),
    (r'\b(WARN|WARNING)\b', 'WARN'),
    (r'\b(INFO|INFORMATION)\b', 'INFO'),
    (r'\b(DEBUG|TRACE)\b', 'DEBUG'),
]

TIMESTAMP_PATTERNS = [
    r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',  # ISO format
    r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',     # US format
    r'\d{2}:\d{2}:\d{2}',                         # Time only
]


def extract_timestamp(line: str) -> Optional[str]:
    """Extract timestamp from log line.
    
    Args:
        line: Log line text
        
    Returns:
        Extracted timestamp or None
    """
    for pattern in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    return None


def extract_log_level(line: str) -> Optional[str]:
    """Extract log level from log line.
    
    Args:
        line: Log line text
        
    Returns:
        Log level (ERROR, WARN, INFO, DEBUG) or None
    """
    for pattern, level in LOG_LEVEL_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return level
    return None


def extract_error_pattern(message: str) -> str:
    """Extract pattern from error message by removing variable parts.
    
    Args:
        message: Error message
        
    Returns:
        Pattern string with variables replaced
    """
    # Remove numbers
    pattern = re.sub(r'\b\d+\b', '<NUM>', message)
    
    # Remove hex addresses
    pattern = re.sub(r'0x[0-9a-fA-F]+', '<ADDR>', pattern)
    
    # Remove quoted strings
    pattern = re.sub(r'"[^"]*"', '<STR>', pattern)
    pattern = re.sub(r"'[^']*'", '<STR>', pattern)
    
    # Remove file paths
    pattern = re.sub(r'(/[\w/.-]+|[A-Z]:\\[\w\\.-]+)', '<PATH>', pattern)
    
    # Remove timestamps
    for ts_pattern in TIMESTAMP_PATTERNS:
        pattern = re.sub(ts_pattern, '<TIME>', pattern)
    
    return pattern[:200]  # Truncate long patterns


def analyze_log_file(
    file_path: Path,
    max_lines: Optional[int] = None,
    max_errors: int = 100,
    max_warnings: int = 100
) -> LogSummary:
    """Analyze a log file and extract errors/warnings.
    
    Args:
        file_path: Path to log file
        max_lines: Maximum lines to read (None = all)
        max_errors: Maximum errors to store
        max_warnings: Maximum warnings to store
        
    Returns:
        LogSummary with extracted information
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")
    
    errors: List[LogEntry] = []
    warnings: List[LogEntry] = []
    error_messages: List[str] = []
    warning_messages: List[str] = []
    timestamps: List[str] = []
    
    total_lines = 0
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if max_lines and line_num > max_lines:
                break
            
            total_lines += 1
            line = line.strip()
            if not line:
                continue
            
            # Extract timestamp
            timestamp = extract_timestamp(line)
            if timestamp:
                timestamps.append(timestamp)
            
            # Extract log level
            level = extract_log_level(line)
            
            if level == 'ERROR':
                if len(errors) < max_errors:
                    errors.append(LogEntry(
                        timestamp=timestamp,
                        level='ERROR',
                        message=line,
                        line_number=line_num
                    ))
                error_messages.append(line)
            
            elif level == 'WARN':
                if len(warnings) < max_warnings:
                    warnings.append(LogEntry(
                        timestamp=timestamp,
                        level='WARN',
                        message=line,
                        line_number=line_num
                    ))
                warning_messages.append(line)
    
    # Extract patterns
    error_patterns = Counter(extract_error_pattern(msg) for msg in error_messages)
    warning_patterns = Counter(extract_error_pattern(msg) for msg in warning_messages)
    
    # Timestamp range
    timestamp_range = None
    if timestamps:
        timestamp_range = (timestamps[0], timestamps[-1])
    
    return LogSummary(
        file_path=str(file_path),
        total_lines=total_lines,
        errors=errors,
        warnings=warnings,
        error_patterns=dict(error_patterns.most_common(10)),
        warning_patterns=dict(warning_patterns.most_common(10)),
        timestamp_range=timestamp_range
    )


def extract_log_summary(file_path: Path) -> Dict[str, Any]:
    """Extract summary information from a log file.
    
    Args:
        file_path: Path to log file
        
    Returns:
        Dictionary with summary and metadata
    """
    summary = analyze_log_file(file_path)
    summary_text = summary.to_text()
    
    # Calculate sizes
    original_size = file_path.stat().st_size
    summary_size = len(summary_text)
    
    return {
        'summary': summary,
        'summary_text': summary_text,
        'original_size_bytes': original_size,
        'summary_size_bytes': summary_size,
        'token_reduction_pct': ((original_size - summary_size) / original_size * 100) if original_size > 0 else 0.0,
        'recommended_action': 'Use summary for LLM analysis instead of full log file'
    }
