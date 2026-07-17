"""Vendor-neutral ephemeral private-key file lifecycle and SSH host-key trust."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Callable, Iterator

from device_command_proxy.contracts import DeviceCredentials


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


def ensure_host_key(
    host: str,
    port: int,
    known_hosts_file: str,
    *,
    scan: Callable[[], str] | None = None,
) -> None:
    """Learn a device's SSH host key on first contact (accept-new semantics).

    A device already present in known_hosts is left untouched, so a changed
    key on a known device still fails strict host-key checking as before.
    """
    path = Path(known_hosts_file)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.touch(exist_ok=True)

    host_field = host if port == 22 else f"[{host}]:{port}"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.split(" ", 1)[0] == host_field:
            return

    scan_output = scan() if scan is not None else _scan_host_key(host, port)
    if not scan_output:
        return
    # ponytail: concurrent first contacts may append duplicate lines; OpenSSH
    # matches the first entry for a host, so duplicates are harmless.
    with open(path, "a", encoding="utf-8") as known_hosts:
        known_hosts.write(scan_output)


def _scan_host_key(host: str, port: int) -> str:
    result = subprocess.run(
        ["ssh-keyscan", "-T", "5", "-p", str(port), host],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout
