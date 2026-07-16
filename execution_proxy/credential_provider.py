"""Vault-backed credential resolution with a short in-memory cache."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Mapping

from execution_proxy.contracts import (
    CredentialProvider,
    DeviceCredentials,
    ErrorCode,
    ExecutionError,
)


SecretReader = Callable[[str], Mapping[str, Any]]
Clock = Callable[[], float]


@dataclass(frozen=True)
class _CachedCredentials:
    credentials: DeviceCredentials
    expires_at: float


class VaultCredentialProvider(CredentialProvider):
    def __init__(
        self,
        secret_reader: SecretReader,
        profile_paths: Mapping[str, str],
        *,
        cache_ttl_sec: float = 60.0,
        clock: Clock = monotonic,
    ):
        if cache_ttl_sec <= 0 or cache_ttl_sec > 300:
            raise ValueError("cache_ttl_sec must be between 0 and 300")
        self._secret_reader = secret_reader
        self._profile_paths = dict(profile_paths)
        self._cache_ttl_sec = cache_ttl_sec
        self._clock = clock
        self._cache: dict[str, _CachedCredentials] = {}

    def get_credentials(self, credential_profile: str) -> DeviceCredentials:
        current_time = self._clock()
        cached_credentials = self._cache.get(credential_profile)
        if cached_credentials is not None and cached_credentials.expires_at > current_time:
            return cached_credentials.credentials

        self._cache.pop(credential_profile, None)
        secret_path = self._profile_paths.get(credential_profile)
        if secret_path is None:
            raise ExecutionError(
                ErrorCode.CREDENTIAL_UNAVAILABLE,
                "credential profile is not allowed",
            )

        try:
            secret = self._secret_reader(secret_path)
            credentials = _credentials_from_secret(secret)
        except ExecutionError:
            raise
        except Exception as exception:
            raise ExecutionError(
                ErrorCode.CREDENTIAL_UNAVAILABLE,
                "credentials are unavailable",
            ) from exception

        self._cache[credential_profile] = _CachedCredentials(
            credentials=credentials,
            expires_at=current_time + self._cache_ttl_sec,
        )
        return credentials

    def evict(self, credential_profile: str) -> None:
        self._cache.pop(credential_profile, None)


def _credentials_from_secret(secret: Mapping[str, Any]) -> DeviceCredentials:
    username = secret.get("username")
    authentication_type = secret.get("authentication_type")
    if not isinstance(username, str) or not username:
        raise ExecutionError(
            ErrorCode.CREDENTIAL_UNAVAILABLE,
            "credential secret is invalid",
        )
    if not isinstance(authentication_type, str):
        raise ExecutionError(
            ErrorCode.CREDENTIAL_UNAVAILABLE,
            "credential secret is invalid",
        )

    try:
        return DeviceCredentials(
            username=username,
            authentication_type=authentication_type,
            password=_optional_string(secret.get("password")),
            private_key=_optional_string(secret.get("private_key")),
            private_key_passphrase=_optional_string(
                secret.get("private_key_passphrase")
            ),
            ssh_certificate=_optional_string(secret.get("ssh_certificate")),
        )
    except ValueError as exception:
        raise ExecutionError(
            ErrorCode.CREDENTIAL_UNAVAILABLE,
            "credential secret is invalid",
        ) from exception


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ExecutionError(
            ErrorCode.CREDENTIAL_UNAVAILABLE,
            "credential secret is invalid",
        )
    return value

