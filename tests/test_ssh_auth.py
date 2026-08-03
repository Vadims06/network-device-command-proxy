from pathlib import Path

import pytest

from device_command_proxy.contracts import DeviceCredentials
from device_command_proxy.ssh_auth import authentication_options, ensure_host_key


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


def test_unknown_host_gets_scanned_key_appended_once(tmp_path):
    known_hosts_file = tmp_path / "known_hosts"
    scan_calls = []

    def scan():
        scan_calls.append(1)
        return "10.0.0.5 ssh-ed25519 AAAAscannedkey\n"

    ensure_host_key("10.0.0.5", 22, str(known_hosts_file), scan=scan)
    assert known_hosts_file.read_text(encoding="utf-8") == "10.0.0.5 ssh-ed25519 AAAAscannedkey\n"
    assert len(scan_calls) == 1

    ensure_host_key("10.0.0.5", 22, str(known_hosts_file), scan=scan)
    assert len(scan_calls) == 1


def test_non_default_port_recorded_and_matched_in_bracket_form(tmp_path):
    known_hosts_file = tmp_path / "known_hosts"
    scan_calls = []

    def scan():
        scan_calls.append(1)
        return "[10.0.0.6]:2222 ssh-ed25519 AAAAscannedkey\n"

    ensure_host_key("10.0.0.6", 2222, str(known_hosts_file), scan=scan)
    assert known_hosts_file.read_text(encoding="utf-8") == "[10.0.0.6]:2222 ssh-ed25519 AAAAscannedkey\n"
    assert len(scan_calls) == 1

    ensure_host_key("10.0.0.6", 2222, str(known_hosts_file), scan=scan)
    assert len(scan_calls) == 1


def test_failing_scan_leaves_known_hosts_file_unchanged(tmp_path):
    known_hosts_file = tmp_path / "known_hosts"

    ensure_host_key("10.0.0.7", 22, str(known_hosts_file), scan=lambda: "")

    assert known_hosts_file.read_text(encoding="utf-8") == ""


def test_known_host_with_different_key_is_left_untouched_for_ssh_to_reject(tmp_path):
    known_hosts_file = tmp_path / "known_hosts"
    known_hosts_file.write_text("10.0.0.8 ssh-ed25519 AAAAoriginalkey\n", encoding="utf-8")

    def scan():
        pytest.fail("scan must not run for an already-known host")

    ensure_host_key("10.0.0.8", 22, str(known_hosts_file), scan=scan)

    assert known_hosts_file.read_text(encoding="utf-8") == "10.0.0.8 ssh-ed25519 AAAAoriginalkey\n"


def test_certificate_is_written_beside_the_key_where_openssh_looks_for_it(tmp_path):
    credentials = DeviceCredentials(
        username="diag",
        authentication_type="private_key",
        private_key="PRIVATE KEY",
        ssh_certificate="CERT",
    )

    with authentication_options(
        credentials, private_key_directory=str(tmp_path)
    ) as authentication:
        certificate = Path(f"{authentication['auth_private_key']}-cert.pub")

        assert certificate.read_text(encoding="utf-8") == "CERT"

    assert not certificate.exists()


def test_no_certificate_file_is_left_behind_when_none_is_configured(tmp_path):
    credentials = DeviceCredentials(
        username="diag",
        authentication_type="private_key",
        private_key="PRIVATE KEY",
    )

    with authentication_options(
        credentials, private_key_directory=str(tmp_path)
    ) as authentication:
        assert not Path(f"{authentication['auth_private_key']}-cert.pub").exists()

    assert list(tmp_path.iterdir()) == []
