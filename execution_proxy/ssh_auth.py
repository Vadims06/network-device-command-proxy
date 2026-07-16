"""Vendor-neutral ephemeral private-key file lifecycle."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
from typing import Iterator

from execution_proxy.contracts import DeviceCredentials


@contextmanager
def authentication_options(
    credentials: DeviceCredentials,
    *,
    private_key_directory: str = "/run/execution-proxy",
) -> Iterator[dict[str, str]]:
    if credentials.authentication_type == "password":
        yield {"auth_password": credentials.password or ""}
        return

    directory = Path(private_key_directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_descriptor, private_key_path = tempfile.mkstemp(
        prefix="device-key-",
        dir=directory,
        text=True,
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as private_key_file:
            private_key_file.write(credentials.private_key or "")
        yield {
            "auth_private_key": private_key_path,
            "auth_private_key_passphrase": credentials.private_key_passphrase or "",
        }
    finally:
        Path(private_key_path).unlink(missing_ok=True)
