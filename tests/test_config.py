import pytest

from device_command_proxy import config


def test_profile_paths_default_to_demo_lab_when_no_file_configured(monkeypatch):
    monkeypatch.delenv("PROFILE_PATHS_FILE", raising=False)

    assert config.build_profile_paths() == config.DEFAULT_PROFILE_PATHS


def test_profile_paths_are_loaded_from_configured_file(monkeypatch, tmp_path):
    profile_paths_file = tmp_path / "profile_paths.json"
    profile_paths_file.write_text(
        '{"prod-frr-readonly": "network/prod/frr-readonly"}', encoding="utf-8"
    )
    monkeypatch.setenv("PROFILE_PATHS_FILE", str(profile_paths_file))

    assert config.build_profile_paths() == {
        "prod-frr-readonly": "network/prod/frr-readonly"
    }


@pytest.mark.parametrize(
    "profile_paths_json",
    [
        '{"prod-frr-readonly": null}',
        '{"prod-frr-readonly": 123}',
        '{"prod-frr-readonly": []}',
        '{"prod-frr-readonly": ""}',
        '{"": "network/prod/frr-readonly"}',
        # Whitespace-only is "non-empty" by a bare truthiness check, but
        # still builds a request to a percent-encoded whitespace Vault path.
        '{"prod-frr-readonly": "   "}',
        '{"prod-frr-readonly": "/"}',
        '{"prod-frr-readonly": " / "}',
        '{"prod-frr-readonly": "/ /"}',
        '{"   ": "network/prod/frr-readonly"}',
        "[]",
        "{}",
    ],
)
def test_profile_paths_file_with_invalid_shape_fails_at_startup(
    monkeypatch, tmp_path, profile_paths_json
):
    profile_paths_file = tmp_path / "profile_paths.json"
    profile_paths_file.write_text(profile_paths_json, encoding="utf-8")
    monkeypatch.setenv("PROFILE_PATHS_FILE", str(profile_paths_file))

    with pytest.raises(ValueError):
        config.build_profile_paths()


def test_duplicate_profile_name_in_profile_paths_file_fails_at_startup(
    monkeypatch, tmp_path
):
    # json.loads keeps only the last of two duplicate keys, so a copy-paste
    # error could point a familiar profile name at the wrong Vault path
    # without any visible sign in the file's own structure.
    profile_paths_file = tmp_path / "profile_paths.json"
    profile_paths_file.write_text(
        '{"prod-frr-readonly": "network/prod/frr-readonly", '
        '"prod-frr-readonly": "network/prod/other-path"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("PROFILE_PATHS_FILE", str(profile_paths_file))

    with pytest.raises(ValueError, match="duplicate key 'prod-frr-readonly'"):
        config.build_profile_paths()


def test_profile_names_colliding_after_stripping_whitespace_fail_at_startup(
    monkeypatch, tmp_path
):
    # Two distinct raw keys that only collide once both are stripped would
    # otherwise silently pick whichever one dict iteration visits last.
    profile_paths_file = tmp_path / "profile_paths.json"
    profile_paths_file.write_text(
        '{"prod-frr-readonly": "network/prod/frr-readonly", '
        '"prod-frr-readonly ": "network/prod/other-path"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("PROFILE_PATHS_FILE", str(profile_paths_file))

    with pytest.raises(ValueError, match="duplicate key 'prod-frr-readonly'"):
        config.build_profile_paths()


def test_inventory_uses_static_file_when_configured(monkeypatch, tmp_path):
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        '{"router1": {"host": "172.21.20.11", "platform": "frr", '
        '"credential_profile": "demo-frr-readonly", "interfaces": []}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("STATIC_INVENTORY_PATH", str(inventory_path))

    inventory = config.build_inventory(["demo-frr-readonly"])

    assert inventory.get_device("router1").host == "172.21.20.11"


def test_inventory_falls_back_to_netbox_when_no_static_path_configured(monkeypatch):
    monkeypatch.delenv("STATIC_INVENTORY_PATH", raising=False)
    monkeypatch.setenv("NETBOX_URL", "http://netbox.invalid")
    monkeypatch.setenv("NETBOX_TOKEN", "test-token")

    from device_command_proxy.netbox_inventory import NetBoxInventoryProvider

    inventory = config.build_inventory(["demo-frr-readonly"])

    assert isinstance(inventory, NetBoxInventoryProvider)


def test_vault_reader_uses_http_when_vault_addr_configured(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.internal:8200")
    monkeypatch.setenv("VAULT_TOKEN", "s.abc123")

    reader = config.build_vault_reader()

    assert reader._client.headers["x-vault-token"] == "s.abc123"


def test_vault_reader_falls_back_to_socket_when_the_proxy_socket_exists(
    monkeypatch, tmp_path
):
    import socket

    socket_path = tmp_path / "vault.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_PROXY_SOCKET_PATH", str(socket_path))

    import httpx

    try:
        reader = config.build_vault_reader()
    finally:
        listener.close()

    assert isinstance(reader._client._transport, httpx.HTTPTransport)


def test_a_regular_file_where_the_vault_socket_belongs_fails_at_startup(
    monkeypatch, tmp_path
):
    # Existence alone would build a transport that can never connect.
    not_a_socket = tmp_path / "vault.sock"
    not_a_socket.touch()
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_PROXY_SOCKET_PATH", str(not_a_socket))

    with pytest.raises(ValueError, match="no credential source configured"):
        config.build_vault_reader()


def test_no_vault_connection_at_all_fails_at_startup_not_on_the_first_request(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_PROXY_SOCKET_PATH", str(tmp_path / "absent.sock"))

    with pytest.raises(ValueError, match="no credential source configured"):
        config.build_vault_reader()


def test_kv_mount_is_configurable_for_a_non_default_vault_layout(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.internal:8200")
    monkeypatch.setenv("VAULT_TOKEN", "s.abc123")
    monkeypatch.setenv("VAULT_KV_MOUNT", "kv")

    assert config.build_vault_reader()._mount == "kv"


def test_kv_mount_defaults_to_secret(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.internal:8200")
    monkeypatch.setenv("VAULT_TOKEN", "s.abc123")
    monkeypatch.delenv("VAULT_KV_MOUNT", raising=False)

    assert config.build_vault_reader()._mount == "secret"


@pytest.mark.parametrize(
    "name", ["NETBOX_URL", "NETBOX_TOKEN", "EXECUTION_PROXY_TOKEN"]
)
def test_missing_required_env_names_itself_instead_of_raising_keyerror(
    monkeypatch, name
):
    monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match=name):
        config.required_env(name, "needed")


@pytest.mark.parametrize("vault_token", [None, ""])
def test_vault_addr_without_token_fails_at_startup(monkeypatch, vault_token):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.internal:8200")
    if vault_token is None:
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
    else:
        monkeypatch.setenv("VAULT_TOKEN", vault_token)

    with pytest.raises(ValueError):
        config.build_vault_reader()
