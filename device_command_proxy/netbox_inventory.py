"""Live NetBox inventory resolution."""

from __future__ import annotations

import ipaddress

import httpx

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError


class NetBoxInventoryProvider:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout_sec: float = 3.0,
        client: httpx.Client | None = None,
    ):
        authorization_scheme = "Bearer" if token.startswith("nbt_") else "Token"
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"{authorization_scheme} {token}"},
            timeout=timeout_sec,
        )
        self._owns_client = client is None

    def get_device(self, device_name: str) -> DeviceProfile:
        try:
            device_response = self._client.get(
                "/api/dcim/devices/",
                params={"name": device_name, "limit": 2},
            )
            device_response.raise_for_status()
            devices = device_response.json().get("results", [])
            if len(devices) != 1 or devices[0].get("name") != device_name:
                raise ExecutionError(ErrorCode.DEVICE_NOT_FOUND, "device not found")
            device = devices[0]
            interface_response = self._client.get(
                "/api/dcim/interfaces/",
                params={"device_id": device["id"], "limit": 100},
            )
            interface_response.raise_for_status()
            interfaces = frozenset(
                interface["name"]
                for interface in interface_response.json().get("results", [])
            )
            return DeviceProfile(
                name=device_name,
                host=self._management_host(device),
                port=int(device.get("custom_fields", {}).get("ssh_port", 22)),
                platform=(device.get("platform") or {}).get("slug", ""),
                credential_profile=device.get("custom_fields", {}).get(
                    "credential_profile", ""
                ),
                interfaces=interfaces,
            )
        except ExecutionError:
            raise
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
        ) as exception:
            raise ExecutionError(
                ErrorCode.INVENTORY_UNAVAILABLE,
                "live inventory is unavailable or invalid",
            ) from exception

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _management_host(self, device: dict) -> str:
        address = (device.get("primary_ip4") or {}).get("address")
        if not isinstance(address, str):
            raise ValueError("device has no primary IPv4 address")
        host = ipaddress.ip_interface(address).ip
        return str(host)
