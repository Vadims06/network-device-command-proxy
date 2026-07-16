import pytest

from execution_proxy.contracts import ErrorCode, ExecutionError
from execution_proxy.credential_provider import VaultCredentialProvider


PROFILE_PATHS = {
    "demo-frr-readonly": "network/demo/demo-lab/frr-readonly",
    "demo-junos-readonly": "network/demo/demo-lab/junos-readonly",
}


class MutableClock:
    def __init__(self):
        self.current_time = 100.0

    def __call__(self):
        return self.current_time


def test_fixed_profile_mapping_and_cache():
    secret_paths = []

    def read_secret(secret_path):
        secret_paths.append(secret_path)
        return {
            "username": "diag",
            "authentication_type": "password",
            "password": "secret-value",
        }

    provider = VaultCredentialProvider(
        read_secret,
        PROFILE_PATHS,
        cache_ttl_sec=60,
    )

    first_credentials = provider.get_credentials("demo-frr-readonly")
    second_credentials = provider.get_credentials("demo-frr-readonly")

    assert first_credentials is second_credentials
    assert secret_paths == ["network/demo/demo-lab/frr-readonly"]


def test_unknown_profile_fails_without_vault_read():
    secret_paths = []
    provider = VaultCredentialProvider(
        lambda secret_path: secret_paths.append(secret_path),
        PROFILE_PATHS,
    )

    with pytest.raises(ExecutionError) as raised_error:
        provider.get_credentials("../../ticketing")

    assert raised_error.value.code == ErrorCode.CREDENTIAL_UNAVAILABLE
    assert secret_paths == []


def test_expired_cache_fails_closed_when_vault_is_unavailable():
    clock = MutableClock()
    vault_available = True

    def read_secret(_secret_path):
        if not vault_available:
            raise ConnectionError("socket unavailable")
        return {
            "username": "diag",
            "authentication_type": "password",
            "password": "secret-value",
        }

    provider = VaultCredentialProvider(
        read_secret,
        PROFILE_PATHS,
        cache_ttl_sec=60,
        clock=clock,
    )
    provider.get_credentials("demo-frr-readonly")

    clock.current_time = 161.0
    vault_available = False
    with pytest.raises(ExecutionError) as raised_error:
        provider.get_credentials("demo-frr-readonly")

    assert raised_error.value.code == ErrorCode.CREDENTIAL_UNAVAILABLE
    assert str(raised_error.value) == "credentials are unavailable"


def test_evict_forces_next_read():
    read_count = 0

    def read_secret(_secret_path):
        nonlocal read_count
        read_count += 1
        return {
            "username": "diag",
            "authentication_type": "password",
            "password": f"secret-{read_count}",
        }

    provider = VaultCredentialProvider(read_secret, PROFILE_PATHS)
    provider.get_credentials("demo-frr-readonly")
    provider.evict("demo-frr-readonly")
    credentials = provider.get_credentials("demo-frr-readonly")

    assert read_count == 2
    assert credentials.password == "secret-2"


def test_invalid_secret_does_not_leak_secret_value():
    provider = VaultCredentialProvider(
        lambda _secret_path: {
            "username": "diag",
            "authentication_type": "password",
            "password": "",
            "private_key": "sensitive-private-key",
        },
        PROFILE_PATHS,
    )

    with pytest.raises(ExecutionError) as raised_error:
        provider.get_credentials("demo-frr-readonly")

    assert str(raised_error.value) == "credential secret is invalid"
    assert "sensitive-private-key" not in str(raised_error.value)

