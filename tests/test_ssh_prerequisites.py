import os

import pytest

from device_command_proxy import ssh_auth


# root bypasses directory permissions, so the write probe succeeds there and
# the check under test cannot fire at all.
skip_as_root = pytest.mark.skipif(
    os.geteuid() == 0, reason="root ignores the directory mode being tested"
)


def test_prerequisites_pass_when_the_scanner_and_directories_are_usable(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh-keyscan")

    ssh_auth.verify_prerequisites(
        known_hosts_file=str(tmp_path / "hosts" / "known_hosts"),
    )

    assert (tmp_path / "hosts").is_dir()


def test_known_hosts_file_is_optional_when_not_passed_explicitly(monkeypatch, tmp_path):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh")
    monkeypatch.delenv(ssh_auth.KNOWN_HOSTS_FILE_ENV, raising=False)
    monkeypatch.delenv(ssh_auth.PRIVATE_KEY_DIRECTORY_ENV, raising=False)

    ssh_auth.verify_prerequisites()


def test_runtime_paths_can_be_loaded_from_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh")
    monkeypatch.setenv(ssh_auth.KNOWN_HOSTS_FILE_ENV, str(tmp_path / "hosts" / "known_hosts"))
    ssh_auth.verify_prerequisites()

    assert (tmp_path / "hosts").is_dir()


def test_missing_host_key_scanner_fails_at_startup_naming_the_package(
    monkeypatch, tmp_path
):
    # Otherwise it raises FileNotFoundError inside the connection path, which
    # is an OSError and is reported as device_unreachable on every device.
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: None)

    with pytest.raises(ValueError, match="openssh-client"):
        ssh_auth.verify_prerequisites(
            known_hosts_file=str(tmp_path / "known_hosts"),
        )


def test_missing_ssh_client_fails_at_startup_even_when_scanner_is_present(
    monkeypatch, tmp_path
):
    # An environment can have ssh-keyscan without the "ssh" binary Scrapli's
    # system transport actually invokes; the scanner passing is not proof the
    # connection path itself will work.
    monkeypatch.setattr(
        ssh_auth.shutil,
        "which",
        lambda name: "/usr/bin/ssh-keyscan" if name == "ssh-keyscan" else None,
    )

    with pytest.raises(ValueError, match="ssh is required"):
        ssh_auth.verify_prerequisites(
            known_hosts_file=str(tmp_path / "known_hosts"),
        )


@skip_as_root
@pytest.mark.parametrize("unwritable", ["known_hosts"])
def test_an_unwritable_runtime_directory_fails_at_startup(
    monkeypatch, tmp_path, unwritable
):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh-keyscan")
    read_only = tmp_path / "read-only"
    read_only.mkdir(mode=0o500)
    writable = tmp_path / "writable"

    paths = {"known_hosts": str(writable / "known_hosts")}
    paths[unwritable] = str(read_only / "denied")

    with pytest.raises(ValueError, match="must exist and be writable"):
        ssh_auth.verify_prerequisites(
            known_hosts_file=paths["known_hosts"],
        )


@skip_as_root
def test_an_existing_known_hosts_file_that_cannot_be_written_to_fails_at_startup(
    monkeypatch, tmp_path
):
    # The parent directory being writable only means a missing file could be
    # created; it says nothing about a file that already exists under a
    # different owner or with the write bit removed.
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh-keyscan")
    known_hosts_file = tmp_path / "known_hosts"
    known_hosts_file.write_text("existing entry\n")
    known_hosts_file.chmod(0o400)

    with pytest.raises(ValueError, match=str(known_hosts_file)):
        ssh_auth.verify_prerequisites(
            known_hosts_file=str(known_hosts_file),
        )


@skip_as_root
def test_an_existing_known_hosts_file_that_cannot_be_read_fails_at_startup(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh")
    known_hosts_file = tmp_path / "known_hosts"
    known_hosts_file.write_text("existing entry\n")
    known_hosts_file.chmod(0o200)

    with pytest.raises(ValueError, match=str(known_hosts_file)):
        ssh_auth.verify_prerequisites(
            known_hosts_file=str(known_hosts_file),
        )


@skip_as_root
def test_existing_known_hosts_does_not_require_a_writable_parent(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh")
    read_only_parent = tmp_path / "known-hosts"
    read_only_parent.mkdir()
    known_hosts_file = read_only_parent / "known_hosts"
    known_hosts_file.write_text("existing entry\n")
    known_hosts_file.chmod(0o600)
    read_only_parent.chmod(0o500)

    ssh_auth.verify_prerequisites(
        known_hosts_file=str(known_hosts_file),
    )


@skip_as_root
def test_private_key_directory_is_not_required_at_startup(monkeypatch, tmp_path):
    # Which devices use keys may be known only after Vault resolution.
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh-keyscan")

    ssh_auth.verify_prerequisites(
        known_hosts_file=str(tmp_path / "hosts" / "known_hosts"),
    )


def test_private_key_directory_is_checked_when_selected(monkeypatch, tmp_path):
    monkeypatch.setattr(ssh_auth.shutil, "which", lambda _name: "/usr/bin/ssh-keyscan")

    ssh_auth.verify_prerequisites(
        known_hosts_file=str(tmp_path / "hosts" / "known_hosts"),
        private_key_directory=str(tmp_path / "keys"),
    )

    assert (tmp_path / "keys").is_dir()
