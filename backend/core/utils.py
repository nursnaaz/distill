from __future__ import annotations
"""Shared utility helpers used across backend services."""

import re

# JSON escape sequences that are valid per the spec
_VALID_JSON_ESCAPES = set('"\\bfnrt/')


def extract_json(text: str) -> str:
    """Strip markdown code fences, fix escape errors, and locate embedded JSON objects."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Fix invalid backslash escapes the LLM sometimes emits (e.g. \s, \p, \:).
    text = re.sub(
        r'\\([^"\\/bfnrtu])',
        lambda m: '\\\\' + m.group(1),
        text,
    )

    # If the model returned prose before/after the JSON, extract the JSON object.
    if not text.startswith('{'):
        start = text.find('{')
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return text
