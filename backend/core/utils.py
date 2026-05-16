from __future__ import annotations
"""Shared utility helpers used across backend services."""

import re

# JSON escape sequences that are valid per the spec
_VALID_JSON_ESCAPES = set('"\\bfnrt/')


def extract_json(text: str) -> str:
    """Strip thinking blocks, markdown fences, extra prose, and fix common LLM JSON escape errors."""
    text = text.strip()
    # Strip <think>...</think> blocks emitted by reasoning models (e.g. Qwen3, DeepSeek-R1)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # If the model added prose before/after the JSON, extract the outermost { ... }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    # Fix invalid backslash escapes the LLM sometimes emits (e.g. \s, \p, \:).
    text = re.sub(
        r'\\([^"\\/bfnrtu])',
        lambda m: '\\\\' + m.group(1),
        text,
    )
    return text
