"""
Input sanitization and prompt injection detection for JustiBot.
Protects the LLM from adversarial user inputs.
"""

import re

from fastapi import HTTPException

# Known prompt injection patterns (case-insensitive)
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "forget everything",
    "new instructions",
    "system prompt",
    "jailbreak",
    "act as",
    "pretend you are",
    "disregard",
    "override",
]

# Control characters to strip (everything below ASCII 32 except \n and \t)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Collapse multiple spaces into one
_MULTI_SPACE_RE = re.compile(r" {2,}")


def sanitize_input(text: str) -> str:
    """
    Clean raw user input for safe downstream processing.

    - Strips leading/trailing whitespace
    - Collapses multiple spaces to a single space
    - Removes null bytes and non-printable control characters
      (preserves \\n and \\t)
    - Truncates to 2000 characters

    Args:
        text: Raw input string.

    Returns:
        Sanitized string (may be empty if input was only whitespace/control chars).
    """
    text = text.strip()
    text = _CONTROL_CHAR_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = text[:2000]
    return text


def detect_injection(text: str) -> bool:
    """
    Check whether the text contains known prompt injection patterns.

    Args:
        text: Sanitized input string.

    Returns:
        True if any injection pattern is found, False otherwise.
    """
    lowered = text.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


def validate_query(text: str) -> str:
    """
    Sanitize and validate a user query before it reaches the LLM.

    Args:
        text: Raw user query.

    Returns:
        Sanitized query string if safe.

    Raises:
        HTTPException 400: If the query is empty or contains injection patterns.
    """
    sanitized = sanitize_input(text)

    if not sanitized:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if detect_injection(sanitized):
        raise HTTPException(status_code=400, detail="Query contains disallowed content")

    return sanitized
