"""Centralized logging configuration for StratifyAI.

Provides JSON and human-readable log formatters for production
and development use respectively.

Usage:
    from stratifyai.logging_config import configure_logging

    # Development (human-readable)
    configure_logging(format="human", level="DEBUG")

    # Production (JSON for log aggregation)
    configure_logging(format="json", level="INFO")
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import IO, Literal


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production / log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)


def configure_logging(
    format: Literal["json", "human"] = "human",
    level: str = "INFO",
    stream: IO[str] | None = None,
) -> None:
    """Configure the root ``stratifyai`` logger.

    Args:
        format: ``"json"`` for structured JSON output (production),
                ``"human"`` for coloured, readable output (development).
        level: Log level name (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, etc.).
        stream: Output stream (defaults to ``sys.stderr``).
    """
    logger = logging.getLogger("stratifyai")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates on re-configuration
    logger.handlers.clear()

    handler = logging.StreamHandler(stream or sys.stderr)
    if format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    logger.addHandler(handler)
