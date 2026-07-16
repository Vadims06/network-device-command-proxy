"""Structured audit logging for every executed device operation.

Never logs passwords, private keys, Vault paths/tokens, or raw command
output - only the fields the completion contract requires.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from device_command_proxy.contracts import DeviceResult

_logger = logging.getLogger("device_command_proxy.audit")


def record(
    result: DeviceResult,
    *,
    request_id: str,
    arguments: Mapping[str, Any],
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "request_id": request_id,
        "device": result.device,
        "operation": result.operation,
        "arguments": dict(arguments),
        "platform": result.platform,
        "duration_ms": result.duration_ms,
        "status": result.status,
    }
    if result.error is not None:
        entry["error_code"] = result.error.code.value
    _logger.info(json.dumps(entry, sort_keys=True))
