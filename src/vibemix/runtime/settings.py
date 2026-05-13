# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — SettingsApplier.

Routes ``ipc.settings.set`` requests to the appropriate runtime hook + the
config store. Per the 12-02-PLAN must-have:

    ipc.settings.set dispatches by field:
      voice            → cascade.set_voice
      mode             → event_detector.set_mode
      genre            → genre_profile_loader.reload
      output_device_id → audio_core.restart_output
      output_profile   → audio_core.set_mic_gating_profile
      retention_days   → config_store.set + persist
      push_to_mute_hotkey → config_store.set + persist (Tauri rebinds)

Every hook ref is **optional** — the cascade agent, event detector,
audio core, and genre loader are wired by ``12-04`` (the glue plan).
Until then this module accepts ``None`` for any hook and returns a
``(False, "<reason>")`` ack so the UI can surface the missing wiring
without crashing the loop.

Persistence rule: voice, mode, genre, output_device_id, output_profile,
retention_days, push_to_mute_hotkey ALL persist via ``config_store``.
``muted`` is transient and not handled here (``SessionLoop`` owns it).

Latency budget (per plan must-haves):
  * voice / mode / output_device / output_profile → <50ms apply
  * genre reload → ≤250ms async overlay window (Phase 6 loader.reload is
    intentionally slow — re-reads the JSON profile + recomputes
    crest-factor & vocal-detection priors).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from typing import Any, Protocol

from vibemix.runtime.config_store import ConfigStore, save_config

log = logging.getLogger("vibemix.runtime.settings")


# Phase 13-05 — mood enum (anti-hallucination guard for T-13-05-01).
_VALID_MOODS: frozenset[str] = frozenset({"hype-man", "teacher", "coach"})


# ---------------------------------------------------------------------------
# Structural hook protocols — duck-typed; the real implementations live
# in Phase 4 (cascade), Phase 3 (event detector), Phase 2 (audio core),
# and Phase 6 (genre loader). SettingsApplier only needs the named
# method on each ref — never the whole class — so the runtime is
# testable with thin fakes.
# ---------------------------------------------------------------------------


class _CascadeHook(Protocol):
    def set_voice(self, voice: str) -> None: ...


class _EventDetectorHook(Protocol):
    def set_mode(self, mode: str) -> None: ...


class _AudioCoreHook(Protocol):
    def restart_output(self, device_id: str | None) -> None: ...

    def set_mic_gating_profile(self, profile: str) -> None: ...


class _GenreLoaderHook(Protocol):
    def reload(self, genre: str) -> None: ...


class _MusicStateHook(Protocol):
    """Duck-typed MusicState — SettingsApplier only needs ``mood`` r/w under
    ``_lock``. See ``vibemix.state.music_state.MusicState`` for the real shape."""

    mood: str
    _lock: Any  # threading.Lock-like (acquire / release / __enter__ / __exit__)


class _WsBusHook(Protocol):
    """Duck-typed ws-bus — SettingsApplier only needs ``emit(dict)`` which the
    real ``WizardBus`` / ``IpcBus`` (Phase 11/12) implements as an async coro.
    Tests pass MagicMock with ``emit = AsyncMock(...)``."""

    async def emit(self, msg: dict) -> None: ...


# ---------------------------------------------------------------------------
# SettingsApplier
# ---------------------------------------------------------------------------


# Per-field overlay window (seconds) — the UI dims the relevant control
# for this long to mask the apply latency. Voice/mode/output are fast
# enough that we don't bother awaiting; genre reload reads + re-parses
# the profile JSON which is intentionally slow (Phase 6).
GENRE_OVERLAY_S: float = 0.25


