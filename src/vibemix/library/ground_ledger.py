# SPDX-License-Identifier: Apache-2.0
"""Cross-turn grounded working-set ledger for Viber chat (the "ground ledger").

Why this exists: every in-app chat turn spawns a fresh ``codex exec`` and a
fresh MCP server, so the per-run seen-set (the Invariant-#2 grounding spine)
forgot every track the PREVIOUS turn had already discovered and validated —
"drop the second one" forced a full re-discovery or got gate-rejected as
invented. This ledger persists ONLY track ids + display meta between turns of
one conversation.

Grounding contract (Cardinal Invariant #2): nothing in this file is an
authority. ``load_working_set`` returns persisted ids as HINTS; every consumer
MUST re-validate each id against the live library in THIS process before it
may enter any grounding set (``LibraryToolset.seed_working_set`` and the chat
wrapper's ``_validate_against_library`` are the enforcing seams). A dead or
foreign id therefore dies silently at load — it can never widen what the
model is allowed to cite.

Merge semantics (continuity heuristic, owned by the chat wrapper):

* empty chat history → fresh conversation → the ledger is OVERWRITTEN with
  this run's validated ids only, so a stale set never leaks forward;
* non-empty history → same conversation → union(loaded-still-live ids, this
  run's validated ids), order-preserving with the prior ids first.

The primitives here are deliberately pure (path in, data out, never raise);
the ``VIBEMIX_VIBER_WORKING_SET=0`` kill-switch is enforced by the wiring in
``codex_curate.chat_with_codex`` (the only writer), not down here, so tests
and operators can still inspect a ledger while the feature is off.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from vibemix.library.cache_paths import VIBEMIX_CACHE_DIR

LEDGER_VERSION = 1
DEFAULT_WORKING_SET_PATH = VIBEMIX_CACHE_DIR / "viber_working_set.json"
# Kill-switch (default ON): "0"/"false"/"no"/"off" disables load+save wiring.
WORKING_SET_ENV = "VIBEMIX_VIBER_WORKING_SET"
# Path override — tests and dev shells point the ledger away from ~/.cache.
WORKING_SET_PATH_ENV = "VIBEMIX_VIBER_WORKING_SET_PATH"

# A working set is a conversation's short-term memory, not an archive; the cap
# keeps the prompt block and the seed pass bounded. Recency wins on overflow
# (later ids are the freshest finds), so the cap keeps the TAIL.
_MAX_IDS = 200


def working_set_enabled() -> bool:
    """Default-on kill-switch (``VIBEMIX_VIBER_WORKING_SET=0`` disables)."""
    raw = os.environ.get(WORKING_SET_ENV, "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def default_ledger_path() -> Path:
    """Resolved ledger path (env override, else the vibemix cache dir)."""
    raw = os.environ.get(WORKING_SET_PATH_ENV, "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_WORKING_SET_PATH


def load_working_set(path: str | Path) -> list[str]:
    """Read persisted track ids — tolerant of a missing/corrupt/foreign file.

    Returns ids exactly as persisted (deduped, order-preserving, non-string
    entries dropped). Callers MUST re-validate every id against the live
    library before letting it near a grounding set; a torn or hand-edited
    file degrades to ``[]``, never to an exception.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        payload = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(payload, dict):
        return []
    ids = payload.get("track_ids")
    if not isinstance(ids, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for tid in ids:
        if isinstance(tid, str) and tid and tid not in seen:
            out.append(tid)
            seen.add(tid)
    return out[-_MAX_IDS:] if len(out) > _MAX_IDS else out


def save_working_set(
    path: str | Path,
    track_ids: list[str],
    meta: dict[str, dict[str, str]] | None = None,
) -> bool:
    """Persist the working set atomically (tmp + rename); best-effort.

    Stores ONLY ids + display meta (title/artist) — no scores, no audio
    facts, nothing the next process could mistake for live evidence. Meta is
    scoped to the persisted ids so a stale entry can't outlive its id.
    Returns ``False`` instead of raising on any I/O failure: continuity is a
    convenience, never worth breaking a chat turn over.
    """
    ids: list[str] = []
    seen: set[str] = set()
    for tid in track_ids:
        if isinstance(tid, str) and tid and tid not in seen:
            ids.append(tid)
            seen.add(tid)
    if len(ids) > _MAX_IDS:
        ids = ids[-_MAX_IDS:]
    kept_meta: dict[str, dict[str, str]] = {}
    for tid in ids:
        row = (meta or {}).get(tid)
        if not isinstance(row, dict):
            continue
        kept_meta[tid] = {
            "title": str(row.get("title") or ""),
            "artist": str(row.get("artist") or ""),
        }
    payload: dict[str, Any] = {
        "version": LEDGER_VERSION,
        "updated_at": time.time(),
        "track_ids": ids,
        "meta": kept_meta,
    }
    target = Path(path)
    # Name-concat (not with_suffix) so odd targets like a bare root path
    # degrade to an OSError below instead of a ValueError here.
    tmp = target.parent / (target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    except (OSError, ValueError):
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


__all__ = [
    "DEFAULT_WORKING_SET_PATH",
    "LEDGER_VERSION",
    "WORKING_SET_ENV",
    "WORKING_SET_PATH_ENV",
    "default_ledger_path",
    "load_working_set",
    "save_working_set",
    "working_set_enabled",
]
