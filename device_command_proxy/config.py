"""Environment-driven selection of inventory, credentials, and logging.

Kept separate from main.py so these can be imported and tested without
triggering main.py's module-level `app = build_app()` side effect.

Every misconfiguration raises here, at startup, rather than surfacing later as
a per-device error on a request that looked well-formed.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterable

from device_command_proxy.contracts import CredentialProvider, DeviceCredentials
from device_command_proxy.credential_provider import VaultCredentialProvider
from device_command_proxy.env_credentials import EnvCredentialProvider
from device_command_proxy.json_files import reject_duplicate_keys
from device_command_proxy.netbox_inventory import NetBoxInventoryProvider
from device_command_proxy.platforms import PLATFORMS
from device_command_proxy.static_inventory import StaticInventoryProvider
from device_command_proxy.vault_reader import VaultKv2Reader


DEFAULT_PROFILE_PATHS = {
    "demo-frr-readonly": "network/demo/demo-lab/frr-readonly",
    "demo-junos-readonly": "network/demo/demo-lab/junos-readonly",
}

DEFAULT_VAULT_PROXY_SOCKET_PATH = "/run/vault-proxy/vault.sock"


def configure_logging() -> None:
    """Without this every audit record and diagnostic is silently discarded.

    uvicorn configures only its own loggers and leaves the root logger without
    a handler, so anything this package logs below WARNING never reaches
    stdout - including the audit entry written for each executed operation.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    logger = logging.getLogger("device_command_proxy")
    # Idempotent: uvicorn --reload imports the app module more than once.
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.propagate = False


def required_env(name: str, reason: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required: {reason}")
    return value


def build_inventory(credential_profiles: Iterable[str] | None):
    static_inventory_path = os.environ.get("STATIC_INVENTORY_PATH")
    if static_inventory_path:
        return StaticInventoryProvider.from_file(
            static_inventory_path,
            supported_platforms=PLATFORMS,
            credential_profiles=credential_profiles,
        )
    return NetBoxInventoryProvider(
        required_env(
            "NETBOX_URL", "set STATIC_INVENTORY_PATH instead to run without NetBox"
        ),
        required_env(
            "NETBOX_TOKEN", "set STATIC_INVENTORY_PATH instead to run without NetBox"
        ),
    )


def build_env_credentials() -> DeviceCredentials | None:
    """One credential set for every device, or None when env mode is not chosen.

    DEVICE_USERNAME is the switch: without it the service keeps requiring a
    Vault, so an existing deployment cannot silently fall back to weaker
    credentials because a variable happened to be set.
    """
    username = os.environ.get("DEVICE_USERNAME")
    if username is None:
        return None
    username = username.strip()
    if not username:
        # A whitespace-only value is truthy, so a bare "not username" check
        # would select this mode and hand every device an unusable login
        # instead of the Vault the docs say an unset variable keeps requiring.
        raise ValueError("DEVICE_USERNAME must not be empty or whitespace-only")

    password = os.environ.get("DEVICE_PASSWORD")
    private_key_file = os.environ.get("DEVICE_PRIVATE_KEY_FILE")
    if bool(password) == bool(private_key_file):
        raise ValueError(
            "DEVICE_USERNAME requires exactly one of DEVICE_PASSWORD or "
            "DEVICE_PRIVATE_KEY_FILE"
        )
    if password:
        return DeviceCredentials(
            username=username,
            authentication_type="password",
            password=password,
        )
    return DeviceCredentials(
        username=username,
        authentication_type="private_key",
        private_key=_read_credential_file(
            private_key_file, "DEVICE_PRIVATE_KEY_FILE"
        ),
        private_key_passphrase=os.environ.get("DEVICE_PRIVATE_KEY_PASSPHRASE") or None,
        ssh_certificate=_optional_credential_file("DEVICE_SSH_CERTIFICATE_FILE"),
    )


def _read_credential_file(path: str, name: str) -> str:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exception:
        raise ValueError(f"{name} cannot be read: {exception}") from exception
    if not content.strip():
        raise ValueError(f"{name} is empty: {path}")
    return content


def _optional_credential_file(name: str) -> str | None:
    path = os.environ.get(name)
    if not path:
        return None
    return _read_credential_file(path, name)


def build_credentials(
    device_credentials: DeviceCredentials | None = None,
) -> tuple[CredentialProvider, list[str] | None]:
    """Pick the credential source and report which profile names an inventory may use.

    None means the inventory's credential_profile has nothing to be checked
    against: env credentials apply to every device regardless of the name.

    device_credentials lets a caller pass an already-resolved value (main.py
    needs it before this call, to decide whether the private-key-directory
    startup check applies) instead of paying for build_env_credentials()'s
    file reads twice.
    """
    if device_credentials is None:
        device_credentials = build_env_credentials()
    if device_credentials is not None:
        return EnvCredentialProvider(device_credentials), None
    profile_paths = build_profile_paths()
    return (
        VaultCredentialProvider(build_vault_reader().read, profile_paths),
        list(profile_paths),
    )


def build_vault_reader() -> VaultKv2Reader:
    mount = os.environ.get("VAULT_KV_MOUNT", "secret")
    vault_address = os.environ.get("VAULT_ADDR")
    if vault_address:
        return VaultKv2Reader(
            base_url=vault_address,
            token=required_env("VAULT_TOKEN", "needed to authenticate to VAULT_ADDR"),
            mount=mount,
        )
    socket_path = os.environ.get(
        "VAULT_PROXY_SOCKET_PATH", DEFAULT_VAULT_PROXY_SOCKET_PATH
    )
    # Without this check an unconfigured Vault only shows up much later, as a
    # credential_unavailable on every device of an otherwise valid request.
    # Existence alone is not enough: a regular file or directory at this path
    # also builds a working-looking transport that can never connect.
    if not Path(socket_path).is_socket():
        raise ValueError(
            f"no credential source configured: set VAULT_ADDR and VAULT_TOKEN, "
            f"or run a Vault Proxy whose socket is at {socket_path} "
            f"(override with VAULT_PROXY_SOCKET_PATH), or set DEVICE_USERNAME "
            f"with DEVICE_PASSWORD or DEVICE_PRIVATE_KEY_FILE to run without a Vault"
        )
    return VaultKv2Reader(socket_path=socket_path, mount=mount)


def build_profile_paths() -> dict[str, str]:
    profile_paths_file = os.environ.get("PROFILE_PATHS_FILE")
    if not profile_paths_file:
        return DEFAULT_PROFILE_PATHS
    profile_paths = json.loads(
        Path(profile_paths_file).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    # Normalize before validation: a boundary made only of whitespace and
    # slashes is not a usable Vault path, and accepted padding would leak into
    # the request URL.
    if not isinstance(profile_paths, dict) or not profile_paths or not all(
        isinstance(name, str) and name.strip() and isinstance(path, str)
        for name, path in profile_paths.items()
    ):
        raise ValueError(
            "PROFILE_PATHS_FILE must map at least one non-empty profile name "
            "to a non-empty Vault path"
        )
    normalized_profile_paths = [
        (name.strip(), path.strip(" \t\r\n\v\f/"))
        for name, path in profile_paths.items()
    ]
    if not all(name and path for name, path in normalized_profile_paths):
        raise ValueError(
            "PROFILE_PATHS_FILE must map at least one non-empty profile name "
            "to a non-empty Vault path"
        )
    # "prod" and "prod " are distinct raw keys that collide after stripping.
    return reject_duplicate_keys(normalized_profile_paths)
