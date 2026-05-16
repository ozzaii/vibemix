# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — sidecar config persistence.

JSON-backed settings store at the OS-standard app-data location:

  * macOS   ``~/Library/Application Support/vibemix/config.json``
  * Windows ``%APPDATA%\\vibemix\\config.json``

This is a **superset** of the Phase 11 first-run schema. The Rust shell
(``tauri/src-tauri/src/config.rs``) writes its own keys via
``tauri-plugin-store`` to the same file — both sides preserve unknown
top-level keys on round-trip so neither stomps the other.

Phase 11 keys preserved verbatim on save:
  * ``first_run_completed``
  * ``calibrated_at``
  * ``output_device_id``
  * ``controller_profile``
  * ``target_dj_app_hint``
  * ``target_window_id``
  * ``blackhole_install_seen``
  * ``first_run_state`` (tauri-plugin-store wrapper key — preserved as-is)

Phase 12 fields added:
  * ``voice`` (default ``"kore"``)
  * ``mode`` (default ``"coach"``)
  * ``genre`` (default ``"tech-house"``)
  * ``output_profile`` (default ``"hp"``)
  * ``retention_days`` (default ``7``)
  * ``push_to_mute_hotkey`` (default ``"cmd+shift+m"`` on darwin,
    ``"ctrl+shift+m"`` on win32)

``muted`` is explicitly NOT persisted — it is a transient session state
owned by ``SessionLoop`` and re-derived per launch.

Atomic write: ``json.dumps`` → temp file in the same directory →
``os.replace`` (POSIX rename is atomic; Windows ReplaceFileW is atomic).
Project convention (Phase 6 D-Area-4.4) — no pydantic; hand-written
``@dataclass`` with a plain dict load/save cycle.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def _default_hotkey() -> str:
    """Platform-aware push-to-mute default. macOS ⌘+Shift+M, Windows Ctrl+Shift+M."""
    if sys.platform == "win32":
        return "ctrl+shift+m"
    return "cmd+shift+m"


