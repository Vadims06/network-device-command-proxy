"""Environment wiring for the network-device-command-proxy service."""

from __future__ import annotations

from device_command_proxy.api import create_app
from device_command_proxy.config import (
    build_credentials,
    build_env_credentials,
    build_inventory,
    configure_logging,
    required_env,
)
from device_command_proxy.executor import BatchExecutor
from device_command_proxy.platforms import PLATFORMS, UNSUPPORTED_FIELDS
from device_command_proxy.ssh_auth import (
    PRIVATE_KEY_DIRECTORY_ENV,
    runtime_path_from_environment,
    verify_prerequisites,
)


def build_app():
    configure_logging()
    # Resolved once, ahead of the SSH prerequisite check: env-credentials
    # mode applies one DeviceCredentials to every device, so whether the
    # private-key directory is needed is already known here. Passed on to
    # build_credentials() below rather than resolved twice.
    device_credentials = build_env_credentials()
    # Before anything else: missing SSH tooling or an unwritable runtime
    # directory would otherwise surface as device_unreachable on every device.
    private_key_directory = None
    if (
        device_credentials is not None
        and device_credentials.authentication_type == "private_key"
    ):
        private_key_directory = runtime_path_from_environment(
            PRIVATE_KEY_DIRECTORY_ENV
        )
    verify_prerequisites(private_key_directory=private_key_directory)
    # Credentials first: which profile names an inventory may reference
    # depends on the source, and the static inventory checks them while loading.
    credentials, credential_profiles = build_credentials(device_credentials)
    inventory = build_inventory(credential_profiles)

    executor = BatchExecutor(inventory, credentials, PLATFORMS, UNSUPPORTED_FIELDS)
    return create_app(
        executor,
        required_env("EXECUTION_PROXY_TOKEN", "bearer token callers must present"),
    )


app = build_app()
