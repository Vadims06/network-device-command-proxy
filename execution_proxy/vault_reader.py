"""Minimal KV v2 reader through a local Vault Proxy Unix socket."""

from __future__ import annotations

from typing import Any, Mapping

import httpx


class VaultKv2Reader:
    def __init__(
        self,
        *,
        socket_path: str = "/run/vault-proxy/vault.sock",
        mount: str = "secret",
        timeout_sec: float = 3.0,
    ):
        transport = httpx.HTTPTransport(uds=socket_path)
        self._client = httpx.Client(
            transport=transport,
            base_url="http://vault-proxy",
            timeout=timeout_sec,
        )
        self._mount = mount.strip("/")

    def read(self, secret_path: str) -> Mapping[str, Any]:
        response = self._client.get(
            f"/v1/{self._mount}/data/{secret_path.lstrip('/')}"
        )
        response.raise_for_status()
        payload = response.json()
        secret = payload.get("data", {}).get("data")
        if not isinstance(secret, dict):
            raise ValueError("Vault KV v2 response has no secret data")
        return secret

    def close(self) -> None:
        self._client.close()

