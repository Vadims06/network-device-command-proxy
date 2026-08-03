"""Vendor-neutral ephemeral private-key file lifecycle and SSH host-key trust."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Iterator

from device_command_proxy.contracts import DeviceCredentials


KNOWN_HOSTS_FILE_ENV = "SSH_KNOWN_HOSTS_FILE"
PRIVATE_KEY_DIRECTORY_ENV = "SSH_PRIVATE_KEY_DIRECTORY"
SSH_CLIENT = "ssh"
HOST_KEY_SCANNER = "ssh-keyscan"


def runtime_path_from_environment(variable_name: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if not value:
        raise ValueError(f"{variable_name} is required")
    return value


def verify_prerequisites(
    *,
    known_hosts_file: str | None = None,
    private_key_directory: str | None = None,
) -> None:
    """Fail at startup on local setup faults that otherwise look like a dead device.

    A missing host-key scanner or an unwritable directory raises OSError deep
    in the connection path, where it is caught alongside a genuine transport
    failure and reported as device_unreachable on every device. Checking here
    turns a misleading per-device error into one startup message.

    The private-key directory is checked when the caller has selected
    environment-backed private-key authentication.
    """
    known_hosts_file = known_hosts_file or os.environ.get(KNOWN_HOSTS_FILE_ENV, "").strip() or None
    # ssh-keyscan is needed only when the operator opts into host-key pinning.
    # Scrapli's system transport still invokes the ssh binary in either mode.
    if shutil.which(SSH_CLIENT) is None:
        raise ValueError(
            f"{SSH_CLIENT} is required to connect to devices: install openssh-client"
        )
    if known_hosts_file is None:
        if private_key_directory is not None:
            _verify_writable(Path(private_key_directory), "ephemeral private keys")
        return
    if shutil.which(HOST_KEY_SCANNER) is None:
        raise ValueError(
            f"{HOST_KEY_SCANNER} is required to learn device host keys: "
            f"install openssh-client"
        )
    known_hosts_path = Path(known_hosts_file)
    if known_hosts_path.exists():
        # An existing trust store only needs to be readable and appendable.
        # Its parent may intentionally prevent replacement of the file.
        _verify_appendable_if_it_exists(known_hosts_path)
    else:
        _verify_writable(known_hosts_path.parent, "the SSH known_hosts file")
    if private_key_directory is not None:
        _verify_writable(Path(private_key_directory), "ephemeral private keys")


def _verify_writable(directory: Path, purpose: str) -> None:
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        # A real create/delete rather than os.access(): the answer must match
        # what the connection path will actually be allowed to do.
        file_descriptor, probe_path = tempfile.mkstemp(dir=directory)
        os.close(file_descriptor)
        os.unlink(probe_path)
    except OSError as exception:
        raise ValueError(
            f"{directory} must exist and be writable by the user running the "
            f"service; it holds {purpose} ({exception}). "
            f"Fix: mkdir -p {directory} && chown $(id -u):$(id -g) {directory}"
        ) from exception


def _verify_appendable_if_it_exists(path: Path) -> None:
    if not path.exists():
        return
    try:
        # Append mode alone does not prove the read that ensure_host_key()
        # performs first; a+ checks both permissions in one operation.
        with open(path, "a+", encoding="utf-8"):
            pass
    except OSError as exception:
        raise ValueError(
            f"{path} exists but is not readable or writable by the user running the "
            f"service ({exception}). "
            f"Fix: chown $(id -u):$(id -g) {path}"
        ) from exception


@contextmanager
def authentication_options(
    credentials: DeviceCredentials,
    *,
    private_key_directory: str | None = None,
) -> Iterator[dict[str, str]]:
    if credentials.authentication_type == "password":
        yield {"auth_password": credentials.password or ""}
        return

    directory = Path(
        private_key_directory
        if private_key_directory is not None
        else runtime_path_from_environment(PRIVATE_KEY_DIRECTORY_ENV)
    )
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    file_descriptor, private_key_path = tempfile.mkstemp(
        prefix="device-key-",
        dir=directory,
        text=True,
    )
    # OpenSSH looks for "<identity>-cert.pub" beside the key it was given, so
    # writing the certificate there is what makes CA-signed auth work; there
    # is no separate option to pass it through.
    certificate_path = Path(f"{private_key_path}-cert.pub")
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as private_key_file:
            private_key_file.write(credentials.private_key or "")
        if credentials.ssh_certificate:
            certificate_path.write_text(credentials.ssh_certificate, encoding="utf-8")
            certificate_path.chmod(0o600)
        yield {
            "auth_private_key": private_key_path,
            "auth_private_key_passphrase": credentials.private_key_passphrase or "",
        }
    finally:
        Path(private_key_path).unlink(missing_ok=True)
        certificate_path.unlink(missing_ok=True)


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
