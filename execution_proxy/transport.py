"""Scrapli driver lifecycle and ephemeral private-key handling."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
from typing import Iterator

from scrapli.driver.core import JunosDriver
from scrapli.driver.generic import GenericDriver

from execution_proxy.contracts import DeviceCredentials, DeviceProfile


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


@contextmanager
def create_frr_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str = "/etc/execution-proxy/known_hosts",
    private_key_directory: str = "/run/execution-proxy",
) -> Iterator[GenericDriver]:
    with authentication_options(
        credentials,
        private_key_directory=private_key_directory,
    ) as authentication:
        driver = GenericDriver(
            host=device.host,
            port=device.port,
            auth_username=credentials.username,
            auth_strict_key=True,
            ssh_known_hosts_file=known_hosts_file,
            timeout_socket=5.0,
            timeout_transport=10.0,
            timeout_ops=10.0,
            transport="system",
            comms_prompt_pattern=r"^[a-zA-Z0-9_.-]+[>#]\s*$",
            channel_log=False,
            **authentication,
        )
        try:
            driver.open()
            yield driver
        finally:
            if driver.isalive():
                driver.close()


@contextmanager
def create_junos_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str = "/etc/execution-proxy/known_hosts",
    private_key_directory: str = "/run/execution-proxy",
) -> Iterator[JunosDriver]:
    with authentication_options(
        credentials,
        private_key_directory=private_key_directory,
    ) as authentication:
        driver = JunosDriver(
            host=device.host,
            port=device.port,
            auth_username=credentials.username,
            auth_strict_key=True,
            ssh_known_hosts_file=known_hosts_file,
            timeout_socket=5.0,
            timeout_transport=10.0,
            timeout_ops=10.0,
            transport="system",
            channel_log=False,
            **authentication,
        )
        try:
            driver.open()
            yield driver
        finally:
            if driver.isalive():
                driver.close()
