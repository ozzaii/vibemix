# SPDX-License-Identifier: Apache-2.0
"""macOS on-screen window enumeration for the calibration wizard.

**Warning #4 — WS-path only.** This module is invoked by
``WizardLoop._on_list_windows`` via the ``ipc.calibration.list_windows``
handler over the WebSocket bus. There is NO Rust-side
``enumerate_windows`` Tauri command. The webview sends ``list_windows``
through ``forward_ipc_to_sidecar``; the sidecar enumerates via Quartz here
and emits ``ipc.calibration.window_list`` back over the same bus.

Rationale:
- OS-specific window enumeration belongs in the Python platform layer where
  Phase 3 + 7 + 8 already live (Quartz on macOS, EnumWindows on Windows).
- Keeping the Rust capability allowlist tight — no ``shell:allow-execute``
  or new app commands needed for window picking.
- The 19-message IPC schema already includes the request + response shape.

Privacy gate (T-11-W4-06): window titles are **never** logged. They are
returned over the WS only and rendered in the webview picker. Auditing:
no ``log.*`` / ``print(...)`` call in this module touches a title field.
The same rule applies to ``WizardLoop._on_list_windows``.

DJ-app hint table (D-Area-3.2): matches the same hint set used by
Phase 7's Windows track backend so the cross-platform user picker has the
same auto-select behavior. Keep this table in sync with
``_windows_windows.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

# DJ-app hint set per D-Area-3.2. Lower-case substring match against the
# concatenation of (app_name + ' ' + title). First entry that matches wins.
# Order is preference order for the wizard's auto-select behavior.
_DJ_APP_HINTS: dict[str, tuple[str, ...]] = {
    "djay": ("djay pro ai", "djay pro", "djay"),
    "rekordbox": ("rekordbox",),
    "serato": ("serato dj pro", "serato dj", "serato"),
    "traktor": ("traktor pro", "traktor"),
    "virtualdj": ("virtualdj", "virtual dj"),
}


@dataclass(frozen=True, slots=True)
class WindowInfoNative:
    """One entry from Quartz.CGWindowListCopyWindowInfo.

    Maps 1:1 to ``vibemix.ui_bus.messages.WindowInfo`` at the WS boundary —
    the WizardLoop adapts ``WindowInfoNative`` instances into ``WindowInfo``
    wire payloads before emitting ``ipc.calibration.window_list``.
    """

    id: str
    app_name: str
    title: str
    dj_app_hint: str | None


def _match_dj_app_hint(app_name: str, title: str) -> str | None:
    """Case-insensitive substring match against the hint table.

    Builds the haystack from ``f"{app_name} {title}"``. First hint with any
    needle present wins. Returns ``None`` when nothing matches — the
    schema's ``dj_app_hint`` is nullable.
    """
    hay = f"{app_name} {title}".lower()
    for hint, needles in _DJ_APP_HINTS.items():
        if any(needle in hay for needle in needles):
            return hint
    return None


def enumerate_windows() -> list[WindowInfoNative]:
    """Return the on-screen, user-facing windows (Quartz.CGWindowList).

    Filtering rules (anti-noise):
        - On-screen only (``kCGWindowListOptionOnScreenOnly``).
        - Exclude desktop elements (Dock, menu bar, wallpaper).
        - Skip rows with no app_name or no title (background helper
          processes, anonymous windows the user can't pick).

    The blocking Quartz call returns in <100ms on a typical macOS box; the
    WizardLoop offloads it to a thread executor regardless so the asyncio
    event loop never blocks on the WS reply path.

    Privacy: this function returns titles in the dataclass. **Never log
    them.** The caller is responsible for adapting to the wire format and
    emitting over the WS bus only.
    """
    import Quartz  # type: ignore[import-not-found]

    opts = (
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements
    )
    raw = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID) or []

    out: list[WindowInfoNative] = []
    for w in raw:
        app_name = str(w.get(Quartz.kCGWindowOwnerName, "") or "").strip()
        title = str(w.get(Quartz.kCGWindowName, "") or "").strip()
        wid = w.get(Quartz.kCGWindowNumber)
        if wid is None or not app_name or not title:
            # User can't pick what they can't see — skip anonymous /
            # background-helper / windowless rows.
            continue
        out.append(
            WindowInfoNative(
                id=str(int(wid)),
                app_name=app_name,
                title=title,
                dj_app_hint=_match_dj_app_hint(app_name, title),
            )
        )
    return out


__all__ = ["WindowInfoNative", "enumerate_windows"]
