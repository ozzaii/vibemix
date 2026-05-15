# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 07 — 30-day library staleness nudge.

Closes v2.0 LIBRARY-06 deferred surface: detect when the user's library
cache is older than 30 days and emit a single ``ipc.library.staleness_nudge``
at sidecar boot so the renderer can show a "re-import to keep me grounded"
banner. Snooze persists 7 days in ``~/.config/vibemix/state.json``.

Pure functions — no module-level state. Caller (``__main__.py``) decides
when to call ``emit_nudge_if_stale`` (once per boot).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# 30-day staleness threshold + 7-day snooze duration. Locked.
STALE_AGE_SECONDS = 30 * 86400
SNOOZE_DURATION_SECONDS = 7 * 86400

# Plan 25's library.pkl path — the staleness signal.
DEFAULT_LIBRARY_PKL = Path.home() / ".cache" / "vibemix" / "library.pkl"

# Snooze state lives under the standard user config dir.
DEFAULT_STATE_FILE_PATH = Path.home() / ".config" / "vibemix" / "state.json"
STATE_KEY = "library_staleness_snoozed_until"


def is_stale(library_pkl: Path | None = None) -> tuple[bool, int]:
    """Return ``(is_stale, age_in_days)`` for the library cache.

    Returns ``(False, 0)`` when no ``library.pkl`` exists — fresh-install
    users must NOT see a nudge they don't yet need.
    """
    pkl = Path(library_pkl) if library_pkl else DEFAULT_LIBRARY_PKL
    if not pkl.exists():
        return False, 0
    age = time.time() - pkl.stat().st_mtime
    return age > STALE_AGE_SECONDS, int(age // 86400)


def load_snooze_state(state_path: Path | None = None) -> float | None:
    """Read the snooze timestamp from state.json.

    Returns ``None`` when:
        - state.json doesn't exist (fresh install)
        - JSON is malformed (graceful — we log + over-nudge rather than crash)
        - the snooze key is absent
    """
    sp = Path(state_path) if state_path else DEFAULT_STATE_FILE_PATH
    try:
        with sp.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("staleness state.json malformed (%s); treating as empty", e)
        return None
    val = data.get(STATE_KEY)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def save_snooze_state(
    snoozed_until_ts: float, state_path: Path | None = None
) -> None:
    """Atomic write of snooze state. Preserves existing keys."""
    sp = Path(state_path) if state_path else DEFAULT_STATE_FILE_PATH
    sp.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sp.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    data[STATE_KEY] = float(snoozed_until_ts)

    # Atomic write: tempfile in same dir + os.replace. NamedTemporaryFile so
    # the tmp file is cleaned up on exception before the replace.
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(sp.parent), prefix=".state-", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, sp)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def is_snoozed(state_path: Path | None = None) -> bool:
    """True iff snooze is set AND not yet expired."""
    snoozed_until = load_snooze_state(state_path)
    if snoozed_until is None:
        return False
    return snoozed_until > time.time()


def emit_nudge_if_stale(
    emit_ipc: Callable[[str, dict], None],
    library_pkl: Path | None = None,
    state_path: Path | None = None,
) -> bool:
    """Boot-time check: emit nudge IFF library is stale AND not snoozed.

    Returns ``True`` if the nudge was emitted, ``False`` otherwise. Pure —
    caller must invoke once per boot.
    """
    stale, age_days = is_stale(library_pkl)
    if not stale:
        return False
    if is_snoozed(state_path):
        return False
    snoozed_until = load_snooze_state(state_path)
    emit_ipc(
        "ipc.library.staleness_nudge",
        {
            "age_days": age_days,
            "snoozed_until_ts": snoozed_until,
            "schema_version": "1",
        },
    )
    return True


def apply_snooze_action(
    action: str, state_path: Path | None = None
) -> None:
    """Apply a renderer-initiated staleness action.

    Actions:
        ``"dismiss"``  → no-op on disk (UI hides banner this-session only).
        ``"snooze_7d"`` → persist ``time.time() + SNOOZE_DURATION_SECONDS``.

    Unknown actions raise ValueError.
    """
    if action == "dismiss":
        return
    if action == "snooze_7d":
        save_snooze_state(time.time() + SNOOZE_DURATION_SECONDS, state_path)
        return
    raise ValueError(
        f"unknown staleness action {action!r}; "
        f"expected 'dismiss' or 'snooze_7d'"
    )


__all__ = [
    "STALE_AGE_SECONDS",
    "SNOOZE_DURATION_SECONDS",
    "STATE_KEY",
    "DEFAULT_LIBRARY_PKL",
    "DEFAULT_STATE_FILE_PATH",
    "is_stale",
    "load_snooze_state",
    "save_snooze_state",
    "is_snoozed",
    "emit_nudge_if_stale",
    "apply_snooze_action",
]
