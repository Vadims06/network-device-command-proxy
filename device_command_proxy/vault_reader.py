"""Minimal KV v2 reader, reachable either via a local Vault Proxy Unix socket
(a sidecar that resolves AppRole auth for us) or directly
over HTTP(S) with a Vault token (the standalone case, no Vault Proxy sidecar
required).
"""

from __future__ import annotations

from typing import Any, Mapping

import httpx


class VaultKv2Reader:
    def __init__(
        self,
        *,
        socket_path: str = "/run/vault-proxy/vault.sock",
        base_url: str | None = None,
        token: str | None = None,
        mount: str = "secret",
        timeout_sec: float = 3.0,
        client: httpx.Client | None = None,
    ):
        # Remove all supported boundary whitespace and slashes before checking
        # the mount, so tabs and slash-only values fail at startup.
        mount = mount.strip(" \t\r\n\v\f/")
        if not mount:
            raise ValueError("mount is required")
        if client is not None:
            self._client = client
            self._owns_client = False
        elif base_url is not None:
            headers = {"X-Vault-Token": token} if token else {}
            self._client = httpx.Client(
                base_url=base_url.rstrip("/"),
                headers=headers,
                timeout=timeout_sec,
                # Vault HA standbys answer with a 307 to the active node.
                follow_redirects=True,
            )
            self._owns_client = True
        else:
            transport = httpx.HTTPTransport(uds=socket_path)
            self._client = httpx.Client(
                transport=transport,
                base_url="http://vault-proxy",
                timeout=timeout_sec,
            )
            self._owns_client = True
        self._mount = mount

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
        if self._owns_client:
            self._client.close()
