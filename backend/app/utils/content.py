"""Shared content-extraction utility.

Gemini's chat API sometimes returns a list of content blocks (dicts with
a ``"text"`` key) instead of a plain string.  Three different call-sites
previously handled this inline with slightly different implementations.

This module consolidates all three into one canonical ``extract_text``
function so a format change is patched in one place.
"""

from __future__ import annotations


def extract_text(content: object) -> str:
    """Convert Gemini's content-block format into a plain string.

    Handles:
        * ``str`` — returned as-is.
        * ``list[dict]`` — joins the ``"text"`` fields, skipping
          non-dict items and dicts without a ``"text"`` key.
        * ``None`` — returns ``""``.
        * Anything else — converted via ``str()``.

    Args:
        content: Raw LLM response content (string, list, or other).

    Returns:
        A plain text string.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content)
