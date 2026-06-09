# SPDX-License-Identifier: Apache-2.0
"""Bounded keyring calls — the OS keychain can block forever, not just fail.

A locked macOS login keychain (screen lock, launch-at-login before unlock)
turns SecItemAdd/SecItemCopyMatching into an xpc wait on an authorization
dialog (StorageManager::makeLoginAuthUI) that never returns in an unattended
session — sampled live 2026-06-10: the replay sidecar wedged pre-capture
inside the proxy auth block, immune to SIGINT/SIGTERM. Callers already treat
keyring.errors.KeyringError as the designed degradation (install_uuid falls
to its file path, jwt_cache treats the cache as missed and re-registers);
this wrapper converts BLOCKED into that same family so the existing fallback
paths absorb a locked keychain.

The worker is a bare daemon thread, deliberately not a ThreadPoolExecutor: a
thread stuck inside the Security framework cannot be cancelled, and executor
threads are atexit-joined — which would re-wedge interpreter shutdown on the
very hang this module exists to bound. daemon=True keeps exit clean while
the OS call dangles.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import keyring.errors

log = logging.getLogger("vibemix.keyring_guard")

KEYRING_TIMEOUT_S = 10.0


class KeyringTimeout(keyring.errors.KeyringError):
    """Keychain call did not return within the timeout (locked keychain UI)."""


def bounded_keyring_call(
    fn: Callable[..., Any],
    *args: Any,
    timeout_s: float = KEYRING_TIMEOUT_S,
) -> Any:
    """Run one keyring call on a daemon thread; KeyringTimeout if it blocks."""
    result: list[Any] = []
    error: list[BaseException] = []
    done = threading.Event()

    def _worker() -> None:
        try:
            result.append(fn(*args))
        except BaseException as exc:  # noqa: BLE001 — re-raised on the caller thread
            error.append(exc)
        finally:
            done.set()

    threading.Thread(target=_worker, daemon=True, name="keyring-call").start()
    if not done.wait(timeout_s):
        log.warning(
            "keyring call %s timed out after %.1fs — keychain locked? falling back",
            getattr(fn, "__name__", repr(fn)),
            timeout_s,
        )
        raise KeyringTimeout(f"keyring call timed out after {timeout_s:.1f}s")
    if error:
        raise error[0]
    return result[0]


__all__ = ["KEYRING_TIMEOUT_S", "KeyringTimeout", "bounded_keyring_call"]
