# SPDX-License-Identifier: Apache-2.0
"""keyring_guard — bounded keychain calls (the locked-keychain boot wedge).

Sampled live 2026-06-10: with the macOS login keychain locked (screen lock),
SecItemAdd blocks forever on an authorization UI (StorageManager::
makeLoginAuthUI → xpc wait) — the replay sidecar wedged pre-capture, immune
to SIGINT/SIGTERM. Every caller already treats keyring.errors.KeyringError
as "fall back to file / skip the cache", so the guard converts BLOCKED into
that same designed degradation instead of a forever-hang.
"""

from __future__ import annotations

import threading
import time

import keyring.errors
import pytest

from vibemix.agent import install_uuid as iu_mod
from vibemix.agent.keyring_guard import KeyringTimeout, bounded_keyring_call


def test_blocked_call_raises_keyring_error_within_timeout() -> None:
    """A keychain call that never returns must surface as KeyringError (the
    family every call site already catches), promptly — not hang the loop."""
    started = time.monotonic()
    with pytest.raises(keyring.errors.KeyringError):
        bounded_keyring_call(lambda: threading.Event().wait(30.0), timeout_s=0.2)
    assert time.monotonic() - started < 2.0


def test_timeout_is_a_keyring_error_subclass() -> None:
    """KeyringTimeout must stay inside the KeyringError family — the existing
    except-clauses in install_uuid/jwt_cache are the designed fallback path."""
    assert issubclass(KeyringTimeout, keyring.errors.KeyringError)


def test_fast_call_returns_value() -> None:
    assert bounded_keyring_call(lambda: "jwt-value", timeout_s=5.0) == "jwt-value"


def test_call_args_forwarded() -> None:
    assert bounded_keyring_call(lambda a, b: (a, b), "svc", "acct", timeout_s=5.0) == (
        "svc",
        "acct",
    )


def test_worker_exception_propagates() -> None:
    """A real keyring error (not a timeout) must reach the caller unchanged."""

    def _boom() -> None:
        raise keyring.errors.KeyringError("locked")

    with pytest.raises(keyring.errors.KeyringError, match="locked"):
        bounded_keyring_call(_boom, timeout_s=5.0)


def test_install_uuid_survives_blocked_keychain(monkeypatch, tmp_path) -> None:
    """Boot-level pin for the measured wedge: keyring.get_password blocks
    forever → get_or_create_install_uuid returns via the file fallback in
    bounded time instead of hanging the asyncio loop pre-capture."""

    def _blocked(*_args, **_kwargs):
        threading.Event().wait(30.0)

    monkeypatch.setattr(iu_mod.keyring, "get_password", _blocked)
    monkeypatch.setattr(iu_mod.keyring, "set_password", _blocked)
    monkeypatch.setattr(iu_mod, "_keyring_is_null", lambda: False)
    monkeypatch.setattr(iu_mod, "_fallback_path", lambda: tmp_path / "install_uuid")
    monkeypatch.setattr(iu_mod, "_KEYRING_TIMEOUT_S", 0.2)

    started = time.monotonic()
    value = iu_mod.get_or_create_install_uuid()
    assert time.monotonic() - started < 3.0
    assert len(value) == 32
    assert (tmp_path / "install_uuid").read_text().strip() == value
