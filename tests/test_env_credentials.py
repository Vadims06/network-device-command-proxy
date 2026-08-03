import pytest

from device_command_proxy import config
from device_command_proxy.env_credentials import EnvCredentialProvider


@pytest.fixture(autouse=True)
def clear_device_env(monkeypatch):
    for name in (
        "DEVICE_USERNAME",
        "DEVICE_PASSWORD",
        "DEVICE_PRIVATE_KEY_FILE",
        "DEVICE_PRIVATE_KEY_PASSPHRASE",
        "DEVICE_SSH_CERTIFICATE_FILE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_no_env_credentials_without_device_username(monkeypatch):
    # A stray DEVICE_PASSWORD must not switch an existing Vault deployment
    # over to weaker credentials.
    monkeypatch.setenv("DEVICE_PASSWORD", "leftover")

    assert config.build_env_credentials() is None


@pytest.mark.parametrize("username", ["", "   ", "\t"])
def test_whitespace_only_device_username_fails_at_startup(monkeypatch, username):
    # "   " is truthy, so a bare "not username" check would select
    # env-credentials mode and hand every device this unusable login instead
    # of the Vault an unset variable keeps requiring.
    monkeypatch.setenv("DEVICE_USERNAME", username)
    monkeypatch.setenv("DEVICE_PASSWORD", "s3cret")

    with pytest.raises(ValueError, match="DEVICE_USERNAME"):
        config.build_env_credentials()


def test_device_username_with_surrounding_whitespace_is_trimmed(monkeypatch):
    monkeypatch.setenv("DEVICE_USERNAME", " diag ")
    monkeypatch.setenv("DEVICE_PASSWORD", "s3cret")

    assert config.build_env_credentials().username == "diag"


def test_password_credentials_are_read_from_env(monkeypatch):
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PASSWORD", "s3cret")

    credentials = config.build_env_credentials()

    assert credentials.username == "diag"
    assert credentials.authentication_type == "password"
    assert credentials.password == "s3cret"


def test_private_key_credentials_are_read_from_the_referenced_file(
    monkeypatch, tmp_path
):
    key_file = tmp_path / "id_ed25519"
    key_file.write_text("PRIVATE KEY BODY", encoding="utf-8")
    certificate_file = tmp_path / "id_ed25519-cert.pub"
    certificate_file.write_text("CERT BODY", encoding="utf-8")
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PRIVATE_KEY_FILE", str(key_file))
    monkeypatch.setenv("DEVICE_PRIVATE_KEY_PASSPHRASE", "phrase")
    monkeypatch.setenv("DEVICE_SSH_CERTIFICATE_FILE", str(certificate_file))

    credentials = config.build_env_credentials()

    assert credentials.authentication_type == "private_key"
    assert credentials.private_key == "PRIVATE KEY BODY"
    assert credentials.private_key_passphrase == "phrase"
    assert credentials.ssh_certificate == "CERT BODY"


@pytest.mark.parametrize(
    "password, private_key_file",
    [(None, None), ("s3cret", "/tmp/key")],
)
def test_exactly_one_authentication_method_is_required(
    monkeypatch, password, private_key_file
):
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    if password:
        monkeypatch.setenv("DEVICE_PASSWORD", password)
    if private_key_file:
        monkeypatch.setenv("DEVICE_PRIVATE_KEY_FILE", private_key_file)

    with pytest.raises(ValueError, match="exactly one"):
        config.build_env_credentials()


def test_unreadable_private_key_file_fails_at_startup_naming_the_variable(monkeypatch):
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PRIVATE_KEY_FILE", "/nonexistent/key")

    with pytest.raises(ValueError, match="DEVICE_PRIVATE_KEY_FILE"):
        config.build_env_credentials()


def test_empty_private_key_file_fails_at_startup(monkeypatch, tmp_path):
    key_file = tmp_path / "empty"
    key_file.write_text("   \n", encoding="utf-8")
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PRIVATE_KEY_FILE", str(key_file))

    with pytest.raises(ValueError, match="DEVICE_PRIVATE_KEY_FILE is empty"):
        config.build_env_credentials()


def test_the_same_credentials_serve_every_profile(monkeypatch):
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PASSWORD", "s3cret")
    provider = EnvCredentialProvider(config.build_env_credentials())

    assert provider.get_credentials("anything") is provider.get_credentials("other")


def test_env_credentials_are_used_without_any_vault_configured(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_PROXY_SOCKET_PATH", "/nonexistent/vault.sock")
    monkeypatch.setenv("DEVICE_USERNAME", "diag")
    monkeypatch.setenv("DEVICE_PASSWORD", "s3cret")

    provider, credential_profiles = config.build_credentials()

    assert isinstance(provider, EnvCredentialProvider)
    # No profile names to check an inventory against: one login covers all.
    assert credential_profiles is None


def test_vault_is_still_required_when_no_env_credentials_are_set(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_PROXY_SOCKET_PATH", "/nonexistent/vault.sock")

    with pytest.raises(ValueError, match="DEVICE_USERNAME"):
        config.build_credentials()