class SettingsApplier:
    """Apply a single ``ipc.settings.set`` field to the runtime + config.

    Constructor accepts every hook as ``Optional`` so Phase 12 Wave 2
    can ship before Wave 3/4 wires the real refs. Tests pass fakes
    (MagicMock) for the hooks they care about and ``None`` for the rest.

    ``config_store`` is the ONE non-optional ref — without it we can't
    persist anything and there's no point running.
    """

    def __init__(
        self,
        *,
        config_store: ConfigStore,
        cascade_agent: _CascadeHook | None = None,
        event_detector: _EventDetectorHook | None = None,
        audio_core: _AudioCoreHook | None = None,
        genre_loader: _GenreLoaderHook | None = None,
        music_state: _MusicStateHook | None = None,
        ws_bus: _WsBusHook | None = None,
    ) -> None:
        self.config_store = config_store
        self.cascade_agent = cascade_agent
        self.event_detector = event_detector
        self.audio_core = audio_core
        self.genre_loader = genre_loader
        # Phase 13-05 — mood writes back into MusicState (canonical) +
        # emits ipc.mascot.mood_change over the WS bus the moment a swap
        # is applied. Both refs are optional so Plan 13-05 ships independent
        # of the orchestration plan that finally wires them in main().
        self.music_state = music_state
        self.ws_bus = ws_bus

    # ------------------------------------------------------------------
    # Dispatch entry point
    # ------------------------------------------------------------------

    async def apply(self, field: str, value: Any) -> tuple[bool, str | None]:
        """Apply ``field=value`` to the runtime + config.

        Returns ``(success, error)``. On success, ``error`` is ``None``;
        on failure (missing hook, bad value, hook raised), ``success``
        is ``False`` and ``error`` is a one-line user-facing reason.

        Never raises — exceptions are caught and converted to error
        acks so the calling handler can emit ``ipc.error`` (or a
        partial ack) without crashing the WS loop.
        """
        try:
            if field == "voice":
                return await self._apply_voice(value)
            if field == "mode":
                return await self._apply_mode(value)
            if field == "genre":
                return await self._apply_genre(value)
            if field == "output_device_id":
                return await self._apply_output_device(value)
            if field == "output_profile":
                return await self._apply_output_profile(value)
            if field == "retention_days":
                return await self._apply_retention(value)
            if field == "push_to_mute_hotkey":
                return await self._apply_hotkey(value)
            if field == "mood":
                return await self._apply_mood(value)
            if field == "click_through":
                return await self._apply_click_through(value)
            if field == "lighter_blur":
                return await self._apply_lighter_blur(value)
            return (False, f"unknown settings field: {field!r}")
        except Exception as e:  # pragma: no cover — guard against bad hooks
            log.exception("SettingsApplier.apply(%r, %r) raised", field, value)
            return (False, f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # Per-field handlers
    # ------------------------------------------------------------------

    async def _apply_voice(self, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str) or not value:
            return (False, "voice must be a non-empty string")
        if self.cascade_agent is None:
            # TODO(phase-12-04): wire real cascade_agent ref
            return (False, "cascade_agent not wired")
        self.cascade_agent.set_voice(value)
        self.config_store.voice = value
        save_config(self.config_store)
        return (True, None)

    async def _apply_mode(self, value: Any) -> tuple[bool, str | None]:
        if value not in ("hype", "coach"):
            return (False, f"mode must be 'hype' or 'coach', got {value!r}")
        if self.event_detector is None:
            # TODO(phase-12-04): wire real event_detector ref
            return (False, "event_detector not wired")
        self.event_detector.set_mode(value)
        self.config_store.mode = value
        save_config(self.config_store)
        return (True, None)

    async def _apply_genre(self, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str) or not value:
            return (False, "genre must be a non-empty string")
        if self.genre_loader is None:
            # Phase 6's genre_profile_loader is the real ref; if it isn't
            # injected we still persist (so a restart picks it up) and
            # return success with a soft warning. The settings UI logs
            # an "applied on next launch" toast in that path.
            log.warning(
                "genre_loader not wired — persisted %r but live reload deferred", value
            )
            self.config_store.genre = value
            save_config(self.config_store)
            return (True, None)
        # 250ms overlay window — the UI dims the control for this long
        # so the reload feels deliberate rather than janky.
        await asyncio.sleep(GENRE_OVERLAY_S)
        self.genre_loader.reload(value)
        self.config_store.genre = value
        save_config(self.config_store)
        return (True, None)

    async def _apply_output_device(self, value: Any) -> tuple[bool, str | None]:
        # Accept str or None (auto). Reject other types.
        if value is not None and not isinstance(value, str):
            return (False, "output_device_id must be string or null")
        if self.audio_core is None:
            # TODO(phase-12-04): wire real audio_core ref
            return (False, "audio_core not wired")
        self.audio_core.restart_output(value)
        self.config_store.output_device_id = value
        save_config(self.config_store)
        return (True, None)

    async def _apply_output_profile(self, value: Any) -> tuple[bool, str | None]:
        if value not in ("hp", "spk"):
            return (False, f"output_profile must be 'hp' or 'spk', got {value!r}")
        if self.audio_core is None:
            # TODO(phase-12-04): wire real audio_core ref
            return (False, "audio_core not wired")
        self.audio_core.set_mic_gating_profile(value)
        self.config_store.output_profile = value
        save_config(self.config_store)
        return (True, None)

    async def _apply_retention(self, value: Any) -> tuple[bool, str | None]:
        try:
            iv = int(value)
        except (TypeError, ValueError):
            return (False, f"retention_days must be an integer, got {value!r}")
        if iv < 0:
            return (False, "retention_days must be ≥ 0")
        # No runtime hook — Phase 15 reads this at boot to prune session
        # recordings. Persist only.
        self.config_store.retention_days = iv
        save_config(self.config_store)
        return (True, None)

    async def _apply_hotkey(self, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str) or not value:
            return (False, "push_to_mute_hotkey must be a non-empty string")
        # No runtime hook — the Tauri shell owns global-shortcut binding
        # via ``tauri-plugin-global-shortcut`` and rebinds on each launch.
        # Persist only.
        self.config_store.push_to_mute_hotkey = value
        save_config(self.config_store)
        return (True, None)

    # ------------------------------------------------------------------
    # Phase 13-05 — mood + click_through
    # ------------------------------------------------------------------

    async def _apply_mood(self, value: Any) -> tuple[bool, str | None]:
        """Apply a mood swap: validate enum → write MusicState under the lock
        → persist to ConfigStore.extra → emit ipc.mascot.mood_change.

        Threat T-13-05-01: invalid mood is rejected at this trust boundary
        with ``(False, "<reason>")`` — NO silent fallback to the default.
        """
        if not isinstance(value, str) or value not in _VALID_MOODS:
            return (
                False,
                f"mood must be one of {sorted(_VALID_MOODS)}, got {value!r}",
            )
        if self.music_state is None or self.ws_bus is None:
            # No music_state / ws_bus wiring — Plan 13-05 ships before the
            # main() glue that injects them. Fail loud rather than silently
            # writing only ConfigStore (would desync the mascot renderer).
            missing: list[str] = []
            if self.music_state is None:
                missing.append("music_state")
            if self.ws_bus is None:
                missing.append("ws_bus")
            return (False, f"mood requires {', '.join(missing)} wiring")

        # Capture previous mood for the emit payload.
        previous = self.music_state.mood
        # Skip the emit when nothing actually changed — same-value sets
        # are legitimate (UI re-render) but the bus shouldn't see noise.
        if previous == value:
            return (True, None)

        with self.music_state._lock:
            self.music_state.mood = value

        # ConfigStore stores mood in ``extra`` (not a typed top-level field).
        # The Rust shell + Phase 12 settings panel persist + reload via the
        # same ``extra`` round-trip path that already preserves Phase 11
        # first_run_state keys, so the Phase 13 addition rides on top
        # without a config-store schema bump.
        self.config_store.extra["mood"] = value
        save_config(self.config_store)

        # Build + emit the mood_change envelope. The wrapper's .to_json()
        # validates against the source-of-truth schema, so any drift between
        # this Python emit and the JSON schema is caught here at runtime.
        from vibemix.ui_bus import MascotMoodChange

        msg = MascotMoodChange.make(
            mood=value,
            previous_mood=previous,
            at=time.monotonic(),
        )
        # Round-trip through the wrapper so the dict we emit matches the
        # schema-validated wire form (drops None optionals etc.).
        import json as _json

        msg_dict = _json.loads(msg.to_json())
        try:
            await self.ws_bus.emit(msg_dict)
        except Exception as e:  # pragma: no cover — bus emit fail surfaces here
            log.warning("ws_bus.emit failed for ipc.mascot.mood_change: %r", e)
            return (False, f"emit failed: {type(e).__name__}: {e}")

        return (True, None)

    async def _apply_click_through(self, value: Any) -> tuple[bool, str | None]:
        """Apply the mascot overlay's click-through toggle.

        click_through is a Rust/webview-side window concern (the mascot
        overlay uses ``set_ignore_cursor_events`` to make mouse events
        pass through to the underlying app). The sidecar's only job is to
        persist the canonical bit in ConfigStore so a relaunch restores it
        — no MusicState write, no ws_bus emit.
        """
        if not isinstance(value, bool):
            return (
                False,
                f"click_through expects bool, got {type(value).__name__}",
            )
        # Stored in ConfigStore.extra to keep the typed Phase-12 surface
        # untouched (no new top-level dataclass field, no schema bump in
        # config_store.py).
        self.config_store.extra["click_through"] = value
        save_config(self.config_store)
        return (True, None)

    # ------------------------------------------------------------------
    # Phase 14-04 — perf-blur preference
    # ------------------------------------------------------------------

    async def _apply_lighter_blur(self, value: Any) -> tuple[bool, str | None]:
        """Apply the Settings → Performance → "Lighter blur" toggle.

        Presentation-only — the user's preference for swapping the heavy
        v5 backdrop blurs for lighter variants. The webview reads it at
        boot (main.ts) and writes ``html[data-blur-perf="on"]`` which the
        tokens.css cascade (Wave 2) picks up to swap ``--blur-glass-*``
        without restart. No MusicState write, no ws_bus emit, no session
        teardown — pure persistence so next launch restores the bit.

        Threat T-14-04-03: presentation-only boolean; no PII surface.
        """
        if not isinstance(value, bool):
            return (
                False,
                f"lighter_blur expects bool, got {type(value).__name__}",
            )
        # Top-level typed field — extends the Phase 12 ConfigStore surface
        # (per Plan 14-04 ConfigStore extension) so SettingsState boot
        # snapshots can include it without an ``extra`` round-trip.
        self.config_store.lighter_blur = value
        save_config(self.config_store)
        return (True, None)


# Suppress unused-import noise — asdict is reserved for upcoming wrappers.
_ = asdict


__all__ = ["SettingsApplier", "GENRE_OVERLAY_S"]