# Phase 11 + 12 fields the store ALWAYS materializes on save (other
# top-level keys — e.g. tauri-plugin-store's ``first_run_state`` wrapper
# — are preserved verbatim via the merge in ``save_config``).
_PHASE12_FIELDS: tuple[str, ...] = (
    "voice",
    "mode",
    "genre",
    "output_device_id",
    "output_profile",
    "retention_days",
    "push_to_mute_hotkey",
    # Phase 14-04 — perf-blur preference. Persisted alongside the other
    # Phase 12 settings; default False (full v5 visual contract on fresh
    # installs). Read at boot by main.ts to set html[data-blur-perf].
    "lighter_blur",
    # Phase 34 / SEC-08 — telemetry consent. Default False (OFF).
    # Pitfall P67 — no dark pattern. Toggled only by the wizard
    # step-telemetry-consent.ts on explicit user click. Skipping the
    # wizard step leaves it False. Persisted alongside Phase 12 fields.
    "telemetry_consent",
)
_PHASE11_FIELDS: tuple[str, ...] = (
    "first_run_completed",
    "calibrated_at",
    "controller_profile",
    "target_dj_app_hint",
    "target_window_id",
    "blackhole_install_seen",
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _app_data_dir() -> Path:
    """Resolve the OS-standard app-data directory for vibemix.

    macOS: ``$HOME/Library/Application Support/vibemix``
    Windows: ``$APPDATA/vibemix`` (falls back to ``$USERPROFILE/AppData/Roaming``)
    Other (CI/Linux): ``$XDG_CONFIG_HOME/vibemix`` or ``$HOME/.config/vibemix``

    Tests monkeypatch ``HOME`` / ``APPDATA`` to redirect into ``tmp_path``.
    """
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~")) / "Library" / "Application Support" / "vibemix"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "vibemix"
        return Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "vibemix"
    # CI/Linux fallback — keeps tests runnable on non-Mac/Win runners.
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "vibemix"
    return Path(os.path.expanduser("~")) / ".config" / "vibemix"


def config_path() -> Path:
    """Return the absolute path of ``config.json`` (creating no directories)."""
    return _app_data_dir() / "config.json"


def app_data_dir() -> Path:
    """Public alias for ``_app_data_dir``. Phase 15 added so callers outside
    this module (notably ``vibemix.__main__`` resolving the recordings root)
    can read the OS-aware path without importing a private name. Pure
    forwarder — no behavior change, no caching.
    """
    return _app_data_dir()


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class ConfigStore:
    """Phase 12 settings + Phase 11 first-run superset.

    Mutable so ``SettingsApplier`` can write fields in place between
    ``save()`` calls. Unknown top-level keys read off disk are preserved
    in ``extra`` so the Rust-side ``first_run_state`` wrapper is never
    stomped.
    """

    # Phase 12 fields
    voice: str = "kore"
    mode: str = "coach"
    genre: str = "tech-house"
    output_device_id: str | None = None
    output_profile: str = "hp"
    retention_days: int = 7
    push_to_mute_hotkey: str = field(default_factory=_default_hotkey)
    # Phase 14-04 — perf-blur preference (default False = full v5 visuals).
    lighter_blur: bool = False
    # Phase 34 / SEC-08 — telemetry consent (default False = OFF).
    # Pitfall P67 — no dark pattern; the field's existence does not imply
    # consent. Only an explicit wizard toggle flips this to True.
    telemetry_consent: bool = False

    # Phase 11 fields (preserved verbatim — sidecar reads only, Rust writes)
    first_run_completed: bool | None = None
    calibrated_at: str | None = None
    controller_profile: str | None = None
    target_dj_app_hint: str | None = None
    target_window_id: str | None = None
    blackhole_install_seen: bool | None = None

    # Catch-all for keys we don't know — e.g. tauri-plugin-store's
    # ``first_run_state`` wrapper, or future fields a newer build wrote.
    # Preserved verbatim through save.
    extra: dict[str, Any] = field(default_factory=dict)

    # ----- I/O -----

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ConfigStore:
        """Build a ConfigStore from a parsed JSON dict.

        Unknown keys land in ``extra``. Type coercion is permissive — a
        Phase 11-only config (missing all Phase 12 fields) reads back
        with Phase 12 defaults filled in.
        """
        if not isinstance(raw, dict):
            return cls()
        known: set[str] = set(_PHASE11_FIELDS) | set(_PHASE12_FIELDS)
        kwargs: dict[str, Any] = {}
        for key in known:
            if key in raw:
                kwargs[key] = raw[key]
        extra = {k: v for k, v in raw.items() if k not in known}
        # If retention_days came in as something non-int, fall back to default.
        if "retention_days" in kwargs and not isinstance(kwargs["retention_days"], int):
            try:
                kwargs["retention_days"] = int(kwargs["retention_days"])
            except (TypeError, ValueError):
                kwargs.pop("retention_days", None)
        # IN-02 in 14-REVIEW.md — coerce/drop non-bool lighter_blur from
        # disk. A corrupted config.json with `"lighter_blur": "yes"` or
        # `1` would otherwise populate the dataclass verbatim and break
        # the boot-time SettingsState emit (schema requires `"type":
        # "boolean"`). bool is a subclass of int in Python, so
        # `isinstance(True, int)` is True — keep the explicit bool check
        # to reject ints. Same treatment applied to the other Phase 11
        # bool fields so the policy is uniform: silently drop garbage
        # rather than emit a broken ack.
        for _bool_field in (
            "lighter_blur",
            "first_run_completed",
            "blackhole_install_seen",
            # Phase 34 / SEC-08 — telemetry_consent gets the same guard.
            # A corrupted on-disk value (e.g. "yes" or 1) silently falls
            # back to default False (OFF) rather than coercing to True.
            "telemetry_consent",
        ):
            if _bool_field in kwargs and not isinstance(kwargs[_bool_field], bool):
                kwargs.pop(_bool_field, None)
        return cls(extra=extra, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict — preserves ``extra`` keys verbatim.

        Phase 11 keys that are ``None`` are emitted only when they were
        populated; this keeps a fresh Phase 12 install from clobbering
        the Rust shell's ``first_run_state`` wrapper with stray nulls.
        """
        out: dict[str, Any] = {}
        # Always emit Phase 12 fields (defaults are user-facing settings).
        for k in _PHASE12_FIELDS:
            out[k] = getattr(self, k)
        # Phase 11 fields — emit only when populated.
        for k in _PHASE11_FIELDS:
            v = getattr(self, k)
            if v is not None:
                out[k] = v
        # Merge ``extra`` last — preserves keys the sidecar doesn't own
        # (e.g. ``first_run_state`` written by tauri-plugin-store).
        for k, v in self.extra.items():
            if k not in out:
                out[k] = v
        return out

    def save(self, path: Path | None = None) -> Path:
        """Persist via atomic write. Returns the path written.

        Atomic = json.dumps → write to ``<path>.tmp`` in the same dir →
        ``os.replace`` (which is atomic on POSIX + Windows ReplaceFileW).
        """
        target = path or config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)
        return target


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> ConfigStore:
    """Read ``config.json`` and return a populated ``ConfigStore``.

    Missing file → all-defaults ConfigStore (typical for a fresh
    install before Phase 11 wizard completion). Corrupt JSON →
    all-defaults ConfigStore plus a stderr warning; we never crash the
    sidecar over a malformed config.
    """
    target = path or config_path()
    if not target.exists():
        return ConfigStore()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[config_store] load failed ({e}); using defaults", file=sys.stderr)
        return ConfigStore()
    return ConfigStore.from_dict(raw)


def save_config(store: ConfigStore, path: Path | None = None) -> Path:
    """Persist a ``ConfigStore`` atomically. Returns the path written.

    Thin wrapper around ``ConfigStore.save()`` so the module exports the
    classic ``load_config`` / ``save_config`` pair (the plan's exports
    list).
    """
    return store.save(path)


__all__ = ["ConfigStore", "config_path", "load_config", "save_config"]
