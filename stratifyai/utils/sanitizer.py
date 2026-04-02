"""Sanitization helpers for safe error handling."""

import re

# Pre-compiled patterns for known API key formats
_KEY_PATTERNS = [
    # OpenAI keys (standard and project-scoped)
    re.compile(r"sk-[a-zA-Z0-9\-_]{16,}"),
    re.compile(r"sk-proj-[a-zA-Z0-9\-_]{16,}"),
    # Anthropic keys
    re.compile(r"sk-ant-[a-zA-Z0-9\-_]{16,}"),
    # Groq keys
    re.compile(r"gsk_[a-zA-Z0-9\-_]{16,}"),
    # Grok / xAI keys
    re.compile(r"xai-[a-zA-Z0-9\-_]{16,}"),
    # Google API keys (AIzaSy...)
    re.compile(r"AIza[a-zA-Z0-9\-_]{30,}"),
    # AWS access key IDs (always start with AKIA for long-term keys)
    re.compile(r"AKIA[A-Z0-9]{16}"),
    # AWS secret access keys (40-char base64-ish strings preceded by common assignment patterns)
    re.compile(r"(?<=secret_access_key[=: ])[A-Za-z0-9/+=]{40}"),
    # OpenRouter keys
    re.compile(r"sk-or-v1-[a-zA-Z0-9\-_]{16,}"),
    # DeepSeek keys
    re.compile(r"sk-[a-f0-9]{32,}"),
    # Generic bearer-style long hex/base64 tokens (catch-all, 64+ chars)
    re.compile(r"[A-Za-z0-9\-_]{64,}"),
]

_REDACTED = "***REDACTED***"


def sanitize_error(message: str, api_key: str | None = None) -> str:
    """Remove sensitive API key fragments from error messages.

    Strategy:
    1. If a known ``api_key`` is provided, replace the full key first.
    2. Only if the full key was **not** found, attempt a prefix-only match
       (first 12 chars).  The last-4-char partial match is intentionally
       skipped because short suffixes cause excessive false positives.
    3. Apply regex-based scrubbing for all known provider key formats,
       regardless of whether a specific key was supplied.

    Args:
        message: The raw error string that may contain key material.
        api_key: The specific API key to scrub, if known.

    Returns:
        Sanitised message with key material replaced by ``***REDACTED***``.
    """
    sanitized = message

    # --- Phase 1: exact key removal ----------------------------------------
    if api_key and len(api_key) >= 8:
        if api_key in sanitized:
            # Full key present — replace it and skip partial matching
            sanitized = sanitized.replace(api_key, _REDACTED)
        else:
            # Full key not found; try a longer prefix (12 chars min) to
            # reduce false positives compared to the previous 8-char prefix.
            prefix_len = min(len(api_key), max(12, len(api_key) // 2))
            prefix = api_key[:prefix_len]
            if prefix in sanitized:
                sanitized = sanitized.replace(prefix, _REDACTED)

    # --- Phase 2: regex-based pattern scrubbing ----------------------------
    for pattern in _KEY_PATTERNS:
        sanitized = pattern.sub(_REDACTED, sanitized)

    return sanitized
