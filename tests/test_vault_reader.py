import httpx
import pytest

from device_command_proxy.vault_reader import VaultKv2Reader


def _reader_with_secret(secret):
    def handler(request):
        assert request.url.path == "/v1/secret/data/network/demo-lab/frr-readonly"
        return httpx.Response(200, json={"data": {"data": secret}})

    client = httpx.Client(base_url="http://vault", transport=httpx.MockTransport(handler))
    return VaultKv2Reader(client=client)


def test_read_returns_kv2_secret_data():
    reader = _reader_with_secret({"username": "diag", "authentication_type": "password"})

    secret = reader.read("network/demo-lab/frr-readonly")

    assert secret == {"username": "diag", "authentication_type": "password"}


def test_read_raises_when_response_has_no_secret_data():
    reader = _reader_with_secret(None)

    with pytest.raises(ValueError):
        reader.read("network/demo-lab/frr-readonly")


def test_injected_client_is_not_closed_by_reader():
    closed = []

    class TrackingClient(httpx.Client):
        def close(self):
            closed.append(True)
            super().close()

    client = TrackingClient(base_url="http://vault")
    reader = VaultKv2Reader(client=client)

    reader.close()

    assert closed == []


def test_base_url_mode_sends_configured_vault_token():
    reader = VaultKv2Reader(base_url="https://vault.internal:8200", token="s.abc123")

    assert reader._client.headers["x-vault-token"] == "s.abc123"
    assert str(reader._client.base_url) == "https://vault.internal:8200"


def test_base_url_mode_without_token_sends_no_vault_token_header():
    reader = VaultKv2Reader(base_url="https://vault.internal:8200")

    assert "x-vault-token" not in reader._client.headers


def test_default_mode_uses_unix_socket_transport_without_connecting():
    reader = VaultKv2Reader(socket_path="/run/vault-proxy/vault.sock")

    assert isinstance(reader._client._transport, httpx.HTTPTransport)


def test_base_url_mode_follows_ha_standby_redirects():
    reader = VaultKv2Reader(base_url="https://vault.internal:8200")

    assert reader._client.follow_redirects is True


@pytest.mark.parametrize(
    "mount", [" ", "   ", "\t", "\t/\t", "/ /", "/  /", " / / ", " /  / "]
)
def test_whitespace_only_mount_fails_at_startup(mount):
    # A boundary made only of whitespace and slashes must fail at startup
    # instead of becoming a percent-encoded Vault mount on the first read.
    with pytest.raises(ValueError, match="mount"):
        VaultKv2Reader(base_url="https://vault.internal:8200", token="t", mount=mount)


def test_mount_with_surrounding_whitespace_is_trimmed():
    reader = VaultKv2Reader(base_url="https://vault.internal:8200", token="t", mount=" kv ")

    assert reader._mount == "kv"


def test_mount_with_surrounding_whitespace_and_slashes_is_trimmed():
    # Boundary whitespace and slashes must not leak into the Vault URL.
    reader = VaultKv2Reader(base_url="https://vault.internal:8200", token="t", mount=" /kv/ ")

    assert reader._mount == "kv"
