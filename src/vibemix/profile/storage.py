# SPDX-License-Identifier: Apache-2.0
"""Profile + consent on-disk storage.

Phase 32 / PROFILE-01 + PROFILE-05. Two files:

- ``~/.config/vibemix/profile.json`` — the profile dict, 0o600. Written
  through :func:`save_profile` which runs the 2KB cap + schema validate.
- ``~/.config/vibemix/state.json`` — the wizard's first-run state file
  (existing). We extend it with the ``profile_consent: bool`` key.

The state.json file is shared with the wizard's ``write_first_run_state``
Tauri command (see :mod:`vibemix.runtime.wizard_loop`). To stay compatible
we read the full dict, mutate the ``profile_consent`` key, write it back.

P51 chmod: profile.json is owner-only (0o600) because it carries the user's
DJ tendencies and gets sent verbatim into the GeminiContextCache body.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from vibemix.profile.builder import serialize_profile
from vibemix.profile.schema import validate_profile


def _config_root() -> Path:
    """Return the user's vibemix config directory.

    Honors ``HOME`` so tests can monkeypatch it without touching $XDG_*.
    """
    return Path.home() / ".config" / "vibemix"


def profile_path() -> Path:
    """Location of the user's profile.json."""
    return _config_root() / "profile.json"


def consent_path() -> Path:
    """Location of the shared state.json (consent + wizard state share it)."""
    return _config_root() / "state.json"


def load_profile() -> dict | None:
    """Return the parsed + validated profile, or ``None`` if absent/corrupt.

    Treats a parse error or schema violation as "missing": the file is
    discarded silently rather than crashing the boot path. The user-facing
    Settings → Profile panel surfaces an explicit "no profile yet" empty
    state in that case (no scary error toast).
    """
    p = profile_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        validate_profile(data)
    except Exception:
        return None
    return data


def save_profile(profile: dict) -> None:
    """Validate, size-cap-check, write atomically, then chmod 0o600.

    Raises :class:`vibemix.profile.ProfileError` if the profile fails the
    schema or the 2048-byte cap. The disk file is NOT written on failure
    (we serialize FIRST, then write the bytes — the bytes call is the
    only thing that touches the filesystem).
    """
    raw = serialize_profile(profile)
    p = profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write via temp + replace so a crash mid-write doesn't leave a
    # half-truncated profile.json that would later fail validation.
    tmp = p.with_suffix(".json.tmp")
    tmp.write_bytes(raw)
    # chmod BEFORE rename so the final inode is owner-only from first moment.
    # Windows os.chmod has limited semantics; the call is harmless there.
    if sys.platform != "win32":
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
    tmp.replace(p)


def delete_profile() -> bool:
    """Unlink the profile.json. Returns True if the file existed."""
    p = profile_path()
    if not p.exists():
        return False
    p.unlink()
    return True


# ---------------------------------------------------------------------------
# Consent (state.json shared with wizard)
# ---------------------------------------------------------------------------


def _read_state() -> dict:
    p = consent_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    p = consent_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    if sys.platform != "win32":
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
    tmp.replace(p)


def load_consent() -> bool:
    """Return current profile_consent flag.

    Default is ``False`` (PROFILE-05 default-OFF). Missing key OR missing
    file BOTH read as False.
    """
    state = _read_state()
    return bool(state.get("profile_consent", False))


def save_consent(consent: bool) -> None:
    """Persist profile_consent to state.json without clobbering other keys."""
    state = _read_state()
    state["profile_consent"] = bool(consent)
    _write_state(state)
