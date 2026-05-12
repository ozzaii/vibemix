# SPDX-License-Identifier: Apache-2.0
"""Windows on-screen window enumeration for the calibration wizard.

Companion to ``_windows_macos.py`` — same surface, same return type, same
DJ-app hint set, different OS API.

**Warning #4 — WS-path only.** This module is invoked by
``WizardLoop._on_list_windows`` via the ``ipc.calibration.list_windows``
handler over the WebSocket bus. There is NO Rust-side
``enumerate_windows`` Tauri command.

DJ-app hint table mirrors ``_windows_macos.py`` minus djay (which is
macOS-exclusive). Keep them in sync.

Privacy gate (T-11-W4-06): titles are never logged. The caller adapts
``WindowInfoNative`` to the wire schema; titles cross the WS boundary
only — they do not enter the rotating sidecar log.

API choice:
- ``win32gui.EnumWindows`` walks the top-level window list synchronously
  in <50ms.
- ``win32process.GetWindowThreadProcessId`` + ``win32api.OpenProcess`` +
  ``win32process.GetModuleFileNameEx`` resolves the owning module path
  → leaf name is the app_name we render.
- ``PROCESS_QUERY_LIMITED_INFORMATION`` (0x1000) is the minimal access
  right that survives Microsoft's protected-process model (works for
  most apps without admin elevation).

Failure modes:
- If module resolution fails (denied access, race vs process exit), the
  row still surfaces with an empty ``app_name``. The hint matcher uses
  the title as fallback context.
"""

from __future__ import annotations

from dataclasses import dataclass

# DJ-app hint set per D-Area-3.2. Lower-case substring match against the
# concatenation of (app_name + ' ' + title). First entry that matches wins.
# Order is preference order for the wizard's auto-select behavior.
# (No djay entry — djay Pro is macOS-only.)
_DJ_APP_HINTS: dict[str, tuple[str, ...]] = {
    "rekordbox": ("rekordbox",),
    "serato": ("serato dj pro", "serato dj", "serato"),
    "traktor": ("traktor pro", "traktor"),
    "virtualdj": ("virtualdj", "virtual dj"),
}


@dataclass(frozen=True, slots=True)
class WindowInfoNative:
    """One entry from EnumWindows. Same shape as the macOS sibling."""

    id: str
    app_name: str
    title: str
    dj_app_hint: str | None


def _match_dj_app_hint(app_name: str, title: str) -> str | None:
    """Lower-case substring match against the hint table."""
    hay = f"{app_name} {title}".lower()
    for hint, needles in _DJ_APP_HINTS.items():
        if any(needle in hay for needle in needles):
            return hint
    return None


def enumerate_windows() -> list[WindowInfoNative]:
    """Return the visible top-level windows (EnumWindows + GetWindowText).

    Filtering rules:
        - Visible windows only (``IsWindowVisible``).
        - Non-empty titles only (matches macOS sibling — skip anonymous
          background helpers).
    """
    import win32api  # type: ignore[import-not-found]
    import win32con  # type: ignore[import-not-found]
    import win32gui  # type: ignore[import-not-found]
    import win32process  # type: ignore[import-not-found]

    results: list[WindowInfoNative] = []

    def _cb(hwnd: int, _ctx: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if not title.strip():
            return True
        try:
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            module_path = win32process.GetModuleFileNameEx(handle, 0)
            app_name = module_path.split("\\")[-1]
        except Exception:
            # Protected process / race condition — surface with empty
            # app_name; the picker still renders the title.
            app_name = ""
        results.append(
            WindowInfoNative(
                id=str(int(hwnd)),
                app_name=app_name,
                title=title.strip(),
                dj_app_hint=_match_dj_app_hint(app_name, title),
            )
        )
        return True

    win32gui.EnumWindows(_cb, None)
    return results


__all__ = ["WindowInfoNative", "enumerate_windows"]
