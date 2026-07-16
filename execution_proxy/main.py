"""Environment wiring for the execution-proxy service."""

from __future__ import annotations

import os

from execution_proxy.api import create_app
from execution_proxy.credential_provider import VaultCredentialProvider
from execution_proxy.executor import BatchExecutor
from execution_proxy.netbox_inventory import NetBoxInventoryProvider
from execution_proxy.platforms import PLATFORMS
from execution_proxy.vault_reader import VaultKv2Reader


PROFILE_PATHS = {
    "demo-frr-readonly": "network/demo/demo-lab/frr-readonly",
    "demo-junos-readonly": "network/demo/demo-lab/junos-readonly",
}


def build_app():
    inventory = NetBoxInventoryProvider(
        os.environ["NETBOX_URL"],
        os.environ["NETBOX_TOKEN"],
        os.environ["MANAGEMENT_CIDRS"].split(","),
    )
    vault_reader = VaultKv2Reader()
    credentials = VaultCredentialProvider(vault_reader.read, PROFILE_PATHS)

    executor = BatchExecutor(inventory, credentials, PLATFORMS)
    return create_app(executor, os.environ["EXECUTION_PROXY_TOKEN"])


app = build_app()
