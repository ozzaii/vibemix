# SPDX-License-Identifier: Apache-2.0
"""UUID-01..06 — install_uuid keyring + file fallback + null-backend detection.

All tests force `_fallback_path` to a `tmp_path` location and mock keyring's
backend / get_password / set_password so they do not touch the real OS
keychain.
"""

from __future__ import annotations

import sys

import pytest

from vibemix.agent import install_uuid as iu_mod


class _FakeKeyringStore:
    """In-memory replacement for keyring backed by a dict."""

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}
        self.raise_on_get = False
        self.raise_on_set = False

    def get_password(self, service, account):
        if self.raise_on_get:
            import keyring.errors

            raise keyring.errors.KeyringError("boom")
        return self._store.get((service, account))

    def set_password(self, service, account, value):
        if self.raise_on_set:
            import keyring.errors

            raise keyring.errors.KeyringError("boom")
        self._store[(service, account)] = value


@pytest.fixture
def fake_keyring(monkeypatch, tmp_path):
    """Wire a fake keyring store + redirect _fallback_path to tmp_path."""
    store = _FakeKeyringStore()
    monkeypatch.setattr(iu_mod.keyring, "get_password", store.get_password)
    monkeypatch.setattr(iu_mod.keyring, "set_password", store.set_password)
    # Default: a "real" backend (NOT null)
    monkeypatch.setattr(iu_mod, "_keyring_is_null", lambda: False)
    monkeypatch.setattr(iu_mod, "_fallback_path", lambda: tmp_path / "install_uuid")
    return store


def test_uuid_01_first_call_mints_and_persists(fake_keyring):
    """UUID-01: first call mints; second call returns same."""
    a = iu_mod.get_or_create_install_uuid()
    b = iu_mod.get_or_create_install_uuid()
    assert a == b
    assert len(a) == 32
    assert all(c in "0123456789abcdef" for c in a)


def test_uuid_02_keyring_failure_uses_file_fallback(monkeypatch, fake_keyring, tmp_path):
    """UUID-02: when keyring raises KeyringError on get, fall back to file
    + mint fresh + write to file."""
    fake_keyring.raise_on_get = True
    a = iu_mod.get_or_create_install_uuid()
    assert len(a) == 32
    # File should now contain the same value
    p = tmp_path / "install_uuid"
    assert p.exists()
    assert p.read_text().strip() == a


def test_uuid_03_null_backend_forces_file_fallback(monkeypatch, fake_keyring, tmp_path):
    """UUID-03: null backend → file fallback even though set_password "succeeds"."""
    monkeypatch.setattr(iu_mod, "_keyring_is_null", lambda: True)
    a = iu_mod.get_or_create_install_uuid()
    assert (tmp_path / "install_uuid").exists()
    # Second call reads from file (not the fake null-backend store)
    b = iu_mod.get_or_create_install_uuid()
    assert a == b


def test_uuid_04_platform_path_macos(monkeypatch):
    """UUID-04: file fallback path matches the platform (darwin variant)."""
    monkeypatch.setattr(sys, "platform", "darwin")
    p = iu_mod._fallback_path()
    assert "Library/Application Support/vibemix" in str(p)


def test_uuid_04_platform_path_windows(monkeypatch, tmp_path):
    """UUID-04 (Windows variant)."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    p = iu_mod._fallback_path()
    assert str(p).startswith(str(tmp_path)) and p.name == "install_uuid"


def test_uuid_05_file_mode_0o600_on_posix(fake_keyring, monkeypatch, tmp_path):
    """UUID-05: file written with chmod 0o600 (POSIX only)."""
    if sys.platform == "win32":
        pytest.skip("POSIX-only chmod check")
    # Force file fallback path
    monkeypatch.setattr(iu_mod, "_keyring_is_null", lambda: True)
    iu_mod.get_or_create_install_uuid()
    p = tmp_path / "install_uuid"
    mode = p.stat().st_mode & 0o777
    assert mode == 0o600


def test_uuid_06_file_present_seeds_empty_keyring(fake_keyring, tmp_path):
    """UUID-06: file has value, keyring empty → return file value AND seed
    keyring for next time."""
    # Pre-write file
    seed = "a" * 32
    (tmp_path / "install_uuid").write_text(seed)
    a = iu_mod.get_or_create_install_uuid()
    assert a == seed
    # Keyring should now contain it too
    assert fake_keyring._store[("vibemix", "install_uuid")] == seed
