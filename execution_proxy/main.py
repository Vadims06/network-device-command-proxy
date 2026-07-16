"""Environment wiring for the execution-proxy service."""

from __future__ import annotations

import os

from execution_proxy.adapters.frr import FrrAdapter
from execution_proxy.adapters.junos import JunosAdapter
from execution_proxy.api import create_app
from execution_proxy.credential_provider import VaultCredentialProvider
from execution_proxy.executor import BatchExecutor
from execution_proxy.netbox_inventory import NetBoxInventoryProvider
from execution_proxy.transport import create_frr_driver, create_junos_driver
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

    def create_frr_adapter(device, device_credentials):
        return FrrAdapter(
            lambda: create_frr_driver(device, device_credentials)
        )

    def create_junos_adapter(device, device_credentials):
        return JunosAdapter(
            lambda: create_junos_driver(device, device_credentials)
        )

    executor = BatchExecutor(
        inventory,
        credentials,
        {"frr": create_frr_adapter, "junos": create_junos_adapter},
    )
    return create_app(executor, os.environ["EXECUTION_PROXY_TOKEN"])


app = build_app()
