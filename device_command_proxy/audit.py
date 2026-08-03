"""Structured audit logging for every executed device operation.

Never logs passwords, private keys, Vault paths/tokens, or raw command
output - only the fields the completion contract requires.
"""

from __future__ import annotations

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

from device_command_proxy.contracts import DeviceResult
from device_command_proxy.validation import LOGGABLE_ARGUMENT_KEYS

_logger = logging.getLogger("device_command_proxy.audit")

def _logged_request_id(request_id: str) -> str:
    if not request_id:
        return ""
    return hashlib.sha256(request_id.encode("utf-8")).hexdigest()


def record(
    result: DeviceResult,
    *,
    request_id: str,
    arguments: Mapping[str, Any],
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "request_id": _logged_request_id(request_id),
        "device": result.device,
        "operation": result.operation,
        # Keep argument names for operation visibility, but never copy values
        # from an authenticated request into logs.
        "arguments": {
            key: "[redacted]"
            for key, value in arguments.items()
            if key in LOGGABLE_ARGUMENT_KEYS
        },
        "platform": result.platform,
        "duration_ms": result.duration_ms,
        "status": result.status,
    }
    if result.error is not None:
        entry["error_code"] = result.error.code.value
    _logger.info(json.dumps(entry, sort_keys=True))
