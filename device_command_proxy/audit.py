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
from device_command_proxy.validation import (
    LOGGABLE_ARGUMENT_KEYS,
    is_valid_interface_name,
    is_valid_prefix,
)

_logger = logging.getLogger("device_command_proxy.audit")

# One predicate per loggable key: a value that fails its own key's check is
# exactly the case validate_arguments() would reject too, so logging it
# verbatim would put an unvalidated (and possibly attacker-supplied) string
# in the log under the guise of a real argument.
_ARGUMENT_VALIDATORS = {
    "interface": is_valid_interface_name,
    "prefix": is_valid_prefix,
}


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
        # Filtered to the known-legitimate keys with values that pass that
        # key's own validity check, not logged verbatim: an authenticated
        # caller can put anything under an allowed key (e.g.
        # {"prefix": "supersecret"}), and validate_arguments() rejecting the
        # request does not stop this record from being written with whatever
        # they sent.
        "arguments": {
            key: value
            for key, value in arguments.items()
            if key in LOGGABLE_ARGUMENT_KEYS and _ARGUMENT_VALIDATORS[key](value)
        },
        "platform": result.platform,
        "duration_ms": result.duration_ms,
        "status": result.status,
    }
    if result.error is not None:
        entry["error_code"] = result.error.code.value
    _logger.info(json.dumps(entry, sort_keys=True))
