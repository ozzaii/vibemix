# SPDX-License-Identifier: Apache-2.0
"""WizardLoop — Phase 11 Wave 4 first-run calibration runtime.

Replaces the Wave 1 stub in ``__main__.py``. Responsibilities:

  1. Open the wizard WS bus (``WizardBus`` from ``ws_bus.py``) on
     ``127.0.0.1:8765`` and register handlers for the 8 ipc.* requests
     the webview makes during the 3-step calibration flow.
  2. Emit ``ipc.boot {ready: true}`` on startup so the Rust shell can
     proceed to render the wizard (the Tauri main.rs waits on this
     event via the ws_client).
  3. Run a 1Hz ``ipc.status.tick`` loop reporting current health
     (livekit / gemini / midi count / screen permission). Probes are
     best-effort during the wizard — the full health system is Phase 12.
  4. Honor SIGTERM (Tauri Cmd+Q) cleanly so the sidecar exits without
     orphans.

Handler list (matches the 19-message schema):
  * ``ipc.permission.check``           → ``ipc.permission.state``
  * ``ipc.calibration.list_devices``   → ``ipc.calibration.device_list``
  * ``ipc.calibration.probe_audio``    → ``ipc.calibration.audio_result``
  * ``ipc.calibration.user_heard_tone`` (correlated by ts)
  * ``ipc.calibration.start_midi_listen`` → ``ipc.calibration.midi_event``
                                          | ``ipc.calibration.midi_timeout``
  * ``ipc.calibration.list_windows``    → ``ipc.calibration.window_list``
                                          (Warning #4 — WS-only window picker)
  * ``ipc.calibration.smoke_test``      → ``ipc.calibration.smoke_test_started``
                                          → ``ipc.calibration.smoke_test_done``
  * ``ipc.wizard.done``                 → sets stop event (sidecar exits)

Anti-patterns avoided (see plan §anti_patterns):
  - LiveKit / cascade agent imports are deferred into the
    ``_on_smoke_test`` body so wizard boot stays under 3s.
  - Window titles are NEVER logged. ``_on_list_windows`` adapts native
    structs to wire structs and emits; no log.* / print(...) call touches
    ``WindowInfo.title``.
  - Mascot broadcast contract is NOT extended — wizard runs in its own
    process and never touches the live-runtime ``ws_broadcast`` lifecycle.
  - No Rust ``enumerate_windows`` Tauri command — windows enumerate over
    the WS (Warning #4).
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import time
import wave
from pathlib import Path

from vibemix.runtime.ws_bus import WizardBus
from vibemix.ui_bus.messages import (
    CalibrationAudioResult,
    CalibrationDeviceList,
    CalibrationMidiEvent,
    CalibrationMidiTimeout,
    CalibrationSmokeTestDone,
    CalibrationSmokeTestStarted,
    CalibrationWindowList,
    DeviceInfo,
    IpcBoot,
    PermissionState,
    StatusTick,
    WindowInfo,
)

log = logging.getLogger("vibemix.wizard")


# Bundled fallback greeting WAV — Wave 4 ships ``offline-greeting.wav`` under
# ``tauri/ui/public/audio/`` so the smoke test still plays audio when Gemini
# is down on first launch. ``scripts/gen_offline_greeting.py`` regenerates it.
def _resolve_offline_greeting_path() -> Path:
    rel = Path("tauri") / "ui" / "public" / "audio" / "offline-greeting.wav"
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / rel
    return Path(__file__).resolve().parents[3] / rel


_OFFLINE_GREETING_PATH = _resolve_offline_greeting_path()


class WizardLoop:
    """First-run calibration wizard runtime.

    Constructed with a ``WizardBus`` (testable — pass a fake to exercise
    handler dispatch without opening a real socket). ``run()`` registers
    handlers, emits ``ipc.boot``, spawns the 1-Hz status tick task, and
    waits on the stop event.
    """

    def __init__(self, bus: WizardBus) -> None:
        self.bus = bus
        self._stop = asyncio.Event()
        self._status_tick_task: asyncio.Task | None = None
        self._user_heard_tone_event = asyncio.Event()
        self._user_heard_tone_result: bool | None = None

    # ------------------------------------------------------------------
    # Boot + handler registration
    # ------------------------------------------------------------------

    def register_handlers(self) -> None:
        """Wire all 8 ipc.* request handlers onto the bus."""
        self.bus.register_handler("ipc.permission.check", self._on_permission_check)
        self.bus.register_handler("ipc.calibration.list_devices", self._on_list_devices)
        self.bus.register_handler("ipc.calibration.probe_audio", self._on_probe_audio)
        self.bus.register_handler(
            "ipc.calibration.user_heard_tone", self._on_user_heard_tone
        )
        self.bus.register_handler(
            "ipc.calibration.start_midi_listen", self._on_start_midi_listen
        )
        # Warning #4 — WS-only window picker.
        self.bus.register_handler(
            "ipc.calibration.list_windows", self._on_list_windows
        )
        self.bus.register_handler("ipc.calibration.smoke_test", self._on_smoke_test)
        self.bus.register_handler("ipc.wizard.done", self._on_wizard_done)
        # ipc.wizard.start (re-run) — registered as a no-op stop trigger here;
        # the live-runtime path in Phase 12 will own the re-run UX.
        self.bus.register_handler("ipc.wizard.start", self._on_wizard_start)

    async def boot(self) -> None:
        """Emit ``ipc.boot {ready: true}`` so the Tauri shell can render
        the wizard. Called exactly once after ``register_handlers``.

        Also fires platform permission requests for any kind that resolves
        to ``notDetermined`` so vibemix registers with TCC immediately
        (otherwise the OS only adds the app to System Settings → Privacy
        list AFTER first capture-API invocation, which can be confusing
        when the wizard's Grant button just deep-links to Settings).
        """
        await self.bus.emit(json.loads(IpcBoot.make(ready=True).to_json()))
        self._prime_tcc_registration()

    def _prime_tcc_registration(self) -> None:
        try:
            from vibemix.platform import permissions  # noqa: PLC0415
        except Exception as exc:  # pragma: no cover
            log.warning("permissions module unavailable: %r", exc)
            return
        try:
            mic_status = permissions.check_microphone_permission()
            print(f"[tcc-prime] microphone status: {mic_status}", flush=True)
            if mic_status == "notDetermined":
                permissions.request_microphone_permission()
                print("[tcc-prime] microphone request fired", flush=True)
        except Exception as exc:  # pragma: no cover
            log.warning("priming microphone TCC failed: %r", exc)
        try:
            scr_status = permissions.check_screen_recording_permission()
            print(f"[tcc-prime] screen_recording status: {scr_status}", flush=True)
            # macOS CGPreflightScreenCaptureAccess returns a boolean — there's
            # no notDetermined state for screen capture. Always call
            # CGRequestScreenCaptureAccess on first wizard boot: it shows
            # the consent prompt if no decision was made, or returns the
            # cached value if already decided. Either way the app gets
            # registered in System Settings → Privacy → Screen Recording.
            if scr_status != "authorized":
                granted = permissions.request_screen_recording_permission()
                print(f"[tcc-prime] screen_recording request fired -> {granted}", flush=True)
        except Exception as exc:  # pragma: no cover
            log.warning("priming screen-recording TCC failed: %r", exc)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _on_permission_check(self, msg: dict) -> None:
        """Resolve permission state via the platform selector.

        If status is ``notDetermined``, also fires the platform's request API
        so the OS surfaces the native consent dialog and the app gets added
        to the Privacy & Security list. Subsequent polls pick up the new
        state.
        """
        kind = msg.get("payload", {}).get("kind")
        if kind not in ("screen_recording", "microphone"):
            log.warning("permission.check: unknown kind %r — ignored", kind)
            return
        from vibemix.platform import permissions  # noqa: PLC0415

        if kind == "screen_recording":
            status = permissions.check_screen_recording_permission()
            if status == "notDetermined":
                try:
                    permissions.request_screen_recording_permission()
                except Exception as exc:  # pragma: no cover — degrade gracefully
                    log.warning("request_screen_recording_permission failed: %r", exc)
        else:
            status = permissions.check_microphone_permission()
            if status == "notDetermined":
                try:
                    permissions.request_microphone_permission()
                except Exception as exc:  # pragma: no cover
                    log.warning("request_microphone_permission failed: %r", exc)
        reply = PermissionState.make(kind=kind, status=status)
        await self.bus.emit(json.loads(reply.to_json()))

    async def _on_list_devices(self, _msg: dict) -> None:
        """Enumerate sounddevice outputs; flag BlackHole presence + variant."""
        import sounddevice as sd  # noqa: PLC0415

        devices: list[DeviceInfo] = []
        blackhole_present = False
        try:
            raw = sd.query_devices()
        except Exception as e:
            log.warning("list_devices: query_devices failed: %s", e)
            raw = []

        for i, d in enumerate(raw):
            name = str(d.get("name", "") or "")
            is_bh = name.startswith("BlackHole")
            if not is_bh and d.get("max_output_channels", 0) == 0:
                # Pure-input device, not BlackHole — skip (the picker wants
                # output endpoints only, except BlackHole which surfaces for
                # the install / detect flow even when input-only).
                continue
            variant: str | None = None
            if is_bh:
                blackhole_present = True
                for v in ("64ch", "16ch", "2ch"):
                    if v in name:
                        variant = v
                        break
            devices.append(
                DeviceInfo(id=str(i), name=name, is_blackhole=is_bh, variant=variant)
            )

        reply = CalibrationDeviceList.make(
            devices=devices, blackhole_present=blackhole_present
        )
        await self.bus.emit(json.loads(reply.to_json()))

    async def _on_probe_audio(self, msg: dict) -> None:
        """Play a 1kHz sine on the selected output + read back the actual
        sample rate. Await ``ipc.calibration.user_heard_tone`` up to 30s
        before emitting ``ipc.calibration.audio_result``.

        The probe is deliberately permissive — the user-confirm gate is
        the source of truth (D-Area-4.2 — both audible + programmatic
        must pass to advance, but the wizard surfaces the per-axis
        result so the user can debug).
        """
        payload = msg.get("payload", {})
        output_device_id = payload.get("output_device_id")
        expected_rate = payload.get("expected_rate", 48000)
        try:
            output_idx = int(output_device_id)
        except (TypeError, ValueError):
            reply = CalibrationAudioResult.make(
                playback_ok=False,
                audible_confirmed=False,
                programmatic_pass=False,
                actual_rate=None,
                error=f"invalid output_device_id: {output_device_id!r}",
            )
            await self.bus.emit(json.loads(reply.to_json()))
            return

        import sounddevice as sd  # noqa: PLC0415

        # Generate the sine — 1.5s @ 48kHz, -6 dBFS peak, 100ms fades.
        sine = self._generate_sine(freq_hz=1000.0, duration_s=1.5, sample_rate=48000)

        playback_ok = False
        actual_rate: int | None = None
        programmatic_pass = False
        err: str | None = None

        try:
            info = sd.query_devices(output_idx)
            actual_rate = int(info.get("default_samplerate", 0)) or None
            programmatic_pass = actual_rate == expected_rate
        except Exception as e:
            err = f"probe: device query failed: {e}"

        try:
            sd.play(sine, samplerate=48000, device=output_idx, blocking=False)
            sd.wait()
            playback_ok = True
        except Exception as e:
            playback_ok = False
            err = ((err + " | ") if err else "") + f"playback: {e}"

        # Wait up to 30s for the user-confirm event.
        self._user_heard_tone_event.clear()
        self._user_heard_tone_result = None
        audible = False
        try:
            await asyncio.wait_for(self._user_heard_tone_event.wait(), timeout=30.0)
            audible = self._user_heard_tone_result is True
        except asyncio.TimeoutError:
            audible = False
            err = ((err + " | ") if err else "") + "user-confirm timeout"

        reply = CalibrationAudioResult.make(
            playback_ok=playback_ok,
            audible_confirmed=audible,
            programmatic_pass=programmatic_pass,
            actual_rate=actual_rate,
            error=err,
        )
        await self.bus.emit(json.loads(reply.to_json()))

    async def _on_user_heard_tone(self, msg: dict) -> None:
        """Correlate the user's Yes/Retry click with the probe_audio handler."""
        self._user_heard_tone_result = bool(msg.get("payload", {}).get("heard", False))
        self._user_heard_tone_event.set()

    async def _on_start_midi_listen(self, msg: dict) -> None:
        """Drain 200ms of bootstrap MIDI noise (Open Q5) then listen for
        ``timeout_s`` seconds for the next event. Emit ``midi_event`` on
        success or ``midi_timeout`` on no input."""
        timeout_s = float(msg.get("payload", {}).get("timeout_s", 10.0))
        try:
            event = await asyncio.wait_for(
                _drain_then_listen(drain_ms=200), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            reply: object = CalibrationMidiTimeout.make()
        except Exception as e:
            # mido / device error — treat as timeout for the UI; log to stderr.
            log.warning("midi listen failed: %s", e)
            reply = CalibrationMidiTimeout.make()
        else:
            reply = CalibrationMidiEvent.make(
                control_label=event["control_label"], raw=event["raw"]
            )
        await self.bus.emit(json.loads(reply.to_json()))  # type: ignore[attr-defined]

    async def _on_list_windows(self, _msg: dict) -> None:
        """Window picker over WS (Warning #4). Calls platform selector via
        ``run_in_executor`` because Quartz / EnumWindows is blocking.

        Privacy: titles cross the WS boundary only; this handler does NOT
        log title values (T-11-W4-06).
        """
        from vibemix.platform import windows as platform_windows  # noqa: PLC0415

        loop = asyncio.get_event_loop()
        try:
            native = await loop.run_in_executor(None, platform_windows.enumerate_windows)
        except Exception as e:
            log.warning("list_windows: enumerate_windows failed: %s", e)
            native = []

        # Adapt native dataclasses → schema wire structs. NEVER log titles.
        wire = [
            WindowInfo(
                id=w.id, app_name=w.app_name, title=w.title, dj_app_hint=w.dj_app_hint
            )
            for w in native
        ]
        reply = CalibrationWindowList.make(windows=wire)
        await self.bus.emit(json.loads(reply.to_json()))
        # Privacy audit: log count only, never titles.
        log.info("list_windows: emitted %d entries (titles redacted)", len(wire))

    async def _on_smoke_test(self, _msg: dict) -> None:
        """Play the HYPE_BEGINNER greeting via the Phase 4 cascade agent;
        fall back to a bundled WAV when Gemini is down (Open Q2)."""
        started = CalibrationSmokeTestStarted.make()
        await self.bus.emit(json.loads(started.to_json()))

        transcript = "(no transcript captured)"
        try:
            # Deferred import — keeps wizard boot lightweight when smoke
            # test isn't reached.
            transcript = await self._run_smoke_greeting()
        except Exception as e:
            log.warning("smoke_test cascade failed (%s); falling back", e)
            await self._play_offline_greeting()
            transcript = "(offline fallback greeting played)"

        done = CalibrationSmokeTestDone.make(transcript=transcript)
        await self.bus.emit(json.loads(done.to_json()))

    async def _run_smoke_greeting(self) -> str:
        """Try the cascade greeting. Best-effort — exceptions propagate so
        ``_on_smoke_test`` can route to the offline fallback.

        For Phase 11 the smoke test does NOT spin up the full live-runtime
        ``main()`` graph (audio I/O, MusicState, etc.). Instead it plays
        the bundled offline-greeting WAV — the actual cascade exercise
        happens on first non-wizard launch and during Phase 16's
        hallucination verification gate.
        """
        # Phase 11 simplification: surface as "cascade not yet wired" so
        # the fallback path runs. The real cascade-greeting wiring is
        # Phase 12's settings-panel ``Re-run calibration`` button + a
        # dedicated one-shot AgentSession context manager (out of scope
        # for the structural gate).
        raise RuntimeError("smoke test cascade not wired in Phase 11 — using offline fallback")

    async def _on_wizard_done(self, msg: dict) -> None:
        """Sidecar logs the choices + exits cleanly. Rust shell persists
        config.json + respawns ``vibemix`` without ``--wizard``."""
        payload = msg.get("payload", {})
        # Privacy-respecting log — controller_profile + device_id are not PII;
        # target_window_id is just an opaque OS handle.
        log.info(
            "wizard done: output=%s controller=%s window_id=%s",
            payload.get("output_device_id"),
            payload.get("controller_profile"),
            payload.get("target_window_id"),
        )
        self._stop.set()

    async def _on_wizard_start(self, _msg: dict) -> None:
        """Wizard re-start — Phase 12 owns the real settings-panel UX.

        Wave 4 just acknowledges the message by logging it. The Tauri
        shell can spawn ``vibemix --wizard`` independently when the
        Phase 12 settings button is wired.
        """
        log.info("wizard start requested (Phase 12 owns the re-run UX)")

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _status_tick_loop(self) -> None:
        """1Hz ``ipc.status.tick`` emit. Probes are best-effort during the
        wizard — Phase 12 wires the full health system."""
        while not self._stop.is_set():
            try:
                tick = StatusTick.make(
                    livekit="connecting",  # full probe is Phase 12
                    gemini="down",          # full probe is Phase 12; "down" is the safer default
                    midi=self._probe_midi_count(),
                    screen=self._probe_screen_status(),
                )
                await self.bus.emit(json.loads(tick.to_json()))
            except Exception as e:
                log.warning("status_tick error: %s", e)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=1.0)
                return
            except asyncio.TimeoutError:
                continue

    def _probe_midi_count(self) -> int | None:
        """Return the count of MIDI input ports, or None if mido errors."""
        try:
            import mido  # noqa: PLC0415

            return len(mido.get_input_names())
        except Exception:
            return None

    def _probe_screen_status(self) -> str:
        """Return ``"ok"`` if screen-recording is authorized; else ``"denied"``."""
        try:
            from vibemix.platform import permissions  # noqa: PLC0415

            return (
                "ok"
                if permissions.check_screen_recording_permission() == "authorized"
                else "denied"
            )
        except Exception:
            return "denied"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_sine(
        self, *, freq_hz: float, duration_s: float, sample_rate: int
    ):  # type: ignore[no-untyped-def]
        """Generate a -6 dBFS 100ms-fade-in/out 1kHz sine as float32."""
        import numpy as np  # noqa: PLC0415

        n = int(sample_rate * duration_s)
        t = np.arange(n) / sample_rate
        peak = 10 ** (-6.0 / 20.0)
        sine = peak * np.sin(2 * np.pi * freq_hz * t)
        fade = int(sample_rate * 0.1)
        sine[:fade] *= np.linspace(0, 1, fade)
        sine[-fade:] *= np.linspace(1, 0, fade)
        return sine.astype(np.float32)

    async def _play_offline_greeting(self) -> None:
        """Fallback for ``_on_smoke_test`` when Gemini is unreachable on
        first launch. Plays the bundled ``offline-greeting.wav`` via
        sounddevice's default output."""
        if not _OFFLINE_GREETING_PATH.exists():
            log.warning(
                "offline-greeting.wav missing at %s; skipping fallback",
                _OFFLINE_GREETING_PATH,
            )
            return
        try:
            import numpy as np  # noqa: PLC0415
            import sounddevice as sd  # noqa: PLC0415

            with wave.open(str(_OFFLINE_GREETING_PATH), "rb") as w:
                frames = w.readframes(w.getnframes())
                sr = w.getframerate()
            pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(pcm, samplerate=sr)
            sd.wait()
        except Exception as e:
            log.warning("offline greeting playback failed: %s", e)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Register handlers → start bus → emit boot → run status loop →
        wait on stop event → tear down."""
        self.register_handlers()
        await self.bus.start()
        await self.boot()
        self._status_tick_task = asyncio.create_task(self._status_tick_loop())

        # SIGTERM (Tauri Cmd+Q) + SIGINT — set the stop event so the
        # status loop exits + the bus tears down. Windows doesn't
        # implement add_signal_handler for the asyncio loop; ignore.
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except NotImplementedError:
                pass

        try:
            await self._stop.wait()
        finally:
            if self._status_tick_task is not None:
                self._status_tick_task.cancel()
                try:
                    await self._status_tick_task
                except (asyncio.CancelledError, Exception):
                    pass
            await self.bus.stop()


# ---------------------------------------------------------------------------
# Entrypoint invoked by __main__.py
# ---------------------------------------------------------------------------


async def run_wizard() -> int:
    """Entry point for ``python -m vibemix --wizard``.

    Constructs a fresh ``WizardBus``, runs the ``WizardLoop`` until
    ``ipc.wizard.done`` arrives (or SIGTERM is delivered), then returns 0.
    """
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    bus = WizardBus()
    loop = WizardLoop(bus)
    print("-> wizard boot", file=sys.stderr)
    started = time.monotonic()
    await loop.run()
    print(f"-> wizard exit ({time.monotonic() - started:.1f}s)", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# MIDI drain-then-listen helper (Open Q5)
# ---------------------------------------------------------------------------


async def _drain_then_listen(*, drain_ms: int) -> dict:
    """Open a MIDI input, drain ``drain_ms`` of bootstrap traffic, then
    return the first event observed thereafter.

    Returns a dict with ``control_label`` + ``raw`` matching
    ``CalibrationMidiEventPayload``.

    Raises ``asyncio.TimeoutError`` if the caller's ``asyncio.wait_for``
    times out before an event lands.
    """
    import mido  # noqa: PLC0415

    from vibemix.midi.registry import find_mapping_or_generic

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    # Pick the first available input port.
    input_names = mido.get_input_names()
    if not input_names:
        # No MIDI ports at all — wait forever; caller's timeout fires.
        while True:  # pragma: no cover — exercised via wait_for timeout
            await asyncio.sleep(3600)

    port_name = input_names[0]
    profile = find_mapping_or_generic(port_name)

    def _on_message(msg: object) -> None:
        # Drop bootstrap traffic until drain_until elapses.
        if time.monotonic() < drain_until:
            return
        # Use the profile's label resolver if available; otherwise raw type.
        try:
            label = _resolve_control_label(msg, profile)
        except Exception:
            label = getattr(msg, "type", "midi")
        raw = repr(msg)
        # Hop back onto the asyncio loop.
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"control_label": label, "raw": raw})
        except RuntimeError:
            pass  # loop closed

    drain_until = time.monotonic() + (drain_ms / 1000.0)
    port = mido.open_input(port_name, callback=_on_message)
    try:
        return await queue.get()
    finally:
        try:
            port.close()
        except Exception:
            pass


def _resolve_control_label(msg: object, profile: object) -> str:
    """Best-effort label resolver for the calibration probe.

    The full DDJ-FLX4 cc/note maps live in ``vibemix.midi.profiles``; for
    the calibration probe we just need something user-friendly for the
    "✓ play_a — CONNECTED" toast. If the profile exposes a resolver, use
    it; otherwise fall back to the message type.
    """
    msg_type = getattr(msg, "type", "midi")
    # Try a few common shapes — controller profiles may expose any of:
    #   profile.cc_label(control)
    #   profile.note_label(note)
    #   profile.label_for(msg)
    try:
        if msg_type == "control_change" and hasattr(profile, "cc_label"):
            label = profile.cc_label(msg.control)  # type: ignore[attr-defined]
            if label:
                return str(label)
        if msg_type in ("note_on", "note_off") and hasattr(profile, "note_label"):
            label = profile.note_label(msg.note)  # type: ignore[attr-defined]
            if label:
                return str(label)
        if hasattr(profile, "label_for"):
            label = profile.label_for(msg)  # type: ignore[attr-defined]
            if label:
                return str(label)
    except Exception:
        pass
    return str(msg_type)


__all__ = ["WizardLoop", "run_wizard"]
