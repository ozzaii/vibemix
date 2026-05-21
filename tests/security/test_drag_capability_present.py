# SPDX-License-Identifier: Apache-2.0
"""Phase 57 / POLISH-02 — regression pin for the v0.1.0-rc1 carryover bugs.

VERIFY-AND-HARDEN, not re-implement. The two fixes pinned here were closed
in commit ``fac4c4a`` and are intact in the working tree; this gate makes them
un-regress-able by turning any removal into a red test instead of a silently
shipped broken build.

Pins:

(POLISH-02a) The window-drag capability ``core:window:allow-start-dragging``
    must be a member of the parsed ``permissions`` array of
    ``tauri/src-tauri/capabilities/default.json``. Without it, the JS-API
    fallback (``tauriWin.startDragging()`` in ``mascot/index.ts``) is rejected
    by the Tauri runtime with "window.start_dragging not allowed" and the
    mascot window cannot be dragged.

(POLISH-02c) ``tauri/src-tauri/src/permissions.rs`` must open the macOS
    Privacy deep-link via the direct ``std::process::Command::new("open")``
    path and must NOT use the deprecated ``app.shell().open()`` form — the
    latter had silent-failure regressions on recent macOS and was removed in
    ``fac4c4a``.

Statically scoped: never runs ``cargo``; reads source as untrusted text /
parsed JSON only.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = REPO_ROOT / "tauri" / "src-tauri" / "capabilities" / "default.json"
PERMISSIONS_RS = REPO_ROOT / "tauri" / "src-tauri" / "src" / "permissions.rs"

DRAG_PERMISSION = "core:window:allow-start-dragging"


def test_capability_files_exist() -> None:
    assert CAPABILITIES.exists(), f"missing {CAPABILITIES}"
    assert PERMISSIONS_RS.exists(), f"missing {PERMISSIONS_RS}"


def test_drag_capability_is_allowlisted() -> None:
    """``core:window:allow-start-dragging`` is a parsed-array member.

    JSON membership (not a substring match) so that whitespace/ordering churn
    in default.json cannot false-pass, and an object-form permission entry is
    handled by its ``identifier``.
    """
    cfg = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    perms = cfg.get("permissions", [])
    flat = [p if isinstance(p, str) else p.get("identifier") for p in perms]
    assert DRAG_PERMISSION in flat, (
        f"capabilities/default.json missing {DRAG_PERMISSION!r} — the mascot "
        "window drag (mascot/index.ts startDragging()) will be rejected by the "
        "Tauri runtime. Regression of POLISH-02a (closed in fac4c4a)."
    )


def test_permissions_rs_uses_direct_open_not_shell() -> None:
    """The Privacy deep-link uses Command::new("open"), not shell().open().

    The deprecated ``app.shell().open()`` path silently failed on recent macOS;
    ``fac4c4a`` switched to the direct ``std::process::Command::new("open")``
    spawn. Pin both the presence of the direct form and the absence of the
    deprecated form so a refactor cannot quietly reintroduce the broken path.
    """
    src = PERMISSIONS_RS.read_text(encoding="utf-8")
    assert 'Command::new("open")' in src, (
        "permissions.rs no longer spawns the macOS Privacy deep-link via "
        'std::process::Command::new("open") — regression of POLISH-02c '
        "(closed in fac4c4a)."
    )
    assert "shell().open" not in src, (
        "permissions.rs reintroduced the deprecated app.shell().open() "
        "deep-link form — it silently fails on recent macOS. Use "
        'std::process::Command::new("open") (POLISH-02c, fac4c4a).'
    )
