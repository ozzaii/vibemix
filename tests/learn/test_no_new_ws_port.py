# SPDX-License-Identifier: Apache-2.0
"""Phase 91 Plan 02 — Invariant #4 (one-socket) grep gate for ``src/vibemix/learn/``.

The Learn surface MUST piggy-back on the existing ``ws_broadcast`` 127.0.0.1:8765
producer (debrief uses ``8766`` — that's the only allowed second listener; Learn
shares 8765). A second ``websockets.serve`` anywhere under ``src/vibemix/learn/``
would silently violate Invariant #4 (CLAUDE.md §Architecture).

This is a static grep gate: every ``.py`` inside ``src/vibemix/learn/`` is
scanned, and the first ``websockets.serve`` outside a comment fails the gate.

REQ-ID: RENDER-07 (one-socket invariant pin for the Learn island).

Sampling: per-task commit (~10 ms — file walk + substring scan).
"""
from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Return the repo root. Tests run from repo root via ``pytest`` so
    ``Path.cwd()`` works, but resolving from ``__file__`` is more robust
    against ``pytest --rootdir`` overrides."""
    # tests/learn/test_no_new_ws_port.py → ../../
    return Path(__file__).resolve().parent.parent.parent


def test_no_websockets_serve_in_learn_subpackage() -> None:
    """Walk ``src/vibemix/learn/**/*.py`` and assert zero ``websockets.serve``
    references outside comment lines.

    The forbidden substring must not appear in any line whose ``lstrip()``
    does NOT start with ``#`` (so the gate ignores "do-not-use" warning
    comments).
    """
    learn_dir = _repo_root() / "src" / "vibemix" / "learn"
    if not learn_dir.exists():
        # Partial checkout without Learn package — invariant trivially holds.
        return

    offenders: list[tuple[Path, int, str]] = []
    for path in learn_dir.rglob("*.py"):
        for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
            stripped = raw.lstrip()
            if stripped.startswith("#"):
                continue
            if "websockets.serve" in raw:
                offenders.append((path, lineno, raw))

    assert not offenders, (
        "Invariant #4 (one-socket) violated. The Learn subpackage shares "
        "ws:8765 with the live deck via the existing ``ws_broadcast`` "
        "producer — no second ``websockets.serve`` is permitted under "
        f"``src/vibemix/learn/``. Offenders ({len(offenders)}):\n"
        + "\n".join(f"  {p}:{n}: {ln.strip()}" for p, n, ln in offenders)
    )
