"""Shared behavior for JSON config files loaded from disk."""

from __future__ import annotations

from typing import Any


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """json.loads silently keeps the last of two duplicate keys.

    Passed as json.loads's object_pairs_hook, so every JSON object in the
    document is checked, not just the top level. A repeated key is usually a
    copy-paste or merge error, and the value it silently overrides could be
    the one an operator meant to keep.
    """
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key '{key}' in JSON file")
        result[key] = value
    return result
