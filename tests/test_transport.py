from pathlib import Path

from execution_proxy.contracts import DeviceCredentials
from execution_proxy.transport import authentication_options


def test_private_key_exists_with_mode_0600_only_inside_context(tmp_path):
    credentials = DeviceCredentials(
        username="diag",
        authentication_type="private_key",
        private_key="sensitive-private-key",
    )

    with authentication_options(
        credentials,
        private_key_directory=str(tmp_path),
    ) as options:
        private_key_path = Path(options["auth_private_key"])
        assert private_key_path.read_text(encoding="utf-8") == "sensitive-private-key"
        assert private_key_path.stat().st_mode & 0o777 == 0o600

    assert not private_key_path.exists()


def test_password_does_not_create_private_key_file(tmp_path):
    credentials = DeviceCredentials(
        username="diag",
        authentication_type="password",
        password="sensitive-password",
    )

    with authentication_options(
        credentials,
        private_key_directory=str(tmp_path),
    ) as options:
        assert options == {"auth_password": "sensitive-password"}

    assert list(tmp_path.iterdir()) == []
