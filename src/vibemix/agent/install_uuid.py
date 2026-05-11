# SPDX-License-Identifier: Apache-2.0
"""Get-or-create persistent install UUID for this vibemix install.

Per RESEARCH Q4: keyring primary + file fallback at platform path.
Pitfall 6: detect keyring.backends.null.Keyring at startup and force
file fallback — null backend silently succeeds on set then returns
None on get, causing fresh UUID every launch.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path

import keyring
import keyring.errors

log = logging.getLogger("vibemix.install_uuid")

_SERVICE = "vibemix"
_ACCOUNT_UUID = "install_uuid"


def _fallback_path() -> Path:
    """Platform-appropriate path for the file fallback."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "vibemix"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "vibemix"
    else:  # Linux excluded per CONTEXT — harmless fallback
        base = Path.home() / ".local" / "share" / "vibemix"
    base.mkdir(parents=True, exist_ok=True)
    return base / "install_uuid"


def _is_valid_uuid_hex(value: str | None) -> bool:
    return bool(value) and len(value) == 32 and all(c in "0123456789abcdef" for c in value)


def _read_file() -> str | None:
    p = _fallback_path()
    if not p.exists():
        return None
    v = p.read_text(encoding="utf-8").strip()
    return v if _is_valid_uuid_hex(v) else None


def _write_file(value: str) -> None:
    p = _fallback_path()
    p.write_text(value, encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass  # Windows perms model differs; best-effort


def _keyring_is_null() -> bool:
    """Detect Pitfall 6: silently-failing null backend."""
    backend = keyring.get_keyring()
    return "null" in backend.__class__.__module__.lower()


def get_or_create_install_uuid() -> str:
    """Return persistent install UUID. Mints UUIDv4 on first call.

    Order of precedence:
        1. OS keychain (keyring) when backend is real.
        2. Local file fallback (keyring failure OR null backend).
        3. Mint fresh UUIDv4 and persist to both keyring + file.
    """
    force_file = _keyring_is_null()
    if force_file:
        log.warning(
            "keyring backend is null (%s) — using file fallback",
            keyring.get_keyring().__class__.__module__,
        )

    # Step 1: Try keyring
    if not force_file:
        try:
            existing = keyring.get_password(_SERVICE, _ACCOUNT_UUID)
            if _is_valid_uuid_hex(existing):
                return existing  # type: ignore[return-value]
        except keyring.errors.KeyringError as e:
            log.warning(
                "keyring read failed (%s) — using file fallback",
                e.__class__.__name__,
            )
            force_file = True

    # Step 2: Try file (fallback OR keyring-empty-but-file-present)
    file_value = _read_file()
    if file_value:
        if not force_file:
            try:
                keyring.set_password(_SERVICE, _ACCOUNT_UUID, file_value)
            except keyring.errors.KeyringError:
                pass
        return file_value

    # Step 3: Mint fresh
    new_uuid = uuid.uuid4().hex
    wrote_keyring = False
    if not force_file:
        try:
            keyring.set_password(_SERVICE, _ACCOUNT_UUID, new_uuid)
            wrote_keyring = True
        except keyring.errors.KeyringError as e:
            log.warning(
                "keyring write failed (%s) — using file fallback",
                e.__class__.__name__,
            )
    if not wrote_keyring:
        _write_file(new_uuid)
    return new_uuid
