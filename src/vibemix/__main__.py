# SPDX-License-Identifier: Apache-2.0
"""vibemix — async main() orchestrator. Entry point for ``python -m vibemix``.

Verbatim port of ``cohost_v4.py:1925-2080`` with three structural adjustments
demanded by the new package layout:

1. **AudioMacOS as the firewall.** v4's inline ``sd.InputStream`` /
   ``start_input_to_session`` / ``start_playback_stream`` /
   ``start_passthrough_stream`` are replaced by ``AudioMacOS.open_capture``
   / ``open_voice_output`` / ``open_passthrough_output`` /
   ``open_mic_capture``. The v4 callback bodies live in 4 small factory
   functions in this module.
2. **Phase 2/3 backends.** ``ScreenMacOS`` / ``MidiMacOS`` / ``TrackMacOS``
   wrap the v4 inner instances (``screen_buf`` / ``controller_state`` /
   ``track_info``) and expose them as attributes for ``state_refresh_loop``
   to consume unchanged.
3. **All imports are ``vibemix.*``.** No reference to cohost_v4 at runtime.

Critical ordering invariants preserved from v4:
- ``session.output.audio = PlaybackQueueAudioOutput(...)`` is assigned BEFORE
  ``await session.start(agent)`` (v4:2030-2033).
- Two ``AudioBuffer`` instances: 140s gain-boosted state buffer +
  ``INVOKE_AUDIO_SECONDS + 5.0`` natural-level clean buffer (v4:1948-1949).
- MIDI listener thread spawned AFTER ``session.start`` (v4:2039-2043).
- Input stream opened AFTER the 6 asyncio tasks are created
  (state_refresh_loop must be running before audio starts pushing).
- SIGINT/SIGTERM handlers via ``loop.add_signal_handler``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import signal
import sys
import threading
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import numpy as np
from dotenv import load_dotenv

from vibemix import __version__
from vibemix._main_helpers import apply_genre_env

if TYPE_CHECKING:
    from vibemix.library.codex_curate import CodexCurateResult

# Re-exported for test_main_smoke SMOKE-07 (asserts __main__ surfaces the
# persona cell symbol) — not referenced in code here, so noqa the F401.
from vibemix.agent.config import (
    INPUT_DEVICE,
    LLM_MODEL,
    MIC_DEVICE,
    OPENROUTER_LLM_MODEL,
    OPENROUTER_TTS_MODEL,
    OUTPUT_DEVICE,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)
from vibemix.agent.persona import SYSTEM_INSTRUCTION  # noqa: F401
from vibemix.audio import (
    INPUT_CHUNK_FRAMES,
    INPUT_SR_NATIVE,
    INPUT_SR_TARGET,
    INVOKE_AUDIO_SECONDS,
    LOOKAHEAD_SECONDS,
    LOOKAHEAD_WINDOW_SECONDS,
    MIC_GAIN,
    MIC_GAIN_AT_AI_TALK,
    MUSIC_GAIN_TO_GEMINI,
    OUTPUT_BLOCKSIZE,
    OUTPUT_SR,
    PASSTHROUGH_GAIN,
    VOICE_BLOCKSIZE,
    AudioBuffer,
    BufferRegistry,
    Levels,
    LookaheadProvider,
    MicBuffer,
    PassthroughBuffer,
    PlaybackQueue,
    VoiceRecorder,
)
from vibemix.audio.deck_capture import (
    DeckAudioCapture,
    deck_audio_routing_from_env,
    rekordbox_deck_output_routing_hint,
)
from vibemix.audio.recorder import sweep_crashed_sessions
from vibemix.audio.resample import resample_audio
from vibemix.coach import (
    STRIPPED_RATE_THRESHOLD,
    CitationLinter,
    StrippedRateTracker,
)
from vibemix.library.prepared_pool import (
    load_latest_prepared_pool as _load_latest_prepared_pool,
)
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.platform import AudioMacOS, MidiMacOS, ScreenMacOS, TrackMacOS
from vibemix.profile import load_consent, load_profile, render_profile_for_cache
from vibemix.runtime import coach_loop, diag_loop, watch_parent, ws_broadcast
from vibemix.runtime.cancel import CancelGate
from vibemix.runtime.config_store import app_data_dir, load_config
from vibemix.runtime.recordings_index import run_retention_sweep
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import (
    EventDetector,
    EvidenceRegistry,
    MusicState,
    state_refresh_loop,
)
from vibemix.state.deck_context import DECK_CONTEXT_TRUSTED_SOURCES
from vibemix.state.deck_poller import DeckPoller

# Cohost-only imports are resolved lazily so library/model CLI commands do not
# load LiveKit provider plugins, Google Cloud STT/TTS, or OpenAI TTS plumbing at
# module import time. Tests patch these module globals before ``main()`` runs,
# so the resolver preserves any non-None injected value.
AgentSession = None
DJCoHostAgent = None
PlaybackQueueAudioOutput = None
build_llm = None
build_proxy_genai_client = None
build_tts_chain = None
get_or_create_install_uuid = None
get_or_refresh_jwt = None
GeminiContextCache = None


class _LazyGenAI:
    """Import ``google.genai`` only when a Gemini client is actually needed."""

    def __getattr__(self, name: str):
        from google import genai as _genai

        return getattr(_genai, name)


genai = _LazyGenAI()


def _ensure_context_cache_dep() -> None:
    global GeminiContextCache
    if GeminiContextCache is None:
        from vibemix.agent.cache import GeminiContextCache as _GeminiContextCache

        GeminiContextCache = _GeminiContextCache


def _ensure_proxy_auth_deps() -> None:
    global get_or_create_install_uuid, get_or_refresh_jwt
    if get_or_create_install_uuid is None:
        from vibemix.agent.install_uuid import get_or_create_install_uuid as _get_uuid

        get_or_create_install_uuid = _get_uuid
    if get_or_refresh_jwt is None:
        from vibemix.agent.jwt_cache import get_or_refresh_jwt as _get_jwt

        get_or_refresh_jwt = _get_jwt


def _ensure_live_llm_tts_deps() -> None:
    global build_llm, build_tts_chain
    if build_llm is None:
        from vibemix.agent.llm_factory import build_llm as _build_llm

        build_llm = _build_llm
    if build_tts_chain is None:
        from vibemix.agent.tts_chain import build_tts_chain as _build_tts_chain

        build_tts_chain = _build_tts_chain


def _ensure_proxy_client_dep() -> None:
    global build_proxy_genai_client
    if build_proxy_genai_client is None:
        from vibemix.agent.proxy_client import (
            build_proxy_genai_client as _build_proxy_genai_client,
        )

        build_proxy_genai_client = _build_proxy_genai_client


def _ensure_live_session_deps() -> None:
    global AgentSession, DJCoHostAgent, PlaybackQueueAudioOutput
    if AgentSession is None:
        from livekit.agents import AgentSession as _AgentSession

        AgentSession = _AgentSession
    if DJCoHostAgent is None:
        from vibemix.agent.dj_cohost import DJCoHostAgent as _DJCoHostAgent

        DJCoHostAgent = _DJCoHostAgent
    if PlaybackQueueAudioOutput is None:
        from vibemix.agent.playback_sink import (
            PlaybackQueueAudioOutput as _PlaybackQueueAudioOutput,
        )

        PlaybackQueueAudioOutput = _PlaybackQueueAudioOutput


def _load_env_robust() -> None:
    """Load ``.env`` from any of the known vibemix locations, robust to CWD.

    ``load_dotenv()`` with no args walks up from the *current working
    directory*. That is correct for the dev path (the Tauri shell sets the
    sidecar cwd to the repo root, where ``.env`` lives), but FAILS for the
    bundled PyInstaller binary: a Finder/Dock-launched ``.app`` runs with
    cwd ``/``, so ``find_dotenv()`` never sees the repo ``.env`` and
    ``GEMINI_API_KEY`` is silently absent — the exact "co-host never speaks"
    release blocker.

    We therefore probe an ordered list of candidate ``.env`` paths and load
    the first that exists. ``.env`` values WIN (``override=True``): the
    on-disk ``.env`` is the source of truth for the dev/local path, so a
    stale/ghost ``GEMINI_API_KEY`` lingering in the shell process environment
    can no longer shadow the funded key in ``.env`` (WIRE-06 — the diagnosed
    live bug where a dead ghost key ``...QSFyBQ`` shadowed the funded
    ``.env`` key ``...32u744``, leaving the runtime on a key with no credits).
    SECURITY: no key is ever embedded here — every candidate is a runtime
    file or the inherited process env.

    KAAN-ACTION (A1 — Tauri-injection precedence reversal): this flip
    DELIBERATELY REVERSES the prior ``override=False`` decision, which let a
    key injected into the process env by the Tauri shell win over a stale
    on-disk ``.env``. If a Tauri-bundled install ever needs to inject the key
    via process env INSTEAD of ``.env`` (so the process-env key must win),
    THIS is the knob to revisit — flip back to ``override=False`` here. See
    WIRE-06 / 77-RESEARCH Pitfall 3.

    Candidate order (first existing wins):
      1. CWD-relative ``.env`` (``find_dotenv`` — the dev/repo path).
      2. ``app_data_dir()/.env`` — OS-aware per-user config dir. This is the
         supported place to drop a key for a bundled install
         (``~/Library/Application Support/vibemix/.env`` on macOS) without
         touching the signed bundle.
      3. A ``.env`` next to the running executable / its parent dirs — covers
         a PyInstaller ``--onedir`` bundle shipping a ``.env`` resource.
    """
    from dotenv import find_dotenv

    candidates: list[Path] = []

    # 1. CWD-relative (dev / repo path). find_dotenv returns "" when none.
    found = find_dotenv(usecwd=True)
    if found:
        candidates.append(Path(found))

    # 2. Per-user app data dir — the bundled-install drop point.
    try:
        from vibemix.runtime.config_store import app_data_dir as _add

        candidates.append(_add() / ".env")
    except Exception:
        pass

    # 3. Alongside the frozen executable (PyInstaller) and its parents.
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / ".env")
        candidates.append(exe_dir.parent / ".env")
    except Exception:
        pass

    loaded_from: str | None = None
    for cand in candidates:
        try:
            if cand.is_file():
                load_dotenv(dotenv_path=str(cand), override=True)
                if loaded_from is None:
                    loaded_from = str(cand)
        except Exception:
            continue

    if loaded_from is None:
        # No .env anywhere — rely entirely on the inherited process env
        # (the Tauri shell forwards GEMINI_API_KEY / OPENROUTER_API_KEY).
        load_dotenv(override=True)

    # Diagnostic to stderr — but ONLY for the live-runtime / wizard / session
    # paths the Tauri log captures. The `vibemix library <sub>` CLI emits a
    # strict JSON-only stderr contract (parsed by tests/scripts/*), so we must
    # not prepend a banner there. argv[1] == "library" is the dispatch guard
    # used by cli_entry below.
    _argv = sys.argv[1:]
    # Phase 81 — the `vibemix bench <sub>` CLI is a dev-instrument surface; like
    # `library`, it must not carry the live-runtime startup banner on stderr.
    if not (_argv and _argv[0] in ("library", "bench")):
        if loaded_from is None:
            print(
                "-> env: no .env found; using inherited process environment",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(f"-> env: loaded {loaded_from}", file=sys.stderr, flush=True)


_load_env_robust()


# =============================================================================
# Phase 15 — recordings root resolver
# =============================================================================


def _resolve_recordings_root() -> os.PathLike[str]:
    """Return the OS-aware recordings root: ``app_data_dir() / "recordings"``.

    macOS:   ``~/Library/Application Support/vibemix/recordings``
    Windows: ``%APPDATA%/vibemix/recordings``
    Linux:   ``$XDG_CONFIG_HOME/vibemix/recordings`` (or ``~/.config/...``)

    Matches the Tauri assetProtocol scope set in ``tauri.conf.json5`` so
    ``<audio src="asset://...">`` resolves under the same path the sidecar
    writes to. Pure forwarder over ``app_data_dir`` from Phase 12
    ConfigStore — no caching, no mkdir (``VoiceRecorder.__init__`` mkdirs
    with mode=0o700 per RESEARCH Security V8).
    """
    return app_data_dir() / "recordings"


# =============================================================================
# CLI argument parsing
# =============================================================================


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args. ``--version`` short-circuits via argparse's action.

    ``--wizard`` runs the first-run calibration wizard. Tauri can spawn the
    PyInstaller-built ``vibemix-core`` binary with this flag for setup, then
    use the default full live runtime afterward.
    """
    parser = argparse.ArgumentParser(prog="vibemix", description="Open-source AI DJ co-host.")
    parser.add_argument("--version", action="version", version=f"vibemix {__version__}")
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Run the first-run calibration wizard.",
    )
    # Standalone session-loop runtime for sidecar-only IPC. The full live
    # runtime (audio + cascade) is the default (no flag); ``--session`` is kept
    # for diagnostic/bootstrap checks that only need the snapshot bus.
    parser.add_argument(
        "--session",
        action="store_true",
        help="Run the standalone session IPC loop (diagnostic/bootstrap mode; no cascade graph).",
    )
    # Post-session debrief sidecar. The flag name, port, and message types are
    # stable because the Tauri shell and debrief window invoke this path.
    # ``nargs="?"`` lets the flag take an optional SESSION_DIR — bare
    # ``--debrief`` registers the smoke / port-reservation banner; with a
    # path it logs the reserved-session intent. Absence keeps ``None`` so
    # the dispatch in cli_entry can distinguish "no flag" from "empty arg".
    parser.add_argument(
        "--debrief",
        nargs="?",
        const="",
        default=None,
        metavar="SESSION_DIR",
        help=(
            "Run as post-session DEBRIEF sidecar — binds the DEBRIEF ws bus on "
            "127.0.0.1:8766, emits the 3 reserved DEBRIEF schemas only, never "
            "engages audio I/O or LiveKit. SESSION_DIR is the path to a "
            "closed recordings/* session; omit for a no-op smoke."
        ),
    )
    # v8.0 LOG-04 — opt-in verbose logging. Default OFF keeps stderr +
    # events.jsonl byte-identical to baseline; on, the live path appends a
    # consolidated per-turn ``reaction_evidence`` digest (evidence packet +
    # citation-gate decision). Mirrors the VIBEMIX_DEBUG_LOG env (the env is
    # the floor; this flag can only raise verbosity — see runtime.debug_flags).
    parser.add_argument(
        "--debug-log",
        action="store_true",
        help=(
            "Enable verbose diagnostics (per-turn evidence + citation-gate "
            "decision to events.jsonl). Default off; also set by "
            "VIBEMIX_DEBUG_LOG=1. Does not change the default console output."
        ),
    )
    return parser.parse_args(argv)


# =============================================================================
# DEBRIEF sidecar — Phase 25 Plan 25-03 architectural slot
# =============================================================================


# Port reserved for the v2.1 DEBRIEF ws bus. Lives separate from the live
# mascot bus on 8765 (CONTEXT D-Area-1.1 / D-Area-1.3). v2.0 does NOT bind
# this port — the constant is a forward-compatibility reservation only. v2.1
# wires the real listener + 3-message emit path behind ``--debrief``.
DEBRIEF_PORT: int = 8766


def _run_debrief_sidecar(session_dir: str) -> None:
    """Plan 29-02 DEBRIEF sidecar dispatch.

    ``session_dir`` semantics:

      * ``""`` (sentinel): bare ``--debrief`` was passed — log a banner
        without doing work (useful for verifying flag plumbing).
      * non-empty path: invoke :func:`vibemix.debrief.main.run` which
        canonicalizes the path, validates it lives under recordings
        root, runs the cache-hit fast path / first-time generation, and
        starts the WS server on 127.0.0.1:DEBRIEF_PORT (8766).

    Errors from the orchestrator surface as ``ipc.debrief.error`` frames
    over the WS bus, then the process exits cleanly. See plan 29-02
    SUMMARY for the reason codes.
    """
    import logging

    logger = logging.getLogger("vibemix.debrief")
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    if not session_dir:
        logger.info(
            "[debrief] no session_dir provided; port %d reserved.",
            DEBRIEF_PORT,
        )
        return
    logger.info("[debrief] starting sidecar for %r (port %d)", session_dir, DEBRIEF_PORT)
    from vibemix.debrief.main import run as run_debrief

    run_debrief(session_dir, port=DEBRIEF_PORT)


# =============================================================================
# Wizard entrypoint — opens the real WizardLoop runtime.
# =============================================================================
#
# ``vibemix.runtime.wizard.run_wizard`` opens the WS bus, registers the ipc.*
# handlers, drives calibration + smoke test, and exits cleanly on
# ``ipc.wizard.done``.


# =============================================================================
# 4 callback factories — match v4 callback bodies verbatim
# =============================================================================


def _input_callback_factory(
    levels: Levels,
    passthrough: PassthroughBuffer,
    mic: MicBuffer,
    audio_buf: AudioBuffer,
    clean_audio_buf: AudioBuffer,
    recorder: VoiceRecorder,
    deck_audio_capture: DeckAudioCapture | None = None,
    audio_capture_context: dict[str, object] | None = None,
):
    """Verbatim port of cohost_v4.py:912-945 input stream callback."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        if deck_audio_capture is not None:
            captured = deck_audio_capture.process(indata, source_sr=INPUT_SR_NATIVE)
            passthrough_audio = captured.passthrough_stereo
            music48 = captured.master_mono
            if audio_capture_context is not None:
                audio_capture_context.update(deck_audio_capture.context())
        else:
            passthrough_audio = indata[:, :2]
            if passthrough_audio.shape[1] == 1:
                passthrough_audio = np.repeat(passthrough_audio, 2, axis=1)
            music48 = indata.mean(axis=1).astype(np.float32)

        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((passthrough_audio * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(passthrough_audio.astype(np.float32).tobytes())

        # Mic is captured on a SEPARATE stream (mic_buf) for KAAN_SPOKE
        # detection via levels.mic; NEVER mix it into the music buffers —
        # otherwise Gemini hears Kaan's voice as "vocals" in the track.
        mic.pull(len(music48))  # keep cadence aligned, discard samples

        state48 = music48 * MUSIC_GAIN_TO_GEMINI
        state_pcm_48k = np.clip(state48 * 32767.0, -32768, 32767).astype(np.int16)
        clean48 = music48

        try:
            state16f = resample_audio(state48, source_sr=INPUT_SR_NATIVE, target_sr=INPUT_SR_TARGET)
            state_pcm_16k = np.clip(state16f * 32767.0, -32768, 32767).astype(np.int16)
            audio_buf.push(state_pcm_16k)
            recorder.push_input(state_pcm_16k.tobytes())

            clean16f = resample_audio(clean48, source_sr=INPUT_SR_NATIVE, target_sr=INPUT_SR_TARGET)
            clean_pcm_16k = np.clip(clean16f * 32767.0, -32768, 32767).astype(np.int16)
            clean_audio_buf.push(clean_pcm_16k)
        except Exception as e:
            print(f"[buf push err] {e}", file=sys.stderr)

        levels.update_music(state_pcm_48k)

    return callback


def _deck_audio_auto_requested() -> bool:
    return str(os.environ.get("VIBEMIX_DECK_AUDIO_CHANNELS") or "").strip().lower() in {
        "auto",
        "rekordbox",
    }


def _input_device_env_is_explicit() -> bool:
    return bool(str(os.environ.get("VIBEMIX_INPUT_DEVICE") or "").strip())


def _maybe_upgrade_input_device_for_deck_audio(
    audio_backend: AudioMacOS,
    *,
    input_idx: int,
    input_device_name: str,
    base_audio_capture_context: dict[str, object],
    deck_audio_routing: Any,
) -> tuple[int, str, dict[str, object], Any]:
    """Prefer multichannel BlackHole when explicit deck-auto routing needs it."""
    if not _deck_audio_auto_requested() or _input_device_env_is_explicit():
        return input_idx, input_device_name, base_audio_capture_context, deck_audio_routing
    if getattr(deck_audio_routing, "reason", None) != "capture_device_too_few_channels":
        return input_idx, input_device_name, base_audio_capture_context, deck_audio_routing
    required = int(getattr(deck_audio_routing, "required_opened_channels", 0) or 0)
    opened = int(getattr(deck_audio_routing, "opened_channels", 0) or 0)
    if required <= opened or "blackhole" not in input_device_name.lower():
        return input_idx, input_device_name, base_audio_capture_context, deck_audio_routing

    for candidate_device in ("BlackHole 16ch",):
        if candidate_device.lower() == input_device_name.lower():
            continue
        try:
            candidate_idx = audio_backend.find_device(candidate_device, "input")
            candidate_context = audio_backend.describe_capture_input(
                candidate_idx,
                requested_device=candidate_device,
                opened_channels=2,
            )
        except Exception:
            continue
        candidate_routing = deck_audio_routing_from_env(
            input_channels=candidate_context.get("input_channels"),
            default_opened_channels=2,
            capture_device_name=str(candidate_context.get("device_name") or candidate_device),
        )
        if not candidate_routing.enabled:
            continue
        candidate_context = audio_backend.describe_capture_input(
            candidate_idx,
            requested_device=candidate_device,
            opened_channels=candidate_routing.opened_channels,
        )
        print(
            "-> deck audio auto: upgraded input device "
            f"{input_device_name!r} -> {candidate_device!r} "
            f"({candidate_routing.opened_channels}ch)"
        )
        return candidate_idx, candidate_device, candidate_context, candidate_routing

    return input_idx, input_device_name, base_audio_capture_context, deck_audio_routing


def _voice_callback_factory(playback: PlaybackQueue):
    """Verbatim port of cohost_v4.py:885-888 voice output callback."""

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[output status] {status}", file=sys.stderr)
        outdata[:] = playback.pull(frames * 2)

    return callback


def _passthrough_callback_factory(passthrough: PassthroughBuffer):
    """Verbatim port of cohost_v4.py:864-873 passthrough output callback."""
    bytes_per_frame = 2 * 4  # stereo float32 = 8 bytes/frame

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[passthrough status] {status}", file=sys.stderr)
        n_bytes = frames * bytes_per_frame
        raw = passthrough.pull(n_bytes)
        if not raw or len(raw) < n_bytes:
            outdata.fill(0)
            return
        arr = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
        outdata[:] = arr

    return callback


def _mic_callback_factory(mic: MicBuffer, mic_audio_buf: AudioBuffer | None = None):
    """Verbatim port of cohost_v4.py:1965-1969 mic stream callback.

    Plan 40-01 (AUDIO-01): when ``mic_audio_buf`` is provided, the callback
    ALSO resamples 48k→16k, zero-fills while AI talks, clips to int16, and
    pushes into the second buffer — verbatim port of v4:2278-2296.

    Backward-compat: ``mic_audio_buf=None`` (default) preserves the v2.1
    byte-identical mic-only path so existing tests/test_main_smoke.py and
    the legacy run path keep working.

    Pitfall 1 (RESEARCH.md): the AI's own voice plays through the speakers
    → mic → mic_audio_buf and Gemini would hear the AI saying what it just
    said. The ``mic._current_gain() == MIC_GAIN_AT_AI_TALK`` zero-fill is
    load-bearing IP — without it the system self-triggers KAAN_SPOKE loops.
    """

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[mic status] {status}", file=sys.stderr)
        mono = indata[:, 0] if indata.ndim > 1 else indata
        mono_f = mono.astype(np.float32)
        mic.push(mono_f)

        # Plan 40-01 — second-buffer tap. Sounddevice callbacks MUST NEVER
        # crash the audio thread (v4:2293-2294); the whole branch lives
        # inside a try/except Exception: pass.
        if mic_audio_buf is not None:
            try:
                # Resample 48kHz → 16kHz (matches AudioBuffer._sr).
                mic16f = resample_audio(
                    mono_f, source_sr=INPUT_SR_NATIVE, target_sr=INPUT_SR_TARGET
                )
                # AI-talk zero-fill BEFORE the int16 clip (Pitfall 1).
                if mic._current_gain() == MIC_GAIN_AT_AI_TALK:
                    mic16f = np.zeros_like(mic16f)
                pcm16 = np.clip(mic16f * 32767.0, -32768, 32767).astype(np.int16)
                mic_audio_buf.push(pcm16)
            except Exception:
                pass

    return callback


# =============================================================================
# main — async orchestrator
# =============================================================================


async def main() -> None:
    """Verbatim port of cohost_v4.py:1925-2080 with package-aware imports.

    Phase 5 adds env-driven mode dispatch:
      VIBEMIX_LLM_MODE       = 'direct' (default) | 'proxy'
      VIBEMIX_PROXY_BASE_URL = 'https://api.altidus.world' (default)
      VIBEMIX_CLIENT_VERSION = vibemix.__version__ (default)
    """
    # ----- Phase 34 / SEC-10 — auditable privacy banner -----
    # Emitted to stderr BEFORE any network activity so a user reading the
    # sidecar log sees the privacy posture before the proxy /register
    # call. Telemetry state is read from the persisted ConfigStore.
    try:
        from vibemix.runtime.sec_check import print_security_banner

        _cfg = load_config()
        print_security_banner(
            telemetry_on=getattr(_cfg, "telemetry_consent", False),
            version=__version__,
        )
    except Exception as _e:  # pragma: no cover — banner must never crash
        print(f"[sec_check] banner skipped: {_e}", file=sys.stderr)

    # ----- Phase 5 / One Mind W5 — mode dispatch (env > persisted config) -----
    # VIBEMIX_LLM_MODE env wins (dev/CI override). Otherwise the persisted
    # ConfigStore.llm_mode drives it so a UI mode-picker choice survives
    # relaunch. Ships defaulting to "direct" (BYO key) — the packaged-default
    # flip to "proxy" is KAAN-ACTION, gated on the Bravoh /register + /health
    # + /v1 endpoints being live (a premature proxy default would exit boot
    # below for every user without those endpoints).
    _env_mode = os.environ.get("VIBEMIX_LLM_MODE")
    if _env_mode is not None:
        mode = _env_mode.strip().lower()
    else:
        try:
            mode = (load_config().llm_mode or "direct").strip().lower()
        except Exception:
            mode = "direct"
    proxy_base_url = os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world")
    client_version = os.environ.get("VIBEMIX_CLIENT_VERSION", __version__)

    if mode not in ("direct", "proxy"):
        sys.exit(f"VIBEMIX_LLM_MODE must be 'direct' or 'proxy', got {mode!r}")

    api_key: str | None = None
    or_key: str | None = None
    jwt: str | None = None
    install_uuid: str | None = None

    if mode == "direct":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # LOUD failure. A missing key is the #1 cause of the "co-host
            # never speaks" silent dead-end (the bundled binary not finding
            # its .env). Emit a [FATAL]-tagged line so the Tauri watchdog's
            # read_last_log_line surfaces the real cause in the crash banner
            # instead of a generic exit. Exit 4 = "no API key" sentinel.
            print(
                "[FATAL] GEMINI_API_KEY not set (mode=direct) — the co-host "
                "cannot authenticate to Gemini and will never speak.",
                file=sys.stderr,
                flush=True,
            )
            print(
                "[FATAL] Set GEMINI_API_KEY in the environment, in the "
                "repo-root .env (dev), or in "
                f"{app_data_dir() / '.env'} (bundled install). "
                "Or set VIBEMIX_LLM_MODE=proxy to use the Bravoh proxy.",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(4)
        or_key = os.environ.get("OPENROUTER_API_KEY")  # optional
    else:  # mode == "proxy"
        try:
            _ensure_proxy_auth_deps()
            install_uuid = get_or_create_install_uuid()
            jwt = await get_or_refresh_jwt(install_uuid, proxy_base_url, client_version)
        except RuntimeError as e:
            sys.exit(f"Proxy mode setup failed: {e}. Check VIBEMIX_PROXY_BASE_URL and network.")
        except httpx.HTTPError as e:
            sys.exit(
                f"Proxy /register network error: {e.__class__.__name__}: {e}. "
                f"Check VIBEMIX_PROXY_BASE_URL and connectivity."
            )
        print(f"-> mode: proxy (install_uuid={install_uuid[:8]}..., jwt cached)")

    # ----- Phase 6 genre profile dispatch -----
    applied_genre = apply_genre_env()
    if applied_genre is None:
        print("-> genre profile: none (Phase 3 absolute-threshold fallback)")
    else:
        print(f"-> genre profile: {applied_genre}")

    # ----- Phase 52 (GENRE-01) — env override wins over auto-detect -----
    # The user EXPLICITLY pinned a genre only when VIBEMIX_GENRE_PROFILE is
    # actually present in the environment AND resolved to a real profile. A
    # DEFAULTED 'techno' (env var absent) does NOT count as a pin — auto-detect
    # should still self-correct the active profile in that case. When env-pinned,
    # the auto-detector still SCORES (detected_genre/genre_confidence surfaced
    # for honesty) but _tick_once does NOT call set_active_profile.
    from vibemix.state.genre import set_auto_enabled

    env_pinned = "VIBEMIX_GENRE_PROFILE" in os.environ and applied_genre is not None
    set_auto_enabled(not env_pinned)
    if env_pinned:
        print(f"-> genre auto-detect: OFF (user pinned {applied_genre})")
    else:
        print("-> genre auto-detect: ON (self-correcting active profile)")

    # --- Phase 2 audio primitives ---
    import time as _time  # local import so the test suite can mock time.time without import-time side effects

    levels = Levels()
    playback = PlaybackQueue(levels)
    passthrough = PassthroughBuffer()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)
    audio_buf = AudioBuffer(seconds=140.0, sr=INPUT_SR_TARGET)
    clean_audio_buf = AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0, sr=INPUT_SR_TARGET)
    # Plan 40-01 (AUDIO-01) — mic-as-2nd-Gemini-Part ring. 12s wide (8s
    # snapshot + 4s jitter headroom), 16kHz int16. Fed by the mic callback
    # below; consumed by DJCoHostAgent.llm_node when KAAN_SPOKE-recent AND
    # the ring has signal. Zero-filled during AI talk in the callback to
    # prevent self-triggered KAAN_SPOKE loops (Pitfall 1).
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    # Plan 40-03 (AUDIO-02 + AUDIO-04) — source-file lookahead provider.
    # Per-session lifecycle: the title→path Spotlight cache + extrapolation-
    # guard state live for the whole DJ session (RESEARCH Open Question 3
    # resolution). The agent consumes via ``self._lookahead.snapshot_wav()``
    # in llm_node and conditionally appends Part 3 to the multimodal
    # contents list, labeled "NOT YET HEARD BY AUDIENCE" per locked
    # CONTEXT.md Q2.
    # 2026-05-21 (Kaan): lookahead is OFF by default. It feeds the PRISTINE
    # source file from disk (pre-EQ/filter/blend) — so the AI would hear the
    # original track, NOT the DJing Kaan is doing to it on the master. For a
    # coach grounding on HIS performance that's backwards. Master output
    # (Part 1, BlackHole) is the only audience-true signal. Re-enable with
    # VIBEMIX_LOOKAHEAD=1 if a latency-offset peek is ever wanted again.
    if os.environ.get("VIBEMIX_LOOKAHEAD", "0").strip().lower() in ("1", "true", "yes", "on"):
        lookahead_provider = LookaheadProvider()
        print(
            f"-> lookahead: +{LOOKAHEAD_SECONDS:.1f}s @ "
            f"{LOOKAHEAD_WINDOW_SECONDS:.0f}s window "
            f"(degrades silently on streaming tracks)"
        )
    else:
        lookahead_provider = None
        print("-> lookahead: OFF (grounding on live master output only)")

    # Phase 15 — boot-time crashed-session sweep. Walks recordings_root for
    # session.json files whose ended_at_iso is None AND mtime older than
    # 30s; marks them crashed=True. Best-effort: any IO error logs and
    # continues (POC parity — the sweep is a nice-to-have surface for the
    # Plan 15-04 browser UI, not a critical-path operation).
    recordings_root = _resolve_recordings_root()
    try:
        marked = sweep_crashed_sessions(recordings_root)
        if marked:
            print(f"-> recovered {len(marked)} crashed session(s): {', '.join(marked)}")
    except Exception as e:
        print(f"[sweep err] {e}", file=sys.stderr)

    # Phase 15 Plan 03 — boot-time retention sweep. Reads retention_days from
    # the persisted ConfigStore (Phase 12 W2) and prunes any session dir
    # older than that. ∞ sentinel (36500) short-circuits before scandir.
    # Best-effort: any failure logs and continues — the live session must
    # still start.
    try:
        cfg_for_sweep = load_config()
        result = run_retention_sweep(recordings_root, cfg_for_sweep.retention_days)
        if result.deleted_names:
            print(
                f"-> retention sweep (boot): pruned {len(result.deleted_names)} "
                f"session(s) ({result.bytes_pruned} bytes)"
            )
    except Exception as e:
        print(f"[retention sweep boot err] {e}", file=sys.stderr)

    recorder = VoiceRecorder(root=recordings_root)

    # SessionTracer — comprehensive per-session trace.jsonl next to events.jsonl
    # (same session dir, same lock, same time origin). Default ON; gate via
    # VIBEMIX_TRACE=0. Fully fail-soft — never null-checked at call sites.
    from vibemix.runtime import SessionTracer

    tracer = SessionTracer.attach(recorder)
    if tracer.enabled:
        print(f"-> session trace -> {recorder.session_dir.name}/trace.jsonl")

    # Fan events.jsonl ``log_event`` kinds (mostly emitted by the agent path in
    # dj_cohost) into the categorized trace.jsonl — so AI_CALL / AI_RESP / TTS /
    # citation outcomes land in the trace without threading a tracer through the
    # agent's invariant control flow. Pure mirror; fully fail-soft in recorder.
    _TRACE_KIND_CATEGORY = {
        "llm_invoke": ("AI_CALL", "llm_invoke"),
        "cache_hit": ("AI_CALL", "cache_hit"),
        "mic_part_attached": ("AI_CALL", "mic_part_attached"),
        "mic_part_skipped": ("AI_CALL", "mic_part_skipped"),
        "lookahead_part_attached": ("AI_CALL", "lookahead_part_attached"),
        "lookahead_part_skipped": ("AI_CALL", "lookahead_part_skipped"),
        "ai_text": ("AI_RESP", "ai_text"),
        "citation_count": ("AI_RESP", "citation_count"),
        "citation_bypass": ("AI_RESP", "citation_bypass"),
        "citation_strip": ("AI_RESP", "citation_strip"),
        "slop_suppressed": ("AI_RESP", "slop_suppressed"),
        "silence_short_circuit": ("AI_RESP", "silence_short_circuit"),
        "streaming_cancel": ("AI_RESP", "streaming_cancel"),
        "reaction_evidence": ("AI_RESP", "reaction_evidence"),
        "proxy_unavailable": ("ERROR", "proxy_unavailable"),
        "proxy_recovered": ("AI_CALL", "proxy_recovered"),
        "connection_error": ("ERROR", "connection_error"),
        "connection_recovered": ("AI_CALL", "connection_recovered"),
    }

    # ``event`` is already traced richer in coach_loop (EVENT/emit) — skip its
    # mirror here so we don't double-log the same EventDetector emit.
    _TRACE_KIND_SKIP = {"event"}

    def _recorder_trace_sink(kind: str, fields: dict) -> None:
        if kind in _TRACE_KIND_SKIP:
            return
        cat, ev = _TRACE_KIND_CATEGORY.get(kind, ("STATE", kind))
        tracer.trace(cat, ev, **fields)

    recorder.trace_sink = _recorder_trace_sink

    def _live_next_feedback_sink(event) -> None:
        """Record live pill feedback as local, consent-gated taste rows."""
        from vibemix.intel.feedback import append_feedback_event, feedback_event_to_row
        from vibemix.profile import load_consent as _load_profile_consent

        consent = False
        try:
            consent = bool(_load_profile_consent())
        except Exception as e:
            print(f"-> pill feedback: consent read skipped ({e})", file=sys.stderr)

        try:
            recorder.log_event(
                "taste_feedback",
                **feedback_event_to_row(event, profile_consent=consent),
            )
        except Exception as e:
            print(f"-> pill feedback: session log skipped ({e})", file=sys.stderr)

        if not consent:
            return
        try:
            append_feedback_event(
                app_data_dir() / "taste_feedback.jsonl",
                event,
                profile_consent=consent,
            )
        except Exception as e:
            print(f"-> pill feedback: taste append skipped ({e})", file=sys.stderr)

        # One Mind S3 — apply the feedback to the LIVE in-memory taste model so
        # this session's suggestions adapt immediately (not just next launch).
        # _load_live_taste_scores re-reads the JSONL we just appended to. Runs
        # outside SuggestionService._lock (the sink is invoked lock-free from
        # _emit_feedback), so update_taste_scores' lock acquire can't deadlock.
        # suggestion_service is bound later in main(); by the time the sink
        # fires (live session) it is the service or None — guard for None.
        if suggestion_service is not None:
            try:
                suggestion_service.update_taste_scores(_load_live_taste_scores())
            except Exception as e:
                print(f"-> pill taste: live update skipped ({e})", file=sys.stderr)

    def _load_live_taste_scores() -> dict[tuple[str, str], float] | None:
        """Load consent-gated taste feedback for live transition scoring."""
        from vibemix.intel.taste_model import load_taste_model
        from vibemix.profile import load_consent as _load_profile_consent

        try:
            consent = bool(_load_profile_consent())
        except Exception as e:
            print(f"-> pill taste: consent read skipped ({e})", file=sys.stderr)
            return None
        if not consent:
            return None
        try:
            model = load_taste_model(
                app_data_dir() / "taste_feedback.jsonl",
                profile_consent=consent,
            )
        except Exception as e:
            print(f"-> pill taste: disabled ({e})", file=sys.stderr)
            return None
        scores = model.taste_scores()
        if scores:
            print(f"-> pill taste: loaded {len(scores)} role-pair score(s)")
        return scores or None

    registry = BufferRegistry(
        audio=audio_buf,
        clean_audio=clean_audio_buf,
        mic=mic,
        passthrough=passthrough,
        playback=playback,
        levels=levels,
    )

    # --- Phase 3 sensing/state backends ---
    screen_macos = ScreenMacOS()
    midi_macos = MidiMacOS()
    # MIDI trace hook — every de-duplicated controller move (button/fader/knob)
    # is forwarded to the tracer. Set on the shared controller_state so the
    # single-state hot-plug rebuild path (which mutates this object in place)
    # keeps the hook. Fail-soft inside ControllerState._record_move.
    midi_macos.controller_state.on_move = lambda label, ts: tracer.midi("move", label=label)
    # Phase 91 (RENDER-01 + RENDER-02) — the Learn surface mirror. Reads
    # (read-only) the same ControllerState midi_macos owns; the 30 Hz
    # ws_broadcast tick drains its detected queue + pulls a delta-coalesced
    # position snapshot per iteration. Sole writer of ipc.learn.midi_position
    # envelopes (Invariant #1); no second WS listener (Invariant #4); no
    # second mido listener — subscribes to the existing daemon thread via
    # ControllerState.deck_snapshot() reads.
    from vibemix.learn.midi_mirror import MidiMirror

    midi_mirror = MidiMirror(controller_state=midi_macos.controller_state)
    print("-> midi_mirror wired", file=sys.stderr)
    track_macos = TrackMacOS()
    # Seed persona env BEFORE MusicState mood, context-cache construction, and
    # DJCoHostAgent instantiation. The Settings drawer persists these values in
    # ConfigStore; the prompt resolver reads the env at build time.
    from vibemix.runtime.settings import apply_persona_config_to_env

    _boot_settings_config = load_config()
    _persona_seed = apply_persona_config_to_env(_boot_settings_config)
    if _persona_seed:
        print(
            "-> persona settings: "
            + ", ".join(f"{k}={v}" for k, v in sorted(_persona_seed.items()))
        )
    state = MusicState()
    # 2026-05-21 — seed mood from VIBEMIX_MOOD at boot. MusicState.mood defaults
    # to "hype-man" (hardcoded), and the agent reads ``live_mood = state.mood``
    # at build time — a non-None default SILENTLY OVERRODE VIBEMIX_MOOD=coach,
    # so a pro+coach session got the COACH_PRO cell with the HYPE-MAN personality
    # fragment ("high-energy, all-caps, celebrate every move") = hype-flavoured
    # coaching. Seeding state.mood from the env makes VIBEMIX_MOOD actually take.
    from vibemix.agent.dj_cohost import DEFAULT_MOOD, ENV_MOOD

    _seed_mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD).strip().lower()
    if _seed_mood in ("hype-man", "teacher", "coach"):
        state.mood = _seed_mood
        print(f"-> mood: {_seed_mood} (from {ENV_MOOD})")
    state.set_start_at = _time.time()
    state.phase_started_at = _time.time()
    # Phase 17 Plan 05 — pass audio_buf to EventDetector so genre-chain
    # detectors that need raw samples (KickSwap, PhraseBoundary) can call
    # snapshot APIs on it. Default-None signature in EventDetector.__init__
    # keeps the no-arg form working for tests + coach.py callers.
    event_detector = EventDetector(audio_buf=audio_buf)

    # --- Audio I/O via AudioMacOS firewall ---
    audio_backend = AudioMacOS(registry, recorder)
    # Master-capture INPUT: BlackHole 2ch. The common real-world fail is that
    # it isn't installed — exit 3 is the sidecar's "audio-device-missing"
    # sentinel so the Tauri shell shows the BlackHole setup banner with the
    # install link rather than the generic crash UI.
    input_device_name = INPUT_DEVICE
    try:
        input_idx = audio_backend.find_device(input_device_name, "input")
    except RuntimeError as e:
        print(
            f"[FATAL] required audio input device missing: {input_device_name!r} (input)",
            file=sys.stderr,
            flush=True,
        )
        print(f"[FATAL] {e}", file=sys.stderr, flush=True)
        print(
            "[FATAL] install BlackHole 2ch via `brew install blackhole-2ch` "
            "or https://existential.audio/blackhole/",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(3)
    _base_audio_capture_context = audio_backend.describe_capture_input(
        input_idx,
        requested_device=input_device_name,
        opened_channels=2,
    )
    deck_audio_routing = deck_audio_routing_from_env(
        input_channels=_base_audio_capture_context.get("input_channels"),
        default_opened_channels=2,
        capture_device_name=str(_base_audio_capture_context.get("device_name") or input_device_name),
    )
    (
        input_idx,
        input_device_name,
        _base_audio_capture_context,
        deck_audio_routing,
    ) = _maybe_upgrade_input_device_for_deck_audio(
        audio_backend,
        input_idx=input_idx,
        input_device_name=input_device_name,
        base_audio_capture_context=_base_audio_capture_context,
        deck_audio_routing=deck_audio_routing,
    )
    deck_audio_capture = (
        DeckAudioCapture(deck_audio_routing)
        if deck_audio_routing.enabled or deck_audio_routing.opened_channels != 2
        else None
    )
    audio_capture_context = {
        **_base_audio_capture_context,
        **deck_audio_routing.context(),
    }

    # AI-voice / passthrough OUTPUT: resolve with graceful fallback so a brand-
    # new user on ANY Mac boots. Prefer the wizard-persisted output_device_id
    # (an index into query_devices), then the OUTPUT_DEVICE name, then the OS
    # default output. Hardcoding "MacBook Pro Speakers" crashed first launch on
    # a Mac mini/Studio/iMac, external/renamed output, or a localized macOS.
    # Only fail when the machine has NO audio output at all — a different fault
    # than a missing BlackHole, so we do NOT print the BlackHole hint here.
    _persisted_output_idx: int | None = None
    try:
        _raw_out = _boot_settings_config.output_device_id
        if _raw_out is not None and str(_raw_out).strip() != "":
            _persisted_output_idx = int(_raw_out)
    except Exception:
        _persisted_output_idx = None
    try:
        output_idx = audio_backend.find_output_device(_persisted_output_idx, OUTPUT_DEVICE)
    except RuntimeError as e:
        print(
            "[FATAL] no usable audio output device for the AI voice",
            file=sys.stderr,
            flush=True,
        )
        print(f"[FATAL] {e}", file=sys.stderr, flush=True)
        sys.exit(3)

    stop_event = asyncio.Event()

    def handle_sigint():
        print("\n-> stopping...", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_sigint)

    voice_stream = audio_backend.open_voice_output(
        output_idx,
        sample_rate=OUTPUT_SR,
        block_size=VOICE_BLOCKSIZE,
        callback=_voice_callback_factory(playback),
    )
    print(f"-> AI voice -> {OUTPUT_DEVICE} @ {OUTPUT_SR}Hz")

    pass_stream = audio_backend.open_passthrough_output(
        output_idx,
        sample_rate=INPUT_SR_NATIVE,
        channels=2,
        block_size=OUTPUT_BLOCKSIZE,
        callback=_passthrough_callback_factory(passthrough),
    )
    print(f"-> djay passthrough -> {OUTPUT_DEVICE} @ {INPUT_SR_NATIVE}Hz")

    # Mic stream is optional — gracefully degrade if not found (v4:1962-1979)
    try:
        mic_idx = audio_backend.find_device(MIC_DEVICE, "input")
        mic_stream = audio_backend.open_mic_capture(
            mic_idx,
            sample_rate=INPUT_SR_NATIVE,
            block_size=INPUT_CHUNK_FRAMES,
            callback=_mic_callback_factory(mic, mic_audio_buf),
        )
        print(f"-> mic on {MIC_DEVICE} @ {INPUT_SR_NATIVE}Hz")
    except Exception as e:
        print(f"-> mic disabled: {e}")
        mic_stream = None

    # --- LLM + TTS chain ---
    _ensure_live_llm_tts_deps()
    if mode == "direct":
        print("-> mode:  direct (GEMINI_API_KEY from .env)")
        print(f"-> brain: {LLM_MODEL} (thinking=minimal, temp=1.0)")
        genai_client = genai.Client(api_key=api_key)
        llm_inst = build_llm(api_key, mode="direct")
        openrouter_tts_enabled = os.environ.get("VIBEMIX_TTS_OPENROUTER", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        tts_inst = build_tts_chain(
            gemini_api_key=api_key,
            openrouter_api_key=or_key or None,
            openrouter_enabled=openrouter_tts_enabled,
            mode="direct",
        )
        if openrouter_tts_enabled and or_key:
            print(
                f"-> tts:   {TTS_MODEL} → {TTS_FALLBACK_MODEL} "
                f"→ openrouter/{OPENROUTER_TTS_MODEL} (voice={VOICE}) [standby]"
            )
        else:
            print(
                f"-> tts:   {TTS_MODEL} → {TTS_FALLBACK_MODEL} (voice={VOICE}) "
                "[native primary; set VIBEMIX_TTS_OPENROUTER=1 for OpenRouter standby]"
            )
    else:  # mode == "proxy"
        print(f"-> brain: {LLM_MODEL} via proxy at {proxy_base_url}")
        _ensure_proxy_client_dep()
        genai_client = build_proxy_genai_client(jwt, proxy_base_url)
        llm_inst = build_llm(mode="proxy", proxy_base_url=proxy_base_url, jwt=jwt)
        tts_inst = build_tts_chain(mode="proxy", proxy_base_url=proxy_base_url, jwt=jwt)
        print(f"-> tts:   {OPENROUTER_TTS_MODEL} via proxy (voice={VOICE})")

    # ---- Phase 19 latency-stack wiring (ack_bank retired) ----
    # Pre-recorded ack/filler clips ("yeah/oh/nice") were removed —
    # they injected English placeholders into Turkish sessions and the
    # whole "premade reactions" surface fights the anti-slop thesis.
    # Reactions now come only from Gemini; silence is the substitute on
    # citation-stripped responses.
    ttft_meter = TTFTMeter()
    cancel_gate = CancelGate()
    # Plan 32-02 / PROFILE-03 — load long-term DJ profile into the cache body.
    # P60: profile lives in the CACHE, never in the per-turn prompt. If the
    # file is missing or invalid, ``profile_dict`` is None and the cache section
    # is the empty string — byte-identical to the pre-Phase-32 cache body.
    # CURATE-02 (Phase 82): gate on consent so a stale profile.json that
    # outlives a consent toggle-OFF never feeds the co-host cache — mirrors
    # session_loop.py and the curator seam (_curator_seams.taste_hint). The
    # consent-gated taste layer is now consistent across BOTH surfaces.
    profile_dict = load_profile() if load_consent() else None
    profile_section = render_profile_for_cache(profile_dict)
    if profile_dict is not None:
        print(f"-> profile: loaded ({len(profile_section)} chars in cache section)")
    # 2026-05-21 — the context cache MUST carry the SAME persona cell the
    # agent resolves from VIBEMIX_SKILL_LEVEL / VIBEMIX_MODE / VIBEMIX_MOOD.
    # Previously it baked the hardcoded SYSTEM_INSTRUCTION (= HYPE_INTERMEDIATE,
    # Turkish hype). When the cache went warm, Gemini used the cached system
    # instruction and SILENTLY OVERRODE the agent's COACH_PRO/English gen_cfg —
    # so a pro+coach+English session still spoke Turkish hype. Resolve the same
    # cell here so cache ≡ agent.
    from vibemix.agent.dj_cohost import _resolve_prompt_cell

    cache_system_instruction = _resolve_prompt_cell()
    _ensure_context_cache_dep()
    cache: GeminiContextCache | None = GeminiContextCache(
        client=genai_client,
        system_instruction_body=cache_system_instruction,
        model=LLM_MODEL,
        profile_section=profile_section,
    )
    try:
        # 2026-05-21 — wrap in a hard timeout. The SDK caches.create() call has
        # no timeout of its own; on a free-tier key (explicit context caching is
        # paid-tier on some projects) it HANGS indefinitely and blocks boot
        # before "listening to". Fail fast → cache=None → graceful degradation.
        await asyncio.wait_for(cache.create(), timeout=4.0)
        print("-> cache: warm (Gemini context cache active)")
    except Exception as e:
        print(f"-> cache disabled: {e}", file=sys.stderr)
        cache = None  # graceful degradation — agent's None-cache branch handles it

    # ---- Plan 20-05 — Phase 20 anti-slop runtime wiring ----
    # Env-var gate: VIBEMIX_ANTI_SLOP defaults to "on". Set to "off" / "0" /
    # "false" to fall back to the legacy non-wired path (v4 byte-identical
    # legacy emit path inside DJCoHostAgent.llm_node). Default-on because
    # anti-slop IS the v2.0 product — Phase 20's central thesis.
    #
    # The EvidenceRegistry is constructed unconditionally so state_refresh_loop
    # always has a target for observation writes; only the linter + tracker
    # flip on/off via the env flag. Threading the registry into the agent
    # gives the linter a non-empty snapshot to validate against (without
    # this, every response strips with reason='no_citations').
    anti_slop_flag = os.environ.get("VIBEMIX_ANTI_SLOP", "on").strip().lower()
    anti_slop_enabled = anti_slop_flag not in ("off", "0", "false")
    print(f"-> anti-slop: {'on' if anti_slop_enabled else 'off (VIBEMIX_ANTI_SLOP)'}")
    # Plan 41-02 — mutation-driven cache refresh. When the cache is wired,
    # every EvidenceRegistry.write() call schedules a debounced refresh (5s
    # debounce + 30s min-interval guard inside the registry). When cache is
    # None (degraded path), on_mutation stays None → registry stays a pure
    # observation store with no callback overhead. The lambda closes over
    # ``cache`` so refresh() resolves at fire-time, not at construction
    # (lets the wiring tolerate post-construction cache invalidation —
    # ``current_name()`` going None is fine, refresh() will re-create).
    if cache is not None:
        evidence_registry = EvidenceRegistry(on_mutation=lambda: cache.refresh())
    else:
        evidence_registry = EvidenceRegistry()
    # EventDetector is constructed before the registry exists because audio and
    # platform setup happen first. Attach the shared registry before coach_loop
    # starts so [ev:<TYPE>@t] citations resolve like deck/audio evidence.
    event_detector.attach_evidence_registry(evidence_registry)
    # Citation-linter ENFORCEMENT gate — decoupled from anti-slop 2026-05-21
    # (Kaan). The v1.0 prompt contract is "cites encouraged, not required, no
    # penalty" (CITATION_GRAMMAR_BLOCK), but a wired linter strips EVERY
    # uncited reply as reason='no_citations' — gemini-3.x rarely emits the
    # [cite] grammar, so wiring it muzzles the co-host. Default OFF; opt back
    # in with VIBEMIX_CITATION_LINT=on. The banned-phrase slop filter +
    # <silence/> short-circuit are UNAFFECTED — they run regardless of the
    # linter (see dj_cohost.llm_node silence/slop gate).
    citation_lint_flag = os.environ.get("VIBEMIX_CITATION_LINT", "off").strip().lower()
    citation_lint_enabled = anti_slop_enabled and citation_lint_flag not in (
        "off",
        "0",
        "false",
        "",
    )
    citation_linter = CitationLinter() if citation_lint_enabled else None
    stripped_rate_tracker = StrippedRateTracker() if anti_slop_enabled else None
    print(f"-> citation lint: {'on' if citation_lint_enabled else 'off (VIBEMIX_CITATION_LINT)'}")

    def _citation_telemetry() -> dict:
        """Closure invoked by ``coach_loop``'s publish gate every
        ``CITATION_PUBLISH_INTERVAL_S`` (2.0s). Reads fresh from the
        StrippedRateTracker on every call so the emitted SessionCitation
        envelope reflects the latest state.

        Returns the 4 keys ``SessionCitation.make()`` expects:

        - ``slop_ratio``: the REAL cumulative stripped/total ratio sourced
          from ``stripped_rate_tracker.slop_ratio()`` (Plan 55-03 / LIVE-04).
          This is the lifetime "what fraction of model turns got stripped"
          metric — it MOVES when the linter strips, unlike the retired
          ``1 / (1 + mean)`` count-derived placeholder. 0.0 when the tracker
          is None (anti-slop disabled).
        - ``stripped_rate_15s``: tracker 15s rolling rate fresh per call.
          0.0 when tracker is None. Distinct from slop_ratio (windowed
          bypass-guard vs lifetime metric — same record() decisions).
        - ``last_unverified_response``: the REAL most-recent stripped/bypassed
          response text sourced from ``stripped_rate_tracker.last_unverified()``
          (Plan 55-03 / LIVE-04), fed by the agent's strip/bypass branches.
          None when the tracker is None or nothing unverified yet this session.
        - ``bypass_active``: non-destructive read — ``rate >
          STRIPPED_RATE_THRESHOLD``. We deliberately do NOT call
          ``tracker.should_bypass()`` here because that's the one-shot
          latch consumer; using it from telemetry would race the gate
          decision in the agent's llm_node strip path.

        T-20-05-03: the callable must not raise. When the tracker is None
        the safe defaults (slop_ratio 0.0, last_unverified None) are returned
        and nothing is dereferenced. ``coach_loop`` also wraps it in
        try/except, but staying clean keeps the publish path quiet.
        """
        slop_ratio = (
            stripped_rate_tracker.slop_ratio() if stripped_rate_tracker is not None else 0.0
        )
        rate = stripped_rate_tracker.rate() if stripped_rate_tracker is not None else 0.0
        last_unverified = (
            stripped_rate_tracker.last_unverified() if stripped_rate_tracker is not None else None
        )
        bypass_active = stripped_rate_tracker is not None and rate > STRIPPED_RATE_THRESHOLD
        return {
            "slop_ratio": float(slop_ratio),
            "stripped_rate_15s": float(rate),
            "last_unverified_response": last_unverified,
            "bypass_active": bool(bypass_active),
        }

    # ipc.session.snapshot transcript sink — spoken AI lines land here from
    # the agent's cold post-stream logging tail; ws_broadcast drains it per
    # snapshot to light up the Tauri cohost transcript panel. Bounded so a
    # paused/dead UI client can't grow it unbounded.
    transcript_buf: deque = deque(maxlen=200)

    # 2026-05-21 — OpenRouter brain path (opt-in via VIBEMIX_LLM_VIA_OPENROUTER=1).
    # Routes the live-coach LLM through OpenRouter (OpenAI-compat, inline-audio
    # verified) to escape free-tier Gemini 503s. Requires OPENROUTER_API_KEY.
    # Model id overridable via VIBEMIX_OR_LLM_MODEL; default comes from
    # model_router through OPENROUTER_LLM_MODEL.
    or_llm_client = None
    or_llm_model = os.environ.get("VIBEMIX_OR_LLM_MODEL", OPENROUTER_LLM_MODEL)
    if os.environ.get("VIBEMIX_LLM_VIA_OPENROUTER", "0").strip().lower() not in (
        "0",
        "off",
        "false",
        "",
    ):
        if not or_key:
            sys.exit("VIBEMIX_LLM_VIA_OPENROUTER=1 but OPENROUTER_API_KEY missing in .env.")
        from vibemix.agent.openrouter_llm import build_or_client

        or_llm_client = build_or_client(or_key)
        print(f"-> brain via OpenRouter: {or_llm_model} (escapes free-tier 503)")

    # ── Phase 65 Plan 04 — Memory Retrieval Seam (RECALL-01..04) ──
    # Build the MemoryRecall service lazily (best-effort) only when enabled.
    # The recall embedder is the product CLAP factory, never the legacy Gemini
    # embedding client; when DEFAULT-OFF, startup performs zero recall/model
    # setup and agent behavior stays byte-identical.
    recall_svc = None
    # One Mind S4 — env > persisted config (mirror of the W5 llm_mode resolve).
    # VIBEMIX_RECALL_ENABLED wins when set; otherwise the persisted
    # ConfigStore.recall_enabled drives it so a future UI toggle survives
    # relaunch. Default stays OFF (config default False + env unset) — flipping
    # the shipped default ON is KAAN-ACTION (recall-feel ear-pass).
    _recall_env = os.environ.get("VIBEMIX_RECALL_ENABLED")
    if _recall_env is not None:
        recall_enabled = _recall_env.strip().lower() not in ("0", "off", "false", "")
    else:
        try:
            recall_enabled = bool(load_config().recall_enabled)
        except Exception:
            recall_enabled = False
    # Phase 80 Plan 02 — GROUND-01: secondary-ear framing flag, default OFF.
    # When OFF the reaction request is byte-identical to the v8.0 baseline (the
    # Part-1 audio still feeds, no new framing). When ON the prompt names the
    # live audio a *secondary grounding signal* with the structured evidence
    # authoritative. Gates ONLY the prompt clause — never the Part-1 attach.
    ground_secondary_ear = os.environ.get(
        "VIBEMIX_GROUND_SECONDARY_EAR", "0"
    ).strip().lower() not in ("0", "off", "false", "no", "")
    print(
        "-> secondary-ear: ON"
        if ground_secondary_ear
        else "-> secondary-ear: OFF (set VIBEMIX_GROUND_SECONDARY_EAR=1 to flip)"
    )
    if recall_enabled:
        try:
            from vibemix.library.embed_factory import (
                build_embedder as _build_embedder_for_recall,
            )
            from vibemix.memory.retrieval import MemoryRecall as _MemoryRecall
            from vibemix.memory.store import open_memory_store as _open_memory_store

            _recall_embedder = _build_embedder_for_recall()
            _recall_store = _open_memory_store()
            recall_svc = _MemoryRecall(_recall_embedder, _recall_store)
            print("-> recall: armed (CLAP, track-aware, floor=0.7, off-loop)")
        except Exception as e:  # pragma: no cover — best-effort, never blocks boot
            print(f"-> recall: disabled ({e})", file=sys.stderr)
            recall_svc = None
            recall_enabled = False
    else:
        print("-> recall: disabled (set VIBEMIX_RECALL_ENABLED=1 to flip)")

    _ensure_live_session_deps()
    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=clean_audio_buf,
        screen_buf=screen_macos,
        state=state,
        recorder=recorder,
        llm_inst=llm_inst,
        tts_inst=tts_inst,
        cache=cache,
        or_client=or_llm_client,
        or_model=or_llm_model,
        ttft_meter=ttft_meter,
        evidence_registry=evidence_registry,
        citation_linter=citation_linter,
        stripped_rate_tracker=stripped_rate_tracker,
        playback=playback,
        # Plan 32-03 / PROFILE-04 — same dict already injected into the cache
        # body via render_profile_for_cache above. Stored on the agent for
        # Settings → Profile panel diagnostics; NEVER read inside llm_node
        # (P60). None default keeps v2.0 4-kwarg call shape byte-identical.
        profile=profile_dict,
        # Plan 40-01 / AUDIO-01 — mic-as-2nd-Gemini-Part ring. Fed by
        # _mic_callback_factory(mic, mic_audio_buf) on the audio thread;
        # consumed by DJCoHostAgent.llm_node when KAAN_SPOKE-recent AND
        # the ring has signal. None default preserves byte-identical
        # 1-Part path; the wired-in instance enables the 2-Part contract.
        mic_audio_buf=mic_audio_buf,
        # Plan 40-03 / AUDIO-02 + AUDIO-04 — source-file lookahead provider.
        # Per-session lifecycle: instantiated once above; the title→path
        # cache + extrapolation guard state persist for the whole session.
        # Consumed by DJCoHostAgent.llm_node via ``snapshot_wav()`` which
        # returns ``(None, meta)`` on every failure path — the agent's
        # try/except wrapper double-belts that contract (T-40-03-02).
        lookahead=lookahead_provider,
        # ipc.session.snapshot transcript sink (drained by ws_broadcast).
        transcript_sink=transcript_buf,
        # Phase 65 Plan 04 — MemoryRecall service + Kaan-ear veto flag.
        # The service is wired regardless (so tests + telemetry see the seam);
        # recall_enabled is the live-veto switch — default-OFF until Kaan
        # flips it on the real corpus (KAAN-ACTION). With either None,
        # the agent's cold path is byte-identical to v5.0.
        recall=recall_svc,
        recall_enabled=recall_enabled,
        # Phase 80 Plan 02 — GROUND-01 secondary-ear framing gate (default OFF
        # via VIBEMIX_GROUND_SECONDARY_EAR). Omitting the env var = v8.0
        # byte-identical behavior.
        secondary_ear=ground_secondary_ear,
        audio_capture_context=audio_capture_context,
        deck_audio_buffers=deck_audio_capture.buffers if deck_audio_capture is not None else None,
    )

    # ── Plan 27-05 final-mile wiring (closes v2.0 register_library orphan, P48) ──
    library_cache = Path.home() / ".cache" / "vibemix" / "library.pkl"
    # Phase 59-04 (DECK-05) — retain the cache-warm RekordboxLibrary so the deck
    # poller can reuse it READ-ONLY (no second XML import, no DB open). None when
    # the user never imported a collection.xml → poller degrades to honest unknown.
    deck_library = None
    if library_cache.exists():
        lib = RekordboxLibrary()
        if lib.try_load_cache():
            registered = evidence_registry.register_library(lib)
            deck_library = lib  # share the SAME read-only object with the poller
            print(f"-> library: {registered} tracks registered for [track:<id>] citations")
        else:
            print("-> library: cache present but failed to load — skipping registration")
    else:
        print(
            "-> library: no cache at ~/.cache/vibemix/library.pkl — citations limited to nowplaying-cli"
        )

    # ── Plan 28-07 / One Mind W3 — 30-day staleness nudge ──
    # Once-per-boot check (cheap file-stat). The nudge payload is CAPTURED here
    # and flushed onto the live ipc_router below (the router is created
    # downstream at :1492, after this point). Was print-only — the renderer's
    # staleness banner never lit because nothing reached the bus.
    _pending_staleness_nudges: list[dict] = []
    try:
        from vibemix.library import emit_nudge_if_stale as _emit_staleness

        def _staleness_capture(msg_type: str, payload: dict) -> None:
            _pending_staleness_nudges.append(payload)

        _emit_staleness(_staleness_capture, library_cache)
    except Exception as e:
        print(f"-> staleness check failed: {e}", file=sys.stderr)

    # ── Plan 28-04 — grounding pipeline (event-gated, local CLAP) ──
    # Build Grounding lazily when a library cache exists. Embeddings are local
    # CLAP ONNX/512 through build_embedder(); the Gemini client is for the live
    # co-host brain/TTS only, not for library grounding embeddings.
    grounding = None
    suggestion_service = None
    # One Mind W3 — pre-declare so the library-import handler (registered after
    # ipc_router, downstream) can lazily build + rebind these via ``nonlocal``
    # even when no cache exists yet. A first-time import MUST work cold: the
    # whole point of "import library" is to create the embedding store the very
    # first time, when ``library_cache.exists()`` is still False.
    _library_embedder = None
    _library_store = None
    if library_cache.exists():
        try:
            from vibemix.library import (
                Grounding as _Grounding,
            )
            from vibemix.library import (
                open_store as _open_store,
            )
            from vibemix.library.embed_factory import build_embedder as _build_embedder

            _library_embedder = _build_embedder()
            _library_store = _open_store()
            grounding = _Grounding(_library_embedder, _library_store)
            print("-> grounding: armed (event-gated, threshold=0.7)")
            # PILL next-suggestion: reuse the SAME store + cache-warm library so
            # the pill suggests from the embedded library (Phase 1, embedding-
            # only; needs deck_library for track-id resolution). Full ranking is
            # recomputed on TRACK_CHANGE by coach_loop; ws_broadcast performs a
            # throttled live refresh so the shortlist winner + countdown follow
            # the playhead without reranking at 30Hz.
            if deck_library is not None:
                from vibemix.runtime.suggestion import SuggestionService

                suggestion_service = SuggestionService(
                    _library_store,
                    deck_library,
                    feedback_sink=_live_next_feedback_sink,
                    session_id=recorder.session_dir.name,
                    taste_scores=_load_live_taste_scores(),
                    prepared_pool_loader=_load_latest_prepared_pool,
                )
                print("-> pill next-suggestion: armed")
        except Exception as e:
            print(f"-> grounding: disabled ({e})", file=sys.stderr)
            grounding = None

    # ── Phase 77 Plan 04 — WIRE-01: attach the armed Grounding engine ──
    # The agent is built ABOVE (its construction depends on inputs available
    # before deck_library is resolved); the Grounding engine is built HERE,
    # after deck_library + library registration. Rather than reorder the
    # build, the agent was constructed with grounding=None and we attach the
    # engine now via the post-construction setter (smaller, cleaner diff —
    # see 77-04 SUMMARY for the build-reorder-vs-setter rationale). When
    # grounding is None (no library cache / disabled), the agent's cold path
    # stays byte-identical: set_next_event dispatches nothing, llm_node
    # injects nothing. The injected ``[track:<id>]`` resolves against the
    # register_library-seeded ids above (invariant #2 — no linter change).
    agent.attach_grounding(grounding)

    # ── LiveKit 1.5.14 turn_handling: kill the false-interruption resume ──
    # Mic VAD fires on music → LiveKit marks "interrupt" → 2s later "false alarm"
    # → with the default resume_false_interruption=True the prior utterance
    # replays from LiveKit's internal text buffer using stale content (the
    # "audio from before comes back after close" bug). DJ booth: music is
    # always above VAD threshold, so we disable barge-in interruption entirely.
    session = AgentSession(
        llm=llm_inst,
        tts=tts_inst,
        turn_handling={
            "interruption": {
                "enabled": False,
                "resume_false_interruption": False,
            },
        },
    )
    session.output.audio = PlaybackQueueAudioOutput(playback, recorder, sample_rate=OUTPUT_SR)
    print(f"-> AgentSession headless (no Room); audio out → PlaybackQueue @ {OUTPUT_SR}Hz")

    await session.start(agent)
    print("-> agent started.")

    trigger_state: dict = {"in_flight": False}
    manual_trigger = asyncio.Event()

    # --- MIDI daemon thread (Phase 3) ---
    midi_stop = threading.Event()
    midi_thread = midi_macos.start_listener_thread(midi_stop)  # noqa: F841 — daemon thread

    # --- MIDI hot-plug watcher (Phase 53 BRINGUP-03) ---
    # The static listener above retries silently on disconnect; it does NOT flip
    # is_connected() false or clear stale moves. The watcher detects mid-session
    # unplug/replug (~poll_seconds latency) and drives the single-state callback,
    # which mutates midi_macos.controller_state IN PLACE — the SAME object passed
    # to ws_broadcast + state_refresh_loop below, so single-state ownership holds
    # (no rebuild, no consumer change). Runs on its own asyncio.Event stop signal;
    # cleaned up in the finally block alongside midi_stop.
    midi_watcher_stop = asyncio.Event()
    # Phase 91 (RENDER-01) — layer MidiMirror's controller_detected enqueue +
    # bind_profile/unbind hooks on the existing hot-plug watcher. The watcher's
    # default single-state callback (handle_port_change_single_state) would also
    # work, BUT it spawns a fresh listener thread that opens mido.open_input on
    # the same port as the static start_listener_thread above — every MIDI
    # message gets handled twice (CR-01 from Phase 91 review).
    #
    # The fix: do NOT call handle_port_change_single_state from here. The
    # static listener at start_listener_thread() above already:
    #   * Calls controller_state.mark_connected(port_name) on each successful
    #     open (see _midi_common.midi_listener_thread:125).
    #   * Retries silently on disconnect (2s sleep + re-enumerate) — so a
    #     replug rebinds without intervention from this callback.
    #
    # What the static listener does NOT do: call mark_disconnected on unplug
    # (it just retries forever). The single-state callback handled that —
    # mark_disconnected clears the moves/events rings so a coach reaction
    # post-unplug can't hallucinate a move from stale ring data (state.py:193
    # docstring). So we still call mark_disconnected() here on the disconnect
    # event, but we do NOT spawn a second listener thread. Net effect: one
    # listener thread, ring-clear on unplug, MidiMirror bind/unbind layered
    # on top.
    #
    # Order: on connect we bind THEN enqueue (so a subsequent snapshot() sees
    # the bound profile); on disconnect we capture the last-bound profile,
    # enqueue, mark_disconnected on the controller_state, THEN unbind on the
    # mirror (so the envelope payload's profile id / display_name are still
    # well-formed before clearing).

    def _on_midi_port_change(event: tuple) -> None:
        kind = event[0]
        if kind == "connected":
            _, port_name, profile = event
            # The static listener above will (or already did) call
            # controller_state.mark_connected(port_name) on its open. Bind
            # the mirror's profile FIRST so the next ws_broadcast 30 Hz tick
            # emits a fresh full position frame for the freshly-rendered SVG.
            midi_mirror.bind_profile(profile)
            midi_mirror.queue_controller_detected(
                connected=True, profile=profile, port_name=port_name
            )
        elif kind == "disconnected":
            _, port_name = event
            # Use the public current_profile() accessor (WR-04 fix — no
            # reach into MidiMirror's private _profile attribute) so the
            # disconnect envelope's controller_id / display_name reflect the
            # LAST bound profile.
            last_profile = midi_mirror.current_profile()
            if last_profile is not None:
                midi_mirror.queue_controller_detected(
                    connected=False,
                    profile=last_profile,
                    port_name=port_name,
                )
            # Clear the moves/events rings on the live ControllerState so a
            # post-unplug coach reaction can't hallucinate a move from stale
            # ring data (state.py:193 — this is the load-bearing piece of the
            # old single-state callback we preserve; the listener-restart
            # piece is what we drop to avoid the doubled-thread bug).
            try:
                midi_macos.controller_state.mark_disconnected()
            except Exception as e:  # pragma: no cover — defensive
                print(f"[midi disconnect err] {e}", file=sys.stderr)
            midi_mirror.unbind()

    midi_watcher_task = midi_macos.start_port_watcher(
        midi_watcher_stop, on_change=_on_midi_port_change
    )

    # 2026-05-25 — wire the GUI session-control IPC handlers onto the live
    # ws_broadcast socket. Until now the Tauri renderer's ipc.settings.* /
    # ipc.profile.* / ipc.recordings.* requests had NO responder in the live
    # path (ws_broadcast only handled the manual-trigger action; SessionLoop,
    # which owns these handlers, was never instantiated here) — so every
    # persona/output control + settings page silently timed out. We run
    # SessionLoop's tested handlers via the IpcRouterBus adapter routed through
    # ws_broadcast's existing socket (no second listener — One Socket invariant).
    from vibemix.runtime.session_loop import SessionLoop
    from vibemix.runtime.settings import GenreProfileLoader, SettingsApplier
    from vibemix.runtime.ws_bus import IpcRouterBus

    ipc_router: IpcRouterBus | None = IpcRouterBus()
    # Phase 77 Plan 04 — WIRE-05: the live SessionLoop handle. Initialized to
    # None BEFORE the try so the name is always bound in the finally-block
    # close-ingest call (the except path below leaves it unset otherwise).
    _session_ipc = None
    # Phase 77 review WR-02 — strong-ref holder for fire-and-forget tasks
    # (the boot memory-ingest below). Bound before the try so the name is
    # always available; tasks add a self-removing done-callback.
    _background_tasks: set[asyncio.Task] = set()
    try:
        _settings_config = _boot_settings_config
        _live_settings_applier = SettingsApplier(
            config_store=_settings_config,
            music_state=state,  # mood applies live + emits mascot.mood_change
            ws_bus=ipc_router,  # mood-change + acks reach every connected client
            recordings_root=recordings_root,
            genre_loader=GenreProfileLoader(),
        )
        _session_ipc = SessionLoop(
            ipc_router,
            config_store=_settings_config,
            settings_applier=_live_settings_applier,
            music_state=state,
            levels=levels,
            playback_queue=playback,
            controller_state=midi_macos.controller_state,
            screen_available=screen_macos.is_available(),
            recordings_root=recordings_root,
            active_recorder=recorder,
            evidence_registry=evidence_registry,
        )
        # Register handlers ONLY — never call run() (ws_broadcast owns the
        # server + the snapshot loop; SessionLoop here is a handler bag).
        _session_ipc.register_handlers()
        print(
            "-> session IPC handlers wired onto mascot bus "
            f"({len(ipc_router._handlers)} types: settings/profile/recordings)"
        )
        # Phase 77 Plan 04 — WIRE-05: fire the BOOT memory-ingest sweep on the
        # SAME _session_ipc instance. main() builds SessionLoop but only calls
        # register_handlers() (never run()), so the boot+close ingest sweeps
        # that SessionLoop.run() would normally fire never ran on the live
        # path → memory.db stayed empty. We call ``_fire_ingest("boot")``
        # DIRECTLY — NOT the combined boot-sweep method, which ALSO re-runs
        # retention (main() already ran the boot retention sweep at :650;
        # the combined method would DOUBLE-prune). Gated on recall_enabled
        # (VIBEMIX_RECALL_ENABLED, default OFF) → additive no-op for the
        # default user (memory stays opt-in; recall has no fuel until Kaan
        # flips §RECALL-EAR). Off-loop + best-effort inside _fire_ingest.
        #
        # Phase 77 review WR-02 — retain a STRONG reference to the boot
        # ingest task. The event loop holds only a WEAK reference to a task
        # (CPython docs), so a bare ``asyncio.create_task(...)`` whose return
        # value is discarded can be garbage-collected mid-flight and silently
        # cancelled — leaving memory.db un-seeded even with
        # VIBEMIX_RECALL_ENABLED=1. Stash it in a long-lived set with a
        # self-removing done-callback so the loop keeps a strong ref until the
        # ingest completes. (The close-path ingest in the finally already
        # ``await``s, so only this boot path was exposed.)
        if recall_enabled and _session_ipc is not None:
            _boot_ingest_task = asyncio.create_task(_session_ipc._fire_ingest("boot"))
            _background_tasks.add(_boot_ingest_task)
            _boot_ingest_task.add_done_callback(_background_tasks.discard)
    except Exception as _e:  # pragma: no cover — never block boot on this
        ipc_router = None
        _session_ipc = None
        print(f"-> session IPC handlers NOT wired: {_e!r}", file=sys.stderr)

    # One Mind W1 — wire the live UI publish bus into the agent. The agent is
    # constructed at :1230 BEFORE ipc_router exists (:1492), so its _ipc_bus
    # defaulted to None and the citation-chip + overlay-highlight surfaces
    # stayed dark on the live path (the reaction still reached the audience via
    # TTS; only the "show your receipts" chips never broadcast). Bind it now —
    # mirror of attach_grounding. ipc_router is the live bus on success, or None
    # on the rare boot-IPC-failure path above; bind_ipc_bus(None) is a no-op
    # that keeps the cold path byte-identical.
    agent.bind_ipc_bus(ipc_router)
    if ipc_router is not None:
        print("-> agent IPC bus bound (citation chips + overlay-highlight live)")

    # ── One Mind W3 — library import + staleness producers on the live bus ──
    # importer.py (Plan 09) + staleness.py (Plan 28) were built + unit-tested
    # but never registered on the live router: ipc.library.import /
    # import_cancel / staleness_action frames from the renderer had no
    # responder, and the boot staleness nudge only printed. Wire them here — the
    # library embedder/store + evidence_registry + _background_tasks all live in
    # THIS scope (not SessionLoop's), so registering directly on ipc_router is
    # the localized fix (no SessionLoop constructor churn). No schema change:
    # these message types already exist in messages.schema.json.
    if ipc_router is not None:
        try:
            import json as _json

            from vibemix.library.importer import LibraryImporter
            from vibemix.library.staleness import apply_snooze_action
            from vibemix.ui_bus.messages import (
                LibraryImportProgress,
                LibraryStalenessNudge,
            )

            _import_state: dict[str, Any] = {"importer": None, "task": None}

            async def _emit_library(envelope: dict) -> None:
                try:
                    await ipc_router.emit(envelope)
                except Exception as _e:  # pragma: no cover — best-effort UI
                    print(f"-> [library emit err] {_e!r}", file=sys.stderr)

            def _progress_envelope(p: dict) -> dict:
                return _json.loads(
                    LibraryImportProgress.make(
                        total=int(p.get("total", 0)),
                        done=int(p.get("done", 0)),
                        current_track_name=str(p.get("current_track_name", "")),
                        cache_hits=int(p.get("cache_hits", 0)),
                        cancelled=bool(p.get("cancelled", False)),
                    ).to_json()
                )

            async def _on_library_import(msg: dict) -> None:
                nonlocal _library_embedder, _library_store
                _task = _import_state.get("task")
                if _task is not None and not _task.done():
                    return  # an import is already running — drop the duplicate
                payload = msg.get("payload") or {}
                raw_path = str(payload.get("path", "")).strip()
                if not raw_path:
                    return
                xml_path = Path(raw_path).expanduser()
                # Lazily build embedder + store — import is the one path that
                # must run cold (first-time user has no cache yet). build_embedder
                # loads the local CLAP ONNX model.
                try:
                    if _library_embedder is None or _library_store is None:
                        from vibemix.library import open_store as _open_store
                        from vibemix.library.embed_factory import (
                            build_embedder as _build_embedder,
                        )

                        _library_embedder = _build_embedder()
                        _library_store = _open_store()
                except Exception as _e:
                    print(
                        f"-> library import: embedder unavailable ({_e!r})",
                        file=sys.stderr,
                    )
                    return

                loop = asyncio.get_running_loop()

                def _on_progress(p: dict) -> None:
                    # Sync callback fired on the loop thread from import_library;
                    # schedule the async bus emit. Retain a strong ref (RUF006 /
                    # WR-02): the loop only weakly references tasks, so a bare
                    # create_task can be GC'd mid-emit.
                    _pt = loop.create_task(_emit_library(_progress_envelope(p)))
                    _background_tasks.add(_pt)
                    _pt.add_done_callback(_background_tasks.discard)

                importer = LibraryImporter(
                    _library_embedder, _library_store, on_progress=_on_progress
                )
                _import_state["importer"] = importer

                async def _run_import() -> None:
                    try:
                        result = await importer.import_library(xml_path)
                        if not result.get("cancelled"):
                            # Refresh the EvidenceRegistry so [track:<id>]
                            # citations resolve mid-session, no restart needed
                            # (mirrors import_library_async).
                            try:
                                _lib = RekordboxLibrary()
                                if _lib.try_load_cache():
                                    evidence_registry.register_library(_lib)
                            except Exception as _e:
                                print(
                                    f"-> post-import registry refresh failed: {_e!r}",
                                    file=sys.stderr,
                                )
                        # Final frame doubles as the completion signal.
                        await _emit_library(
                            _progress_envelope(
                                {
                                    "total": result.get("total", 0),
                                    "done": result.get("done", 0),
                                    "current_track_name": "",
                                    "cache_hits": result.get("cache_hits", 0),
                                    "cancelled": result.get("cancelled", False),
                                }
                            )
                        )
                    except Exception as _e:
                        print(f"-> library import failed: {_e!r}", file=sys.stderr)

                _t = loop.create_task(_run_import())
                _import_state["task"] = _t
                _background_tasks.add(_t)
                _t.add_done_callback(_background_tasks.discard)

            async def _on_library_import_cancel(msg: dict) -> None:
                importer = _import_state.get("importer")
                if importer is not None:
                    importer.cancel_flag.set()

            async def _on_library_staleness_action(msg: dict) -> None:
                payload = msg.get("payload") or {}
                action = str(payload.get("action", "")).strip()
                try:
                    apply_snooze_action(action)
                except ValueError as _e:
                    print(f"-> staleness action rejected: {_e}", file=sys.stderr)

            ipc_router.register_handler("ipc.library.import", _on_library_import)
            ipc_router.register_handler("ipc.library.import_cancel", _on_library_import_cancel)
            ipc_router.register_handler(
                "ipc.library.staleness_action", _on_library_staleness_action
            )
            print("-> library import + staleness handlers wired")

            # Flush the boot staleness nudge captured above onto the live bus.
            for _p in _pending_staleness_nudges:
                await _emit_library(
                    _json.loads(
                        LibraryStalenessNudge.make(
                            age_days=int(_p.get("age_days", 0)),
                            snoozed_until_ts=_p.get("snoozed_until_ts"),
                        ).to_json()
                    )
                )
            if _pending_staleness_nudges:
                _age = _pending_staleness_nudges[0].get("age_days")
                print(f"-> staleness nudge emitted ({_age}d stale)")
        except Exception as _e:
            print(f"-> library import/staleness NOT wired: {_e!r}", file=sys.stderr)

    # Phase 92 (LESSON-01/03/04) — wire LessonRuntime alongside MidiMirror.
    # P91 already shipped MidiMirror (read-only 30 Hz controller-position
    # snapshotter); P92 ships the FSM that drives the lesson lifecycle on
    # top. The runtime emits ipc.learn.* envelopes via the same
    # ipc_router instance SessionLoop registered handlers on above (One
    # Socket invariant #4 preserved — no second ws listener).
    #
    # Boot sequence:
    #   1. load_progress() reads ~/.cache/vibemix/learn-progress.json. On
    #      corruption (was_corrupt=True) the file is silently nuked +
    #      fresh empty is returned; we surface a one-line toast envelope
    #      to the webview so the user knows their progress was reset.
    #   2. Instantiate LessonRuntime with the loaded progress as the
    #      progress_store; LearnState is the single-writer dataclass
    #      (Invariant #1 binding).
    #   3. asyncio.create_task(lesson_runtime.tick_loop(stop_event)) so
    #      the 30 s strike-escalation timer + 45 s min-dwell gate runs
    #      alongside ws_broadcast's 30 Hz tick (Pitfall 6 mitigation —
    #      tick_loop callbacks are sync emits, no file I/O).
    #
    # Defensive: when ipc_router is None (the SessionLoop wiring above
    # failed) we still wire LessonRuntime so the FSM exists; emit calls
    # become no-ops via the sync-adapter's None branch. The live app
    # boots cleanly even when SessionLoop wiring degrades.
    from vibemix.learn.progress import load_progress as _load_progress
    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
    from vibemix.ui_bus.learn_messages import LearnProgressState

    class _LessonRuntimeIpcAdapter:
        """Sync→async bridge for LessonRuntime emits.

        LessonRuntime's on_enter_<state> callbacks call
        ``self._ipc.emit(envelope_dict)`` synchronously, but
        IpcRouterBus.emit is a coroutine. This adapter schedules the
        coroutine as a fire-and-forget asyncio task when a loop is
        running; when no loop is running (e.g. boot-time toasts emitted
        synchronously before asyncio.create_task fires) the coroutine
        is silently dropped. The webview eventually re-queries progress
        via ipc.learn.progress_state and gets the same data anyway.
        """

        def __init__(self, ipc_router_inst: Any) -> None:
            self._router = ipc_router_inst

        def emit(self, msg: dict) -> None:
            if self._router is None:
                return
            try:
                _loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop — drop the emit. T-92-04-08 mitigation
                # (boot-time emit before the asyncio loop is ready).
                return
            try:
                _t = _loop.create_task(self._router.emit(msg))
                # Strong-ref the task so the loop doesn't garbage-collect
                # it mid-flight (mirrors the _background_tasks pattern
                # used by the SessionLoop boot-ingest block above).
                _background_tasks.add(_t)
                _t.add_done_callback(_background_tasks.discard)
            except Exception as _emit_exc:  # pragma: no cover — defensive
                print(
                    f"[learn boot] ipc emit failed: {_emit_exc!r}",
                    file=sys.stderr,
                )

    _learn_state = LearnState()
    _learn_progress, _learn_was_recovered = _load_progress()
    _lesson_ipc_adapter = _LessonRuntimeIpcAdapter(ipc_router)

    def _load_learn_harmonic_pair() -> Any | None:
        """Return one user-library harmonic pair for Course 2, if available."""
        try:
            from vibemix.learn.harmonic_practice import pick_harmonic_practice_pair
            from vibemix.library.rekordbox import RekordboxLibrary as _RBLibrary

            lib = deck_library
            if lib is None:
                lib = _RBLibrary()
                if not lib.try_load_cache():
                    return None
            return pick_harmonic_practice_pair(lib)
        except Exception as _learn_pair_exc:  # pragma: no cover - defensive boot path
            print(
                f"[learn boot] harmonic pair lookup failed: {_learn_pair_exc!r}",
                file=sys.stderr,
            )
            return None

    def _learn_session_event(kind: str, fields: dict[str, Any]) -> None:
        try:
            recorder.log_event(kind, **fields)
        except Exception as _learn_log_exc:  # pragma: no cover — defensive
            print(
                f"[learn boot] session event log failed: {_learn_log_exc!r}",
                file=sys.stderr,
            )

    lesson_runtime = LessonRuntime(
        learn_state=_learn_state,
        midi_mirror=midi_mirror,
        controller_state=midi_macos.controller_state,
        ipc_router=_lesson_ipc_adapter,
        progress_store=_learn_progress,
        evidence_registry=evidence_registry,
        evidence_clock=lambda: state.set_seconds,
        prepared_pool_loader=_load_latest_prepared_pool,
        harmonic_pair_loader=_load_learn_harmonic_pair,
        session_event_logger=_learn_session_event,
    )
    print("-> lesson_runtime wired", file=sys.stderr)

    class _NoopLearnExemplarPlayer:
        """Fallback player when no output device can be resolved at boot."""

        def play(self, file_path: str, /) -> None:
            return

        def stop(self) -> None:
            return

    def _learn_output_device_index() -> int | None:
        try:
            from vibemix.learn.settings import read_learn_headphone_device_index

            configured = read_learn_headphone_device_index()
            if configured is not None:
                return configured
        except Exception:
            pass
        try:
            import sounddevice as sd

            default_device = getattr(sd.default, "device", None)
            if isinstance(default_device, (list, tuple)) and len(default_device) >= 2:
                output_idx = default_device[1]
            else:
                output_idx = default_device
            if output_idx is None:
                return None
            idx = int(output_idx)
            return idx if idx >= 0 else None
        except Exception:
            return None

    def _learn_observer_emit(msg: dict) -> None:
        _lesson_ipc_adapter.emit(msg)
        if not isinstance(msg, dict) or msg.get("type") != "ipc.learn.complete_lesson":
            return
        payload = msg.get("payload", {})
        reason = payload.get("reason") if isinstance(payload, dict) else None
        lesson_runtime.complete_observer_lesson(completed=reason == "completed")

    try:
        from vibemix.learn.exemplar import ExemplarFinder
        from vibemix.learn.exemplar_lesson import ExemplarLessonController
        from vibemix.learn.recital import RecitalRuntime

        output_device = _learn_output_device_index()
        exemplar_player: Any = _NoopLearnExemplarPlayer()
        if output_device is not None:
            try:
                from vibemix.learn.audio_cue import ExemplarPlayer

                exemplar_player = ExemplarPlayer(device_index=output_device, state=state)
            except Exception as _player_exc:  # pragma: no cover — defensive boot path
                print(
                    f"-> learn exemplar audio using no-op player: {_player_exc!r}",
                    file=sys.stderr,
                )

        lesson_runtime.register_lesson_observer(
            "L1.14",
            ExemplarLessonController(
                finder=ExemplarFinder(registry=evidence_registry),
                player=exemplar_player,
                ipc_emit=_learn_observer_emit,
            ),
        )
        lesson_runtime.register_lesson_observer(
            "L1.16",
            RecitalRuntime(
                ipc_emit=_learn_observer_emit,
                progress=_learn_progress,
            ),
        )
        lesson_runtime.register_lesson_observer(
            "L2.14",
            RecitalRuntime(
                ipc_emit=_learn_observer_emit,
                progress=_learn_progress,
            ),
        )
        print(
            "-> learn lesson observers wired (L1.14/L1.16/L2.14)",
            file=sys.stderr,
        )
    except Exception as _learn_observer_exc:  # pragma: no cover — defensive boot path
        print(
            f"-> learn lesson observers NOT wired: {_learn_observer_exc!r}",
            file=sys.stderr,
        )

    # CR-01 fix (P92 REVIEW) — register the 5 inbound ipc.learn.* handlers
    # onto the bus so frontend envelopes actually reach the FSM. Before
    # this wiring, IpcRouterBus.dispatch returned False for every learn
    # type (no registered handler) and the FSM stayed parked in idle —
    # the "press play" demo could never start. The handler module lives
    # at vibemix.learn.ipc_handlers; we only register when ipc_router is
    # truthy (the SessionLoop wiring above succeeded). Without ipc_router
    # the live boot already degrades gracefully (the sync adapter no-ops
    # emit), and there is no socket to dispatch from anyway.
    if ipc_router is not None:
        try:
            from vibemix.learn.ipc_handlers import register_learn_handlers

            register_learn_handlers(
                ipc_router=ipc_router,
                lesson_runtime=lesson_runtime,
                midi_mirror=midi_mirror,
                progress=_learn_progress,
                ipc_adapter=_lesson_ipc_adapter,
            )
            print(
                "-> learn IPC handlers wired (5 types: start_course/"
                "start_lesson/ack/complete_lesson/progress_state)",
                file=sys.stderr,
            )
        except Exception as _learn_handlers_exc:  # pragma: no cover — defensive
            print(
                f"-> learn IPC handlers NOT wired: {_learn_handlers_exc!r}",
                file=sys.stderr,
            )

    # If the progress file was corrupt, surface a one-line toast via
    # progress_state. Wrapped in try/except so a boot-time emit failure
    # never crashes the app (T-92-04-08).
    if _learn_was_recovered:
        try:
            _lesson_ipc_adapter.emit(
                LearnProgressState.make(
                    action="snapshot",
                    was_recovered=True,
                    progress=_learn_progress.snapshot(),
                ).to_dict()
            )
        except Exception as _toast_exc:  # pragma: no cover — defensive
            print(
                f"[learn boot] progress recovery toast emit failed: {_toast_exc!r}",
                file=sys.stderr,
            )

    # --- Asyncio tasks (6) ---
    ws_task = asyncio.create_task(
        ws_broadcast(
            levels,
            state,
            manual_trigger,
            stop_event,
            transcript_buf=transcript_buf,
            controller_state=midi_macos.controller_state,
            suggestion_holder=suggestion_service,
            tracer=tracer,
            ipc_router=ipc_router,
            screen_available=screen_macos.is_available(),
            midi_mirror=midi_mirror,
            audio_capture_context=audio_capture_context,
        )
    )
    # Phase 92 (LESSON-01) — drive LessonRuntime's 1 Hz tick_loop
    # alongside ws_broadcast's 30 Hz tick. The two coroutines share the
    # same asyncio event loop; the tick_loop coroutine is the strike-
    # escalation timer (Pitfall 6 mitigation pinned by
    # tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py).
    lesson_tick_task = asyncio.create_task(lesson_runtime.tick_loop(stop_event))
    diag_task = asyncio.create_task(diag_loop(levels, state, stop_event, tracer=tracer))
    screen_task = asyncio.create_task(screen_macos.run_capture_loop(state, stop_event))
    track_task = asyncio.create_task(track_macos.run_poll_loop(stop_event))

    # Phase 59-04 (DECK-04/05) — the THIRD external snapshot producer. Reuses the
    # SAME read-only controller_state / track_info instances the refresh loop owns
    # and the cache-warm RekordboxLibrary (deck_library, None when no collection.xml
    # imported → honest unknown). Its run_poll_loop writes the poller's OWN holder;
    # state_refresh_loop is the only thing that copies snapshot() into MusicState
    # under state._lock (single-writer rule). deck_source threads in alongside.
    deck_poller = DeckPoller(
        library=deck_library,
        controller=midi_macos.controller_state,
        track_info=track_macos.track_info,
    )
    deck_poll_task = asyncio.create_task(deck_poller.run_poll_loop(stop_event))
    refresh_task = asyncio.create_task(
        state_refresh_loop(
            state,
            audio_buf,
            midi_macos.controller_state,
            track_macos.track_info,
            stop_event,
            evidence_registry=evidence_registry,
            deck_source=deck_poller,
            section_source=deck_library,
            learn_state=_learn_state,
            audio_capture_context=audio_capture_context,
        )
    )
    coach_task = asyncio.create_task(
        coach_loop(
            session,
            agent,
            state,
            levels,
            event_detector,
            recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            cancel_gate=cancel_gate,
            ttft_meter=ttft_meter,
            playback=playback,
            # One Mind W2 — drain citation telemetry to the LIVE bus. Was
            # ``citation_shim`` (a bounded deque dead-end that nothing read);
            # ipc_router is the real ws_broadcast router, so SessionCitation
            # envelopes now reach the Settings → Diagnostics panel. coach_loop's
            # ``citation_wired`` gate tolerates ipc_router=None (boot-IPC-failure
            # path) — no emit fires there, identical to the old shim-less case.
            ipc_bus=ipc_router,
            citation_telemetry=_citation_telemetry if anti_slop_enabled else None,
            suggestion_service=suggestion_service,
            tracer=tracer,
            audio_capture_context=audio_capture_context,
        )
    )

    # Plan 41-02 — wall-clock cache refresh_loop deleted. Cache refresh is
    # now event-driven from EvidenceRegistry.write() (debounced 5s, capped
    # to once per 30s). No background task to spawn or clean up.

    # Orphan-process self-shutdown — trips stop_event if Tauri parent
    # dies abruptly so the live runtime closes audio streams + session
    # cleanly instead of orphaning under launchd with port 8765 held.
    parent_watch_task = asyncio.create_task(watch_parent(stop_event))

    # --- Input stream — last because state must be ready ---
    input_stream = audio_backend.open_capture(
        input_idx,
        sample_rate=INPUT_SR_NATIVE,
        channels=deck_audio_routing.opened_channels,
        block_size=INPUT_CHUNK_FRAMES,
        callback=_input_callback_factory(
            levels,
            passthrough,
            mic,
            audio_buf,
            clean_audio_buf,
            recorder,
            deck_audio_capture,
            audio_capture_context,
        ),
    )
    print(
        f"-> listening to {input_device_name} @ {INPUT_SR_NATIVE}Hz "
        f"({deck_audio_routing.opened_channels}ch) -> audio_buf + clean_audio_buf"
    )

    try:
        await stop_event.wait()
    finally:
        midi_stop.set()
        # Phase 53 BRINGUP-03: signal the hot-plug watcher to exit cooperatively
        # (within one poll) BEFORE its task is cancelled below.
        midi_watcher_stop.set()
        cleanup_tasks: list[asyncio.Task] = [
            coach_task,
            refresh_task,
            screen_task,
            ws_task,
            diag_task,
            track_task,
            deck_poll_task,
            parent_watch_task,
            midi_watcher_task,
            # WR-01 fix (P92 REVIEW): lesson_tick_task was missing from
            # the cleanup list — tick_loop checks stop_event each second
            # so it exits eventually, but the main coroutine never
            # awaited it. asyncio could shut down the loop mid-
            # `await asyncio.sleep(1.0)` and emit the "Task was destroyed
            # but it is pending" warning. Include it here so the shutdown
            # is clean.
            lesson_tick_task,
        ]
        for t in cleanup_tasks:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await session.aclose()
        except Exception as e:
            print(f"[close session err] {e}", file=sys.stderr)
        # Phase 77 review WR-01 — cancel the agent's off-loop pre-dispatch
        # tasks (grounding + recall) so an event firing just before SIGINT
        # doesn't leak an orphaned executor embed / a "Task was destroyed but
        # it is pending" warning. Both are cancellable best-effort: the field
        # is None until the first track-aware event, and may be done already.
        # WIRE-01 added _grounding_task; _recall_task is the pre-existing
        # Phase-65 sibling — cancel both here so neither leaks.
        for _agent_task in (
            getattr(agent, "_grounding_task", None),
            getattr(agent, "_recall_task", None),
        ):
            if _agent_task is not None and not _agent_task.done():
                _agent_task.cancel()
                try:
                    await _agent_task
                except (asyncio.CancelledError, Exception):
                    pass
        # Phase 77 review WR-02 — drain any still-running fire-and-forget
        # background task (the boot memory-ingest) on shutdown so it doesn't
        # leak past the loop teardown. Snapshot the set first (the done-
        # callback mutates it on completion).
        for _bg_task in list(_background_tasks):
            if not _bg_task.done():
                _bg_task.cancel()
                try:
                    await _bg_task
                except (asyncio.CancelledError, Exception):
                    pass
        for stream in (voice_stream, pass_stream, input_stream):
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                print(f"[close stream err] {e}", file=sys.stderr)
        if mic_stream is not None:
            try:
                mic_stream.stop()
                mic_stream.close()
            except Exception as e:
                print(f"[close mic err] {e}", file=sys.stderr)
        try:
            tracer.close()
        except Exception as e:
            print(f"[close tracer err] {e}", file=sys.stderr)
        try:
            recorder.close()
        except Exception as e:
            print(f"[close recorder err] {e}", file=sys.stderr)
        # Phase 77 Plan 04 — WIRE-05: fire the CLOSE memory-ingest for the
        # just-finished session on the SAME _session_ipc instance. Placed
        # AFTER recorder.close() so session.json is finalized (the layout
        # ingest_session expects). We await ``_fire_ingest("close", ...)``
        # directly (this finally block is inside ``async def main()`` so the
        # await is valid) — NOT the combined session-close method, which
        # ALSO re-runs retention (the close retention sweep runs just below
        # at the run_retention_sweep call; the combined method would
        # DOUBLE-prune). Gated on recall_enabled (default OFF) → additive
        # no-op by default. _session_ipc is None on the handler-wire except
        # path, so guard it. Best-effort + off-loop inside _fire_ingest.
        if recall_enabled and _session_ipc is not None:
            try:
                await _session_ipc._fire_ingest("close", session_dir=recorder.session_dir)
            except Exception as e:  # pragma: no cover — best-effort
                print(f"[close ingest err] {e}", file=sys.stderr)
        # Phase 15 Plan 03 — session-close retention sweep trigger. Fires
        # AFTER recorder.close() so the just-finished session's session.json
        # is finalized (matches the data layout the sweep expects). Reads
        # retention_days fresh in case the user changed it mid-session.
        try:
            cfg_for_close_sweep = load_config()
            result_close = run_retention_sweep(recordings_root, cfg_for_close_sweep.retention_days)
            if result_close.deleted_names:
                print(
                    f"-> retention sweep (close): pruned "
                    f"{len(result_close.deleted_names)} session(s) "
                    f"({result_close.bytes_pruned} bytes)"
                )
        except Exception as e:
            print(f"[retention sweep close err] {e}", file=sys.stderr)
        print("-> bye")


# =============================================================================
# Entry point
# =============================================================================


def _enable_line_buffering() -> None:
    """Flip stdout/stderr to line-buffered so the Tauri rotating log captures
    diagnostic lines in real time instead of in 4-8 KB pipe-buffer batches.

    Why: CPython's default is line-buffered when isatty(), fully-buffered
    otherwise. The Tauri shell spawns the sidecar through a pipe so stderr
    falls into the fully-buffered branch — ``[FATAL] ws_bus port bind failed``
    can sit in the buffer until the process exits, which makes the watchdog's
    ``read_last_log_line`` race the FATAL marker and surface the wrong tail.

    Best-effort: if the streams have been replaced by something without
    ``reconfigure`` (frozen-app edge cases) or are already closed, we silently
    fall through. The log will lag in that case but nothing breaks.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


# ─── Phase 28 — `vibemix library` CLI subcommand group ──────────────────────


def _build_library_subparsers(parser: argparse.ArgumentParser) -> None:
    """Build the `library` subparser tree. Plan 28-03 owns `search`; later
    plans append their own subcommands by importing this helper."""
    sub = parser.add_subparsers(dest="library_command", required=True)

    # Plan 28-03 — search
    sp_search = sub.add_parser("search", help="Natural-language vibe-search against your library")
    sp_search.add_argument("query", help="vibe-search query string")
    sp_search.add_argument("--k", type=int, default=10, help="number of matches (default 10)")
    sp_search.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="emit JSON to stdout (default: on)",
    )
    sp_search.set_defaults(func=_cmd_library_search)

    # Plan 28-05 — similar (USER-ASKED only; never autosurfaces)
    sp_similar = sub.add_parser(
        "similar",
        help="Find tracks similar to a seed track (USER-ASKED only)",
        description=(
            "USER-ASKED similar-track lookup. This command is the only "
            "supported entrypoint — vibemix never autosurfaces 'you might "
            "also like' suggestions in live sessions (anti-feature guard "
            "per CONTEXT LIBRARY-14)."
        ),
    )
    sp_similar.add_argument("track_id", help="seed track id")
    sp_similar.add_argument("--k", type=int, default=10)
    sp_similar.set_defaults(func=_cmd_library_similar)

    # quick-260525-gz2 — embed-folder: ingest a raw audio folder (not XML)
    sp_embed_folder = sub.add_parser(
        "embed-folder",
        help="Embed every supported audio file under a folder (recursive)",
        description=(
            "Walk a raw audio folder, embed each track locally with CLAP ONNX, "
            "persist 512-d vectors + a library.pkl so search/similar resolve "
            "filenames. Resumable, partial-failure-tolerant, and keyless."
        ),
    )
    sp_embed_folder.add_argument("path", help="folder to ingest (recursive)")
    sp_embed_folder.add_argument(
        "--json",
        action="store_true",
        help="emit the IngestReport as JSON (suppress per-track progress)",
    )
    sp_embed_folder.add_argument(
        "--strategy",
        choices=("mean_excerpt", "cue_anchored"),
        default="mean_excerpt",
        help=(
            "embed strategy. 'mean_excerpt' (DEFAULT) = intro/mid/outro 60s "
            "excerpts, mean of embeddings. 'cue_anchored' (opt-in, Path 2) = "
            "offline auto-cue detection, embed ~80s windows anchored at the "
            "mixable structural points, mean of cue-region vectors."
        ),
    )
    sp_embed_folder.set_defaults(func=_cmd_library_embed_folder)

    # Viber Agent Phase 1 — theme → curated playlist (M3U/JSON)
    sp_curate = sub.add_parser(
        "curate",
        help="Curate a playlist from a theme with the Viber agent",
        description=(
            "Bounded Viber agent. The product backend is local Codex via MCP. "
            "It vibe-searches YOUR library for the theme and writes "
            "a neutral M3U/JSON playlist to ~/.cache/vibemix/playlists/. Every "
            "track is grounded — the agent can only use tracks search returned, "
            "never invented ones."
        ),
    )
    sp_curate.add_argument(
        "theme",
        nargs="?",
        default=None,
        help="natural-language playlist theme (optional with --interactive)",
    )
    sp_curate.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="conversational mode — the agent asks you questions, then builds",
    )
    sp_curate.add_argument(
        "--name", default=None, help="playlist name (default: derived from theme)"
    )
    sp_curate.add_argument(
        "--backend",
        choices=("codex",),
        default="codex",
        help=("reasoning backend: 'codex' (local Codex CLI via MCP; needs `codex login`)"),
    )
    sp_curate.add_argument("--json", action="store_true")
    sp_curate.set_defaults(func=_cmd_library_curate)

    # Vibe Mix engine — set-prep co-host flow (discover → sequence → export)
    sp_build_set = sub.add_parser(
        "build-set",
        help="Prep a full DJ set from a brief (discover → sequence → export)",
        description=(
            "Set-prep co-host: the Viber agent discovers a pool from YOUR "
            "library, picks an energy curve, sequences it into a mixable set, "
            "and explains the critical transitions. Every track is grounded — "
            "the agent can only use tracks discovery returned, never invented "
            "ones. Optionally exports a Rekordbox-importable XML."
        ),
    )
    sp_build_set.add_argument("brief", help="natural-language set brief")
    sp_build_set.add_argument(
        "--curve",
        default=None,
        help=(
            "energy curve preset hint (opener / peak_time / after_hours / "
            "festival). Advisory — the agent picks if omitted."
        ),
    )
    sp_build_set.add_argument("--n-slots", type=int, default=None, help="target set length (slots)")
    sp_build_set.add_argument(
        "--export",
        choices=("rekordbox",),
        default=None,
        help="auto-export the chosen set (rekordbox = Rekordbox XML)",
    )
    sp_build_set.add_argument(
        "--name", default=None, help="set name (default: derived from the brief)"
    )
    sp_build_set.add_argument(
        "--backend",
        choices=("codex",),
        default="codex",
        help=(
            "reasoning backend: 'codex' (local Codex CLI via MCP; needs "
            "`codex login` + VIBEMIX_CODEX_ALLOW_SHELL=1)."
        ),
    )
    sp_build_set.add_argument("--json", action="store_true")
    sp_build_set.set_defaults(func=_cmd_library_build_set)

    # Viber chat — the conversational co-host (one turn per invocation; the
    # caller threads prior turns via --history so the CLI stays stateless and
    # the Tauri bridge can drive a live conversation).
    sp_chat = sub.add_parser(
        "chat",
        help="Talk to Viber — conversational, tool-using DJ co-host (one turn)",
        description=(
            "One conversational turn with the Viber co-host. The model may call "
            "any grounded tool (search/discover/quote/web/knowledge/"
            "curate/build) before it replies. Stateless: pass the prior "
            "conversation via --history (JSON) to continue it. Emits a JSON "
            "ChatResult (reply / tool_trace / playlist / export_path)."
        ),
    )
    sp_chat.add_argument("message", help="the user's message this turn")
    sp_chat.add_argument(
        "--history",
        default=None,
        help='prior turns as JSON: [{"role":"you"|"viber","text":...}, ...]',
    )
    sp_chat.add_argument(
        "--live-context",
        default=None,
        help="bounded live deck context JSON from the app socket (optional)",
    )
    sp_chat.add_argument(
        "--live-context-file",
        default=None,
        help=(
            "read live deck context JSON from a file; accepts either a raw "
            "context dict or a `library live-context --out` proof artifact"
        ),
    )
    sp_chat.add_argument(
        "--backend",
        choices=("codex",),
        default="codex",
        help=(
            "reasoning backend: 'codex' (the agentic engine — your ChatGPT-plan "
            "Codex CLI via the MCP server). Codex needs `codex login` + "
            "VIBEMIX_CODEX_ALLOW_SHELL=1."
        ),
    )
    sp_chat.add_argument("--json", action="store_true")
    sp_chat.set_defaults(func=_cmd_library_chat)

    sp_live_context = sub.add_parser(
        "live-context",
        help="Sample the running app socket and show the live context Viber would receive",
        description=(
            "Connects to the existing 127.0.0.1:8765 app socket, samples flat "
            "deck frames plus ipc.session.snapshot MIDI events, and renders the "
            "bounded deck/control/claim-policy packet passed to Viber chat. "
            "No model call, no Rekordbox database read."
        ),
    )
    sp_live_context.add_argument(
        "--timeout",
        type=float,
        default=1.5,
        help="seconds to sample the running socket (default 1.5)",
    )
    sp_live_context.add_argument(
        "--frames",
        type=int,
        default=90,
        help="maximum websocket frames to inspect (default 90)",
    )
    sp_live_context.add_argument(
        "--require-proof",
        action="store_true",
        help=(
            "exit non-zero unless live deck/controller/audio/evidence proof is "
            "present; useful during physical DJ verification"
        ),
    )
    sp_live_context.add_argument(
        "--wait-ready",
        type=float,
        default=0.0,
        help=(
            "keep resampling for this many seconds until --require-proof is "
            "ready; implies --require-proof (default 0)"
        ),
    )
    sp_live_context.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="seconds between --wait-ready proof attempts (default 1.0)",
    )
    sp_live_context.add_argument(
        "--out",
        default=None,
        help="write the full bounded live-context proof packet to this JSON file",
    )
    sp_live_context.add_argument("--json", action="store_true")
    sp_live_context.set_defaults(func=_cmd_library_live_context)

    sp_verify_live_reply = sub.add_parser(
        "verify-live-reply",
        help="Verify a Viber reply against a captured live-context proof packet",
        description=(
            "Deterministically checks whether a Viber reply would violate the "
            "same live deck/audio claim guard used after Codex speaks. Use this "
            "after `library live-context --out` and `library chat --json`."
        ),
    )
    sp_verify_live_reply.add_argument(
        "--live-context-file",
        required=True,
        help="raw live-context JSON or `library live-context --out` proof artifact",
    )
    sp_verify_live_reply.add_argument(
        "--chat-result-file",
        default=None,
        help="JSON output from `library chat --json`; extracts reply and move_grades",
    )
    sp_verify_live_reply.add_argument(
        "--reply",
        default=None,
        help="reply text to verify when --chat-result-file is not provided",
    )
    sp_verify_live_reply.add_argument("--json", action="store_true")
    sp_verify_live_reply.set_defaults(func=_cmd_library_verify_live_reply)

    # Vibe Mix engine — export a saved JSON set to Rekordbox XML
    sp_export_set = sub.add_parser(
        "export-set",
        help="Export a saved JSON set to a Rekordbox-importable XML",
        description=(
            "Read a JSON set (a list of track dicts, or {tracks:[...]}) and "
            "write a Rekordbox-importable collection.xml carrying order + key "
            "+ BPM + cues. The neutral, portable handoff to your DJ software."
        ),
    )
    sp_export_set.add_argument("set_json", help="path to the JSON set file")
    sp_export_set.add_argument("--out", required=True, help="destination .xml path")
    sp_export_set.add_argument("--name", default="vibemix set", help="playlist name in the XML")
    sp_export_set.add_argument("--json", action="store_true")
    sp_export_set.set_defaults(func=_cmd_library_export_set)

    # Viber Agent — Telegram mobile surface (long-poll; chat_id allow-list auth)
    sp_telegram = sub.add_parser(
        "telegram",
        help="Run the Telegram bot so you can curate playlists from your phone",
        description=(
            "Long-poll Telegram bot: send a theme, get a grounded playlist back. "
            "Needs VIBEMIX_TELEGRAM_TOKEN (from @BotFather) + "
            "VIBEMIX_TELEGRAM_ALLOWED_CHATS (your numeric chat id(s), the auth). "
            "Runs alongside the desktop app; Ctrl-C to stop."
        ),
    )
    sp_telegram.set_defaults(func=_cmd_library_telegram)

    # Plan 28-08 — legacy Gemini embedding what-if + live token telemetry
    sp_budget = sub.add_parser(
        "budget",
        help="Show legacy Gemini embedding what-if and live token telemetry",
    )
    sp_budget.add_argument(
        "--dau", type=int, default=1000, help="daily-active users (default 1000)"
    )
    sp_budget.add_argument("--json", action="store_true")
    sp_budget.set_defaults(func=_cmd_library_budget)

    sp_stats = sub.add_parser(
        "stats",
        help="Offline indexed/backend counts for the desktop header (no network)",
    )
    sp_stats.add_argument("--json", action="store_true")
    sp_stats.set_defaults(func=_cmd_library_stats)

    sp_models = sub.add_parser(
        "models",
        help="Show local AI model cache status for CLAP and CUE-DETR",
        description=(
            "Offline model asset status for one-click setup. Reports where "
            "the CLAP embedding snapshot and CUE-DETR cue model should live, "
            "which files are missing, and which env var overrides the path."
        ),
    )
    sp_models.add_argument("--json", action="store_true")
    sp_models.add_argument(
        "--install",
        choices=("required", "clap", "cue", "all"),
        default=None,
        help=(
            "download/install supported local model assets. 'required' "
            "installs the first-run required assets; 'clap' installs the "
            "Hugging Face CLAP ONNX snapshot; 'cue' reports/verifies the "
            "manual CUE-DETR ONNX target until hosting exists; 'all' requires "
            "both local model targets to be ready."
        ),
    )
    sp_models.add_argument(
        "--force",
        action="store_true",
        help="re-download model files even when checksum verification passes",
    )
    sp_models.add_argument(
        "--progress",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    sp_models.set_defaults(func=_cmd_library_models)

    sp_doctor = sub.add_parser(
        "doctor",
        help="Live capability self-check: which grounded tools actually work",
        description=(
            "Probe each capability against the real environment (CLAP runtime + "
            "model, library cache, vector store, dj-knowledge store dim, "
            "web-search key, cue-export deps, Codex CLI) and report ok/not-ok "
            "with the exact fix. Tells a stale build apart from a real breakage."
        ),
    )
    sp_doctor.add_argument("--json", action="store_true")
    sp_doctor.set_defaults(func=_cmd_library_doctor)

    # Phase 89 Plan 01 — ingest: auto-detect a DJ library + embed it on-device.
    sp_ingest = sub.add_parser(
        "ingest",
        help="Auto-detect your DJ library (Rekordbox) and embed it on-device (CLAP)",
        description=(
            "Detect your Rekordbox collection.xml at its standard export "
            "location (or pass an explicit path), parse each track, embed it "
            "ON-DEVICE via CLAP (512-dim, keyless — no Gemini, no API cost, "
            "audio never leaves the machine), and store the vectors so "
            "search/similar resolve your own crate. Resumable + "
            "partial-failure-tolerant."
        ),
    )
    sp_ingest.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            "explicit path to a Rekordbox collection.xml (omit to auto-detect "
            "the standard export location)"
        ),
    )
    sp_ingest.add_argument(
        "--json",
        action="store_true",
        help="emit the IngestReport as JSON (suppress per-track progress)",
    )
    sp_ingest.set_defaults(func=_cmd_library_ingest)


def _library_model_gap_hint(exc, *, status_loader=None):
    """Map a CLAP-model / ONNX-dep gap to an actionable install hint, else None.

    The new-user case: an empty ``~/.cache/vibemix/`` and they run ``library
    search`` / ``similar`` / ``ingest`` / ``embed-folder`` → the embedder raises
    a bare ``FileNotFoundError`` (model files absent) or ``ImportError``
    (onnxruntime/tokenizers not installed), which the CLI dumped as a raw Python
    traceback. This returns a friendly install hint for exactly those two cases
    and ``None`` for anything else (a user-supplied missing file, a real bug) so
    the caller re-raises rather than masking it.
    """
    is_dep_gap = isinstance(exc, (ImportError, ModuleNotFoundError)) and any(
        tok in str(exc).lower() for tok in ("onnxruntime", "tokenizers", "onnx")
    )
    is_model_gap = False
    if isinstance(exc, FileNotFoundError):
        try:
            if status_loader is None:
                from vibemix.library.clap_engine import onnx_model_status as status_loader
            is_model_gap = not bool(status_loader().get("installed", False))
        except Exception:
            is_model_gap = False
    if not (is_dep_gap or is_model_gap):
        return None
    return (
        "vibemix: the local CLAP model isn't installed yet — the library "
        "search / similar / ingest / embed-folder commands need it.\n"
        "Install it with:\n"
        "  uv run python -m vibemix library models --install clap"
    )


def _run_library_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="vibemix library")
    _build_library_subparsers(parser)
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (FileNotFoundError, ImportError, ModuleNotFoundError) as e:
        # New-user model/dep gap → actionable hint instead of a raw traceback.
        # Unrelated errors re-raise (we never mask a real failure).
        hint = _library_model_gap_hint(e)
        if hint is None:
            raise
        print(hint, file=sys.stderr, flush=True)
        print(f"(detail: {e})", file=sys.stderr, flush=True)
        return 2


# =============================================================================
# Phase 81 — `vibemix bench <subcommand>` (the validation instrument)
# =============================================================================


def _build_bench_subparsers(parser: argparse.ArgumentParser) -> None:
    """Build the `bench` subparser tree (Phase 81 / BENCH-01).

    Mirrors ``_build_library_subparsers``: a single ``run`` subcommand drives a
    bounded study sweep over the funded key. The offline harness/eval are the
    honest-green proof; this is the documented PRODUCE step (a parked
    KAAN-ACTION — it never gates the autonomous suite).
    """
    sub = parser.add_subparsers(dest="bench_command", required=True)

    sp_run = sub.add_parser(
        "run",
        help="Run a bounded bench study on the funded key (the produce step)",
        description=(
            "Run one focused bench study (A = arch-axis, B = model-axis, "
            "no-audio = the decisive dsp_only cell) over the real Gemini key, "
            "recording each cell verbatim. Per-cell 429 fail-safe: any "
            "rate-limit/auth/network error parks the cell as {error:...} and "
            "the sweep continues — never fabricated, never aborted. Prints the "
            "SessionMeter cost summary on completion."
        ),
    )
    sp_run.add_argument(
        "--study",
        choices=("A", "B", "no-audio"),
        default="A",
        help="which study to run (default A = the architecture axis)",
    )
    sp_run.add_argument(
        "--out",
        default=None,
        help="results JSON path (default: bench_run.json in the cwd)",
    )
    sp_run.set_defaults(func=_cmd_bench_run)


def _cmd_bench_run(args: argparse.Namespace) -> int:
    import json as _json

    from vibemix.bench.matrix import STUDIES
    from vibemix.bench.run import run_study
    from vibemix.library.budget import get_session_meter

    client, err = _library_genai_client()
    if err is not None:
        # Fail-safe: no funded client → park as KAAN-ACTION, never block.
        print(_json.dumps(err), file=sys.stderr)
        return 1

    cells = STUDIES[args.study]
    out_path = Path(args.out) if args.out else Path("bench_run.json")
    results = run_study(cells, client=client, results_path=out_path)

    errored = sum(1 for r in results if r.error is not None)
    print(
        f"-> bench: study {args.study} — {len(results)} cells "
        f"({errored} parked on error) -> {out_path}",
        file=sys.stderr,
    )
    print(_json.dumps(get_session_meter().summary(), indent=2))
    return 0


def _run_bench_cli(argv: list[str]) -> int:
    if getattr(sys, "frozen", False):
        print(
            "vibemix bench is a source-only dev/eval command and is not bundled in "
            "the shipped sidecar.",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(prog="vibemix bench")
    _build_bench_subparsers(parser)
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


def _library_genai_client():
    """Resolve a genai client for Gemini-backed eval/media helpers.

    Library embedding/search/similar now use local CLAP ONNX and do not need
    this client. Legacy/eval Gemini helpers and Gemini-based media tools still
    use the direct-first selection:

        1. GEMINI_API_KEY set → DIRECT ``genai.Client(api_key=...)`` — the
           SAME construction the live session's mode=direct path uses.
        2. else VIBEMIX_PROXY_JWT set → proxy client.
        3. else → ``None`` (caller emits the JSON error + exits 1).

    Returns ``(client, error_dict_or_None)``. ``.env`` is already loaded at
    import time, so no extra dotenv work is needed here.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    proxy_jwt = os.environ.get("VIBEMIX_PROXY_JWT")
    proxy_url = os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world")

    if api_key:
        return genai.Client(api_key=api_key), None
    if proxy_jwt:
        from vibemix.agent.proxy_client import build_proxy_genai_client

        return build_proxy_genai_client(proxy_jwt, proxy_url), None
    return None, {
        "error": (
            "No API client: set GEMINI_API_KEY (direct, recommended for "
            "local runs) in your .env/environment, or VIBEMIX_PROXY_JWT "
            "(Bravoh proxy). Neither is set."
        ),
        "results": [],
    }


def _cmd_library_search(args: argparse.Namespace) -> int:
    import json as _json

    from vibemix.library import (
        RekordboxLibrary,
        build_embedder,
        open_store,
        vibe_search,
    )

    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        print(
            _json.dumps(
                {
                    "error": (
                        "No library cache. Drag a Rekordbox XML onto Settings → Library first."
                    ),
                    "results": [],
                }
            ),
            file=sys.stderr,
        )
        return 1

    embedder = build_embedder()
    store = open_store()
    try:
        corpus_size = store.row_count()
        results, cache_hit = vibe_search(embedder, store, lib, args.query, k=args.k)
    finally:
        store.close()
    corpus_size = int(corpus_size) if corpus_size is not None else len(results)

    _json.dump(
        {
            "query": args.query,
            "cache_hit": cache_hit,
            "centered": corpus_size >= 2,
            "corpus_size": corpus_size,
            "results": [r.to_dict() for r in results],
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def _cmd_library_similar(args: argparse.Namespace) -> int:
    """Plan 28-05 — USER-ASKED similar-track query."""
    import json as _json

    from vibemix.library import (
        RekordboxLibrary,
        build_embedder,
        open_store,
    )
    from vibemix.library.similar import similar_to

    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        print(
            _json.dumps({"error": "No library cache.", "results": []}),
            file=sys.stderr,
        )
        return 1

    embedder = build_embedder()
    store = open_store()
    try:
        corpus_size = store.row_count()
        results = similar_to(embedder, store, lib, args.track_id, k=args.k)
    finally:
        store.close()
    corpus_size = int(corpus_size) if corpus_size is not None else len(results)
    _json.dump(
        {
            "track_id": args.track_id,
            "centered": corpus_size >= 2,
            "corpus_size": corpus_size,
            "results": [r.to_dict() for r in results],
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


def _cmd_library_curate(args: argparse.Namespace) -> int:
    """Viber Agent Phase 1 — theme → curated playlist (M3U/JSON).

    Product path: ``codex`` (the user's flat-rate ChatGPT sub via ``codex exec``
    + the MCP server). It can only emit tracks that search returned —
    grounding is enforced at the tool boundary.
    """
    import json as _json

    from vibemix.library import RekordboxLibrary

    backend = getattr(args, "backend", "codex")
    if backend != "codex":
        print(
            _json.dumps(
                {
                    "error": (
                        "Unsupported Viber backend. Library/Viber uses local "
                        "Codex; run `codex login` and retry with --backend codex."
                    ),
                    "playlist": None,
                }
            ),
            file=sys.stderr,
        )
        return 2
    if getattr(args, "interactive", False):
        print(
            _json.dumps(
                {
                    "error": (
                        "`library curate --interactive` is retired for the "
                        "Codex path. Use `library chat` for a conversational "
                        "Viber turn, or pass a theme to `library curate`."
                    ),
                    "playlist": None,
                }
            ),
            file=sys.stderr,
        )
        return 2
    if not args.theme:
        print(
            _json.dumps({"error": "Give a theme, or use `library chat` to talk to Viber."}),
            file=sys.stderr,
        )
        return 1

    # The library cache is needed by Codex for result-boundary grounding
    # re-validation.
    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        print(
            _json.dumps(
                {
                    "error": (
                        "No library cache. Drag a Rekordbox XML onto "
                        "Settings → Library (or run `library embed-folder`) first."
                    ),
                    "playlist": None,
                }
            ),
            file=sys.stderr,
        )
        return 1

    return _cmd_library_curate_codex(args, lib)


def _viber_live_context_from_json_payload(payload: Any) -> dict[str, Any] | None:
    """Extract Viber live context from raw JSON or a live-context proof artifact."""
    if not isinstance(payload, dict):
        return None
    nested = payload.get("live_context")
    if isinstance(nested, dict):
        return nested
    return payload


def _load_viber_live_context_file(path_raw: str) -> dict[str, Any]:
    import json as _json

    path = Path(path_raw).expanduser()
    payload = _json.loads(path.read_text(encoding="utf-8"))
    context = _viber_live_context_from_json_payload(payload)
    if not context:
        raise ValueError("file did not contain a live-context object")
    return context


def _load_json_file(path_raw: str) -> Any:
    import json as _json

    return _json.loads(Path(path_raw).expanduser().read_text(encoding="utf-8"))


def _viber_reply_from_chat_payload(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("chat result file did not contain a JSON object")
    reply = str(payload.get("reply") or "").strip()
    raw_grades = payload.get("move_grades")
    grades = (
        [item for item in raw_grades if isinstance(item, dict)]
        if isinstance(raw_grades, list)
        else []
    )
    return reply, grades


def _cmd_library_chat(args: argparse.Namespace) -> int:
    """Viber chat — one conversational, tool-using co-host turn → JSON.

    Stateless per invocation: the caller threads prior turns via ``--history``
    so the Tauri bridge can drive a live conversation. Unlike curate/build-set
    this does NOT hard-fail on a missing library cache — chat can still answer
    technique / web questions; an empty library just means search
    honestly returns nothing.
    """
    import json as _json

    from vibemix.library import RekordboxLibrary

    lib = RekordboxLibrary()
    lib.try_load_cache()  # best-effort; chat works with an empty library too

    history = None
    if getattr(args, "history", None):
        try:
            parsed = _json.loads(args.history)
            if isinstance(parsed, list):
                history = parsed
        except (ValueError, TypeError):
            history = None  # malformed history degrades to a fresh turn

    live_context = None
    if getattr(args, "live_context", None):
        try:
            parsed_context = _json.loads(args.live_context)
            live_context = _viber_live_context_from_json_payload(parsed_context)
        except (ValueError, TypeError):
            live_context = None  # malformed live context degrades to no live hint
    if getattr(args, "live_context_file", None):
        try:
            live_context = _load_viber_live_context_file(str(args.live_context_file))
        except (OSError, ValueError, TypeError, _json.JSONDecodeError) as exc:
            print(
                _json.dumps(
                    {
                        "reply": f"Could not read live context file: {exc}",
                        "stop_reason": "live_context_file_error",
                        "tool_trace": [],
                        "playlist": None,
                        "export_path": None,
                    }
                ),
                file=sys.stderr,
            )
            return 1

    backend = getattr(args, "backend", "codex")
    if backend != "codex":
        print(
            _json.dumps(
                {
                    "reply": (
                        "Unsupported Viber backend. Library/Viber uses local "
                        "Codex; run `codex login` and retry with --backend codex."
                    ),
                    "stop_reason": "unsupported_backend",
                    "tool_trace": [],
                    "playlist": None,
                    "export_path": None,
                }
            ),
            file=sys.stderr,
        )
        return 2

    # CODEX is the agentic engine. It owns the conversational loop + MCP
    # grounded tools; the library is read-only for result-boundary grounding.
    from vibemix.library.codex_curate import chat_with_codex

    result = chat_with_codex(args.message, lib, history=history, live_context=live_context)
    _json.dump(result.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    print(
        f"-> viber chat [codex] ({len(result.tools_used)} tools, stop={result.stop_reason})",
        file=sys.stderr,
    )
    return 0


def _cmd_library_verify_live_reply(args: argparse.Namespace) -> int:
    import json as _json

    try:
        proof_payload = _load_json_file(str(args.live_context_file))
        live_context = _viber_live_context_from_json_payload(proof_payload)
        if not live_context:
            raise ValueError("live context file did not contain a live-context object")
    except (OSError, ValueError, TypeError, _json.JSONDecodeError) as exc:
        result = {
            "ok": False,
            "violations": ["live_context_file_error"],
            "error": str(exc),
        }
        _json.dump(result, sys.stdout if getattr(args, "json", False) else sys.stderr, indent=2)
        sys.stdout.write("\n") if getattr(args, "json", False) else sys.stderr.write("\n")
        return 1

    reply = str(getattr(args, "reply", "") or "").strip()
    move_grades: list[dict[str, Any]] = []
    if getattr(args, "chat_result_file", None):
        try:
            reply, move_grades = _viber_reply_from_chat_payload(
                _load_json_file(str(args.chat_result_file))
            )
        except (OSError, ValueError, TypeError, _json.JSONDecodeError) as exc:
            result = {
                "ok": False,
                "violations": ["chat_result_file_error"],
                "error": str(exc),
            }
            _json.dump(
                result,
                sys.stdout if getattr(args, "json", False) else sys.stderr,
                indent=2,
            )
            sys.stdout.write("\n") if getattr(args, "json", False) else sys.stderr.write("\n")
            return 1

    from vibemix.library.codex_curate import verify_live_reply_for_viber

    result = verify_live_reply_for_viber(reply, live_context, move_grades=move_grades)
    proof_ready: bool | None = None
    if isinstance(proof_payload, dict) and isinstance(proof_payload.get("readiness"), dict):
        proof_ready = bool(proof_payload["readiness"].get("ready"))
        if not proof_ready:
            result = {
                **result,
                "ok": False,
                "violations": [*result.get("violations", []), "proof_not_ready"],
            }
    result = {
        **result,
        "proof_ready": proof_ready,
        "live_context_file": str(Path(str(args.live_context_file)).expanduser()),
        "chat_result_file": (
            str(Path(str(args.chat_result_file)).expanduser())
            if getattr(args, "chat_result_file", None)
            else None
        ),
    }
    if getattr(args, "json", False):
        _json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif result["ok"]:
        print("live reply verification: ok")
    else:
        print("live reply verification failed:", file=sys.stderr)
        for violation in result.get("violations", []):
            print(f"- {violation}", file=sys.stderr)
        corrected = result.get("corrected_reply")
        if corrected:
            print(f"corrected reply: {corrected}", file=sys.stderr)
    return 0 if result["ok"] else 1


def _session_snapshot_recent_moves(frame: dict[str, Any], *, cap: int = 6) -> list[str]:
    payload = frame.get("payload") if isinstance(frame.get("payload"), dict) else frame
    events = payload.get("midi_events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return []
    moves: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        control = str(event.get("control") or "").strip()
        if control:
            moves.append(" ".join(control.split())[:72])
    return moves[-cap:]


_VIBER_LIVE_AUDIO_FLOOR: float = 0.012
_VIBER_LIVE_DECK_CONF_FLOOR: float = 0.3
_VIBER_LIVE_DECK_SOURCES: frozenset[str] = DECK_CONTEXT_TRUSTED_SOURCES
_VIBER_LIVE_EVIDENCE_CAP: int = 10
_VIBER_LIVE_EVIDENCE_REFS_CAP: int = 14
_VIBER_LIVE_MIDI_EVIDENCE_CAP: int = 4
_VIBER_LIVE_CONTEXT_SCHEMA_VERSION: int = 2
_VIBER_LIVE_CONTEXT_REQUIRED_CAPABILITIES: frozenset[str] = frozenset(
    {
        "audio_part_context",
        "deck_audio_separation_context",
        "deck_audio_features_context",
        "deck_audio_delta_context",
        "deck_audio_window_context",
        "deck_source_status",
        "audio_window_map",
        "audio_delta",
        "live_evidence",
    }
)


def _file_probe(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not out["exists"]:
        return out
    try:
        st = path.stat()
        out["size"] = st.st_size
        out["mtime"] = st.st_mtime
    except OSError:
        pass
    return out


def _rekordbox_event_probe(path: Path) -> dict[str, Any]:
    out = _file_probe(path)
    if not out.get("exists"):
        return out
    try:
        import xml.etree.ElementTree as ET

        root = ET.parse(path).getroot()
        count = int(str(root.attrib.get("event_item_count") or "0"))
        controller_count = int(str(root.attrib.get("event_controller_item_count") or "0"))
        out["event_item_count"] = max(0, count)
        out["event_controller_item_count"] = max(0, controller_count)
        out["has_live_deck_payload"] = bool(count or controller_count)
    except Exception:
        out["has_live_deck_payload"] = False
    return out


def _library_cache_probe() -> dict[str, Any]:
    lib = RekordboxLibrary()
    cache_path = lib.CACHE_PATH
    out = _file_probe(cache_path)
    out["loaded"] = False
    out["track_count"] = 0
    out["source_type"] = "missing"
    if not out.get("exists"):
        return out
    try:
        loaded = lib.try_load_cache()
    except Exception:
        loaded = False
    out["loaded"] = bool(loaded)
    if not loaded:
        out["source_type"] = "unreadable"
        return out
    out["track_count"] = len(lib.tracks)
    source_path = Path(lib.xml_path).expanduser() if lib.xml_path else None
    if source_path is not None:
        out["source_path"] = str(source_path)
        if source_path.is_dir():
            out["source_type"] = "folder_cache"
        elif source_path.suffix.lower() == ".xml":
            out["source_type"] = "rekordbox_xml"
        else:
            out["source_type"] = "unknown_cache_source"
    return out


def _nowplaying_probe() -> dict[str, Any]:
    """Return the current OS Now Playing source without artwork payloads."""
    import json as _json
    import shutil as _shutil
    import subprocess as _subprocess

    cli = _shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"
    out: dict[str, Any] = {"cli": cli, "available": Path(cli).exists()}
    if not out["available"]:
        return out
    try:
        lines = (
            _subprocess.check_output(
                [cli, "get", "title", "artist"],
                timeout=1.5,
                stderr=_subprocess.DEVNULL,
            )
            .decode()
            .strip()
            .splitlines()
        )
        title = lines[0].strip() if len(lines) > 0 else ""
        artist = lines[1].strip() if len(lines) > 1 else ""
        if title:
            out["title"] = title[:160]
        if artist:
            out["artist"] = artist[:120]
    except Exception as exc:
        out["title_error"] = type(exc).__name__
    try:
        raw = _json.loads(
            _subprocess.check_output(
                [cli, "get-raw"],
                timeout=1.5,
                stderr=_subprocess.DEVNULL,
            )
        )
        bundle = raw.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier")
        if bundle:
            out["client_bundle_id"] = str(bundle)[:160]
        if raw.get("kMRMediaRemoteNowPlayingInfoPlaybackRate") is not None:
            out["playback_rate"] = raw.get("kMRMediaRemoteNowPlayingInfoPlaybackRate")
        from vibemix.state.deck_poller import nowplaying_source_is_deck_candidate

        out["deck_source_candidate"] = nowplaying_source_is_deck_candidate(
            {"client_bundle_id": bundle}
        )
    except Exception as exc:
        out["raw_error"] = type(exc).__name__
    return out


def _ws_port_listener_probe() -> dict[str, Any]:
    """Return the process listening on the app websocket port, if any."""
    from vibemix.audio import WS_HOST, WS_PORT

    out: dict[str, Any] = {"host": WS_HOST, "port": WS_PORT, "listening": False}
    try:
        import psutil
    except Exception as exc:
        out["error"] = f"psutil unavailable: {type(exc).__name__}"
        return out

    try:
        conns = psutil.net_connections(kind="tcp")
    except Exception as exc:
        out["error"] = f"net_connections failed: {type(exc).__name__}"
        fallback = _ws_port_listener_lsof_probe(WS_HOST, WS_PORT)
        fallback["fallback"] = "lsof"
        fallback["psutil_error"] = out["error"]
        return fallback

    host_aliases = {WS_HOST, "127.0.0.1", "::1", "localhost"}
    for conn in conns:
        laddr = getattr(conn, "laddr", None)
        if not laddr:
            continue
        try:
            ip = str(laddr.ip)
            port = int(laddr.port)
        except AttributeError:
            try:
                ip = str(laddr[0])
                port = int(laddr[1])
            except (TypeError, ValueError, IndexError):
                continue
        if port != WS_PORT or ip not in host_aliases:
            continue
        if str(getattr(conn, "status", "")).upper() != "LISTEN":
            continue

        out["listening"] = True
        pid = getattr(conn, "pid", None)
        if pid is not None:
            out["pid"] = pid
            try:
                proc = psutil.Process(pid)
                out["name"] = proc.name()
                cmdline = [str(arg) for arg in proc.cmdline()]
                if cmdline:
                    out["cmdline"] = cmdline[:8]
                    out["looks_like_vibemix"] = any("vibemix" in arg.lower() for arg in cmdline)
            except Exception as exc:
                out["process_error"] = type(exc).__name__
        return out
    fallback = _ws_port_listener_lsof_probe(WS_HOST, WS_PORT)
    if fallback.get("listening"):
        fallback["fallback"] = "lsof"
        return fallback
    return out


def _ws_port_listener_lsof_probe(host: str, port: int) -> dict[str, Any]:
    """Best-effort macOS-friendly listener probe when psutil is denied."""
    out: dict[str, Any] = {"host": host, "port": port, "listening": False}
    try:
        import subprocess as _subprocess

        proc = _subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-F", "pc"],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
    except Exception as exc:
        out["error"] = f"lsof failed: {type(exc).__name__}"
        return out
    if proc.returncode != 0 or not proc.stdout.strip():
        return out

    pid: int | None = None
    name: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("p"):
            try:
                pid = int(line[1:])
            except ValueError:
                pid = None
        elif line.startswith("c") and line[1:]:
            name = line[1:]
        if pid is not None and name:
            break
    if pid is None and not name:
        return out

    out["listening"] = True
    if pid is not None:
        out["pid"] = pid
    if name:
        out["name"] = name

    cmd_text = ""
    if pid is not None:
        try:
            ps = _subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
            cmd_text = " ".join(ps.stdout.split())
        except Exception:
            cmd_text = ""
    if cmd_text:
        out["cmdline"] = [cmd_text[:300]]
        out["looks_like_vibemix"] = "vibemix" in cmd_text.lower()
    elif name:
        out["looks_like_vibemix"] = "vibemix" in name.lower()
    return out


def _viber_local_source_status() -> dict[str, Any]:
    """Return a compact, content-free local source diagnostic for Viber proof."""
    home = Path.home()
    routing_hint = rekordbox_deck_output_routing_hint(
        capture_device_name=str(os.environ.get("VIBEMIX_INPUT_DEVICE") or INPUT_DEVICE),
        input_channels=None,
    )
    return {
        "ws_port_listener": _ws_port_listener_probe(),
        "library_cache": _library_cache_probe(),
        "nowplaying": _nowplaying_probe(),
        "rekordbox_app": _file_probe(Path("/Applications/rekordbox 7/rekordbox.app")),
        "rekordbox_master_db": _file_probe(home / "Library/Pioneer/rekordbox/master.db"),
        "rekordbox_event_xml": [
            _rekordbox_event_probe(
                home / "Library/Application Support/Pioneer/rekordbox/rekordboxEvent.xml"
            ),
            _rekordbox_event_probe(
                home / "Library/Application Support/Pioneer/rekordbox6/rekordboxEvent.xml"
            ),
        ],
        "rekordbox_deck_routing_hint": routing_hint,
        "live_db_policy": {
            "reads_rekordbox_master_db_live": False,
            "reason": "SQLCipher live DB path stays disabled; deck context uses app state plus library cache.",
        },
    }


def _viber_live_context_hint(error: str | None, source_status: dict[str, Any]) -> str:
    listener = source_status.get("ws_port_listener")
    if isinstance(listener, dict) and listener.get("listening"):
        if not listener.get("looks_like_vibemix"):
            cmdline = listener.get("cmdline")
            if isinstance(cmdline, list) and cmdline:
                label = str(cmdline[0])[:160]
            else:
                label = str(listener.get("name") or "another process")
            pid = listener.get("pid")
            pid_hint = f" pid={pid}" if pid is not None else ""
            return (
                f"Port 8765 is occupied by {label}{pid_hint}, not the Vibemix live socket. "
                "Stop that process or free the port, then start the Vibemix live session "
                "and rerun `vibemix library live-context`."
            )
        if error:
            return (
                "A Vibemix-like process is listening on 8765, but the proof client could not "
                "read frames. Keep the live session open and rerun with --require-proof."
            )
    return "Start the vibemix live session, then rerun `vibemix library live-context`."


def _viber_route_hint_channel_map(raw: Any) -> str | None:
    """Return an env-ready A/B channel map from a Rekordbox route hint."""
    hint = raw if isinstance(raw, dict) else {}
    deck_channels = hint.get("deck_channels")
    if not isinstance(deck_channels, dict):
        return None
    pairs: list[str] = []
    for side in ("A", "B"):
        raw_channels = deck_channels.get(side)
        if not isinstance(raw_channels, (list, tuple)) or len(raw_channels) < 2:
            return None
        channels: list[int] = []
        for raw_channel in raw_channels[:2]:
            try:
                channel = int(raw_channel)
            except (TypeError, ValueError):
                return None
            if channel < 0 or channel >= 32:
                return None
            channels.append(channel)
        pairs.append(f"{side}={channels[0]},{channels[1]}")
    return ";".join(pairs)


def _viber_setup_hint_from_source_status(
    source_status: dict[str, Any],
    readiness: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return actionable deck-pair setup guidance, clearly fenced as not proof."""
    if isinstance(readiness, dict) and readiness.get("ready"):
        return None
    hint = source_status.get("rekordbox_deck_routing_hint")
    if not isinstance(hint, dict):
        return None
    channel_map = _viber_route_hint_channel_map(hint)
    if not channel_map:
        return None
    highest_channel = max(
        int(ch)
        for pair in channel_map.split(";")
        for ch in pair.split("=", 1)[1].split(",")
    )
    opened_channels = max(2, highest_channel + 1)
    current_device = str(os.environ.get("VIBEMIX_INPUT_DEVICE") or INPUT_DEVICE)
    recommended_device = current_device
    if "2ch" in current_device.lower() and opened_channels > 2:
        recommended_device = "BlackHole 16ch"
    default_auto_upgrade = (
        not _input_device_env_is_explicit()
        and current_device == INPUT_DEVICE
        and "blackhole" in current_device.lower()
        and recommended_device != current_device
    )
    output_device = str(hint.get("output_device") or "unknown")
    if default_auto_upgrade:
        recommended_env = {"VIBEMIX_DECK_AUDIO_CHANNELS": "auto"}
        next_action = (
            "Rekordbox deck route hint found "
            f"({channel_map} via {output_device}). Start the live session with "
            "VIBEMIX_DECK_AUDIO_CHANNELS=auto; Vibemix will try BlackHole 16ch "
            "for the deck-pair capture automatically. Play both decks, move a "
            "controller, then rerun `vibemix library live-context --require-proof`."
        )
    else:
        recommended_env = {
            "VIBEMIX_INPUT_DEVICE": recommended_device,
            "VIBEMIX_DECK_AUDIO_CHANNELS": "auto",
        }
        next_action = (
            "Rekordbox deck route hint found "
            f"({channel_map} via {output_device}). Start the live session with "
            f"VIBEMIX_INPUT_DEVICE='{recommended_device}' "
            "VIBEMIX_DECK_AUDIO_CHANNELS=auto, play both decks, move a controller, "
            "then rerun `vibemix library live-context --require-proof`."
        )
    return {
        "status": "rekordbox_route_hint_found",
        "deck_channels": channel_map,
        "opened_channels_min": opened_channels,
        "recommended_env": recommended_env,
        "explicit_env": {
            "VIBEMIX_INPUT_DEVICE": recommended_device,
            "VIBEMIX_DECK_AUDIO_CHANNELS": channel_map,
        },
        "auto_upgrade_input_device": recommended_device if default_auto_upgrade else None,
        "output_device": output_device,
        "next_action": next_action,
        "rule": "setup_hint_not_live_audio_proof",
    }


def _float_or_zero(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _viber_live_context_schema_version(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _viber_live_context_capabilities(raw: Any) -> set[str]:
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        token = item.strip()
        if token and all(ch.isalnum() or ch == "_" for ch in token):
            out.add(token[:48])
    return out


def _viber_live_evidence_priority(token: str) -> int:
    if token.startswith("midi:"):
        return 0
    if "deck_lanes=" in token:
        return 1
    if "deck_reference=" in token:
        return 2
    if "deck_source=" in token:
        return 3
    if "transition_block=" in token or "transition_watch=" in token:
        return 4
    if "transition_candidate=" in token:
        return 5
    if "second_deck_identity=" in token:
        return 6
    if "deck_audio_capture=" in token:
        return 7
    if "deck_audio_features=" in token:
        return 8
    if "deck_audio_delta=" in token:
        return 9
    if "deck_audio_window=" in token:
        return 10
    if "move_scope=" in token:
        return 11
    if "move_effect=" in token or "audio_delta=" in token:
        return 12
    if "deck_audio_support=" in token:
        return 13
    if "deck_route=" in token:
        return 14
    return 15


def _merge_viber_live_evidence_tokens(
    existing: Any,
    incoming: Any,
    *,
    cap: int = _VIBER_LIVE_EVIDENCE_CAP,
) -> list[str]:
    items: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    index = 0
    for raw_list in (existing, incoming):
        if not isinstance(raw_list, list):
            continue
        for raw in raw_list:
            if not isinstance(raw, str):
                continue
            token = raw.strip()
            if not token or token in seen:
                continue
            seen.add(token)
            items.append((_viber_live_evidence_priority(token), index, token))
            index += 1
    if len(items) <= cap:
        return [token for _priority, _index, token in items]
    selected = sorted(items, key=lambda item: (item[0], item[1]))[:cap]
    selected.sort(key=lambda item: item[1])
    return [token for _priority, _index, token in selected]


def _merge_viber_live_midi_evidence(existing: Any, incoming: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for raw_list in (existing, incoming):
        if not isinstance(raw_list, list):
            continue
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            if not isinstance(key, str) or not key:
                continue
            t_session = _float_or_zero(item.get("t"))
            if t_session < 0:
                continue
            rounded_t = round(t_session, 1)
            ident = (key, rounded_t)
            if ident in seen:
                continue
            seen.add(ident)
            items.append({"key": key, "t": rounded_t})
    return items[-_VIBER_LIVE_MIDI_EVIDENCE_CAP:]


def _merge_viber_live_evidence(existing: Any, incoming: Any) -> dict[str, Any]:
    old = existing if isinstance(existing, dict) else {}
    new = incoming if isinstance(incoming, dict) else {}
    merged: dict[str, Any] = {}
    mix = _merge_viber_live_evidence_tokens(old.get("mix"), new.get("mix"))
    if mix:
        merged["mix"] = mix
    midi = _merge_viber_live_midi_evidence(old.get("midi"), new.get("midi"))
    if midi:
        merged["midi"] = midi
    refs = _merge_viber_live_evidence_tokens(
        old.get("refs"),
        new.get("refs"),
        cap=_VIBER_LIVE_EVIDENCE_REFS_CAP,
    )
    if refs:
        merged["refs"] = refs
    return merged


def _viber_mixer_posture_sides(mixer: Any) -> list[str]:
    """Return controller deck sides that carried concrete mixer posture."""
    if not isinstance(mixer, dict):
        return []
    sides: list[str] = []
    posture_keys = {"vol", "eq_low", "eq_mid", "eq_hi", "filter", "play"}
    for side in ("A", "B"):
        row = mixer.get(side)
        if isinstance(row, dict) and posture_keys.intersection(row):
            sides.append(side)
    return sides


def _viber_deck_lane_route_evidence_seen(evidence_items: list[str]) -> bool:
    """Return True when a citable deck_lanes atom has non-unknown routes."""
    for item in evidence_items:
        if "deck_lanes=" not in item:
            continue
        if "_route_" in item and "_route_unknown" not in item:
            return True
    return False


def _viber_deck_reference_route_evidence_seen(evidence_items: list[str]) -> bool:
    """Return True when a citable deck_reference atom has non-unknown routes."""
    for item in evidence_items:
        if "deck_reference=" not in item:
            continue
        if "_route_" in item and "_route_unknown" not in item:
            return True
    return False


def _viber_deck_pair_capture_configured(
    raw_context: object,
    *,
    preview: str,
) -> bool:
    text = str(raw_context or "")
    if "deck_audio_separation_context[" not in text:
        text = preview
    return all(
        atom in text
        for atom in (
            "mode=deck_pair_capture_configured",
            "deckA_audio=captured",
            "deckB_audio=captured",
            "per_deck_audio=captured_not_attached",
            "isolated_decks=runtime_capture_available",
        )
    )


def _viber_deck_audio_capture_evidence_seen(evidence_items: list[str]) -> bool:
    return any("deck_audio_capture=" in item for item in evidence_items)


def _viber_deck_audio_capture_active(evidence_items: list[str]) -> bool:
    for item in evidence_items:
        if "deck_audio_capture=" not in item:
            continue
        if "A_active" in item or "B_active" in item:
            return True
    return False


def _viber_deck_audio_capture_both_active(evidence_items: list[str]) -> bool:
    for item in evidence_items:
        if "deck_audio_capture=" not in item:
            continue
        if "A_active" in item and "B_active" in item:
            return True
    return False


def _viber_audio_part_deck_labels(raw: object) -> dict[str, str]:
    text = str(raw or "")
    if "per_deck_audio=deck_pair_parts" not in text:
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        match = re.search(rf"\bdeck{side}_part=(P[2-9][0-9]?)\b", text)
        if not match:
            return {}
        labels[side] = match.group(1)
    return labels if labels.get("A") != labels.get("B") else {}


def _viber_audio_window_deck_labels(raw: object) -> dict[str, str]:
    text = str(raw or "")
    if "per_deck_audio=deck_pair_parts" not in text:
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        match = re.search(rf"\bdeck{side}_audio=(P[2-9][0-9]?)\b", text)
        if not match:
            return {}
        labels[side] = match.group(1)
    return labels if labels.get("A") != labels.get("B") else {}


def _viber_audio_window_map_deck_labels(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict) or raw.get("per_deck_audio") != "deck_pair_parts":
        return {}
    labels = {
        "A": str(raw.get("deckA_audio") or ""),
        "B": str(raw.get("deckB_audio") or ""),
    }
    valid = all(re.fullmatch(r"P[2-9][0-9]?", label) for label in labels.values())
    return labels if valid and labels["A"] != labels["B"] else {}


def _viber_audio_part_window_labels_consistent(context: dict[str, Any]) -> bool:
    part_labels = _viber_audio_part_deck_labels(context.get("audio_part_context"))
    window_labels = _viber_audio_window_deck_labels(context.get("audio_window_context"))
    map_labels = _viber_audio_window_map_deck_labels(context.get("audio_window_map"))
    observed = [labels for labels in (window_labels, map_labels) if labels]
    if not part_labels:
        return not observed
    return all(labels == part_labels for labels in observed)


def _viber_deck_source_status_blockers(source_status: dict[str, str]) -> list[str]:
    """Translate source-status diagnostics into content-light proof blockers."""
    if not source_status:
        return []
    status = {key: str(value).lower() for key, value in source_status.items()}
    blockers: list[str] = []
    controller_connection = status.get("controller_connection")
    if controller_connection in {"disconnected", "unavailable"}:
        blockers.append("deck identity source: controller snapshot is not connected")
    elif status.get("controller") == "missing":
        blockers.append("deck identity source: controller snapshot is missing")

    library = status.get("library")
    if library == "missing":
        blockers.append("deck identity source: library cache is missing")
    elif library == "empty":
        blockers.append("deck identity source: library cache is empty")
    elif library == "error":
        blockers.append("deck identity source: library cache could not be read")

    if status.get("nowplaying") == "blocked_non_deck_owner":
        blockers.append("deck identity source: Now Playing is owned by a non-DJ app")
    elif status.get("nowplaying_title") == "none":
        blockers.append("deck identity source: no deck Now Playing title was observed")

    library_match = status.get("library_match")
    if library_match in {"ambiguous_label", "not_found", "track_row_missing"}:
        blockers.append("deck identity source: Now Playing did not match a unique library row")
    elif library_match in {"library_missing", "library_empty", "library_error"}:
        blockers.append("deck identity source: Now Playing could not be checked against the library")

    if status.get("resolution") == "no_single_attributable_deck":
        blockers.append("deck identity source: controller posture did not identify one deck")
    if status.get("second_deck_source") == "suppressed_requires_independent_source":
        blockers.append("second deck identity source requires independent deck evidence")
    if status.get("screen_vision") in {"disabled", "enabled_no_reader"}:
        blockers.append("screen vision is not currently resolving the independent second deck")

    out: list[str] = []
    seen: set[str] = set()
    for blocker in blockers:
        if blocker not in seen:
            out.append(blocker)
            seen.add(blocker)
    return out


def _viber_live_context_readiness(
    context: dict[str, Any],
    *,
    frames_seen: int,
    flat_deck_frame_seen: bool,
    session_snapshot_seen: bool,
) -> dict[str, Any]:
    """Return an honest physical-proof verdict for the sampled live context."""
    from vibemix.library.codex_curate import (
        normalize_live_audio_window_map_for_viber,
        normalize_live_context_for_viber,
        normalize_live_source_status_for_viber,
        render_live_context_preview,
    )
    from vibemix.state.deck_context import (
        normalize_audio_part_context_text,
        normalize_audio_window_context_text,
        normalize_deck_audio_delta_context_text,
        normalize_deck_audio_features_context_text,
        normalize_deck_audio_separation_context_text,
        normalize_deck_audio_window_context_text,
        normalize_deck_source_context_text,
    )

    raw_context = context
    raw_audio_part_window_consistent = _viber_audio_part_window_labels_consistent(raw_context)
    normalized_context = normalize_live_context_for_viber(context)
    if normalized_context:
        context = normalized_context
    normalized_audio_part_window_consistent = _viber_audio_part_window_labels_consistent(context)

    schema_version = _viber_live_context_schema_version(context.get("live_context_schema_version"))
    capabilities = _viber_live_context_capabilities(context.get("live_context_capabilities"))
    missing_capabilities = sorted(_VIBER_LIVE_CONTEXT_REQUIRED_CAPABILITIES - capabilities)
    deck_state = context.get("deck_state") if isinstance(context.get("deck_state"), dict) else {}
    resolved_decks: list[str] = []
    citable_decks: list[str] = []
    sourced_decks: list[str] = []
    if isinstance(deck_state, dict):
        for side, row in deck_state.items():
            if not isinstance(row, dict):
                continue
            confidence = _float_or_zero(row.get("confidence"))
            has_identity = bool(row.get("title") or row.get("track_id") or row.get("camelot"))
            if confidence >= _VIBER_LIVE_DECK_CONF_FLOOR and has_identity:
                resolved_decks.append(str(side))
            if confidence >= _VIBER_LIVE_DECK_CONF_FLOOR and row.get("track_id"):
                citable_decks.append(str(side))
                if row.get("source") in _VIBER_LIVE_DECK_SOURCES:
                    sourced_decks.append(str(side))

    mixer = context.get("deck_mixer") if isinstance(context.get("deck_mixer"), dict) else {}
    recent_moves = (
        context.get("recent_moves") if isinstance(context.get("recent_moves"), list) else []
    )
    audio_delta = context.get("audio_delta") if isinstance(context.get("audio_delta"), list) else []
    live_evidence = (
        context.get("live_evidence") if isinstance(context.get("live_evidence"), dict) else {}
    )
    evidence_items: list[str] = []
    if isinstance(live_evidence, dict):
        for key in ("mix", "refs"):
            values = live_evidence.get(key)
            if isinstance(values, list):
                evidence_items.extend(str(item) for item in values if item)
    has_transition_gate = any(
        token in item
        for item in evidence_items
        for token in ("transition_block=", "transition_watch=", "transition_candidate=")
    )
    has_deck_lane_evidence = any("deck_lanes=" in item for item in evidence_items)
    has_deck_lane_route_evidence = _viber_deck_lane_route_evidence_seen(evidence_items)
    has_deck_reference_evidence = any("deck_reference=" in item for item in evidence_items)
    has_deck_reference_route_evidence = _viber_deck_reference_route_evidence_seen(evidence_items)
    has_deck_source_evidence = any("deck_source=" in item for item in evidence_items)
    max_music = _float_or_zero(context.get("music"))
    preview = render_live_context_preview(context)
    has_deck_lane_context = "deck_lanes_context[" in preview
    has_deck_reference_context = "deck_reference_context[" in preview
    has_deck_source_context = "deck_source_context[" in preview or bool(
        normalize_deck_source_context_text(context.get("deck_source_context"))
    )
    deck_source_status = normalize_live_source_status_for_viber(
        context.get("deck_source_status")
    ) or {}
    has_deck_source_status = bool(deck_source_status)
    deck_source_status_blockers = _viber_deck_source_status_blockers(deck_source_status)
    has_raw_audio_part_context = bool(
        normalize_audio_part_context_text(context.get("audio_part_context"))
    )
    has_deck_audio_separation_context = bool(
        normalize_deck_audio_separation_context_text(context.get("deck_audio_separation_context"))
        or "deck_audio_separation_context[" in preview
    )
    has_deck_audio_features_context = bool(
        normalize_deck_audio_features_context_text(context.get("deck_audio_features_context"))
        or "deck_audio_features_context[" in preview
    )
    has_deck_audio_delta_context = bool(
        normalize_deck_audio_delta_context_text(context.get("deck_audio_delta_context"))
        or "deck_audio_delta_context[" in preview
    )
    has_deck_audio_window_context = bool(
        normalize_deck_audio_window_context_text(context.get("deck_audio_window_context"))
        or "deck_audio_window_context[" in preview
    )
    has_deck_pair_capture_configured = _viber_deck_pair_capture_configured(
        context.get("deck_audio_separation_context"),
        preview=preview,
    )
    has_deck_pair_setup_block = (
        "setup_block=capture_device_too_few_channels" in preview
        or "setup_block=opened_channels_too_few" in preview
    )
    has_deck_audio_capture_evidence = _viber_deck_audio_capture_evidence_seen(evidence_items)
    has_deck_audio_capture_active = _viber_deck_audio_capture_active(evidence_items)
    has_deck_audio_capture_both_active = _viber_deck_audio_capture_both_active(evidence_items)
    has_deck_audio_features_evidence = any(
        "deck_audio_features=" in item for item in evidence_items
    )
    has_deck_audio_delta_evidence = any("deck_audio_delta=" in item for item in evidence_items)
    has_deck_audio_window_evidence = any(
        "deck_audio_window=" in item for item in evidence_items
    )
    prompt_audio_part_context_seen = "audio_part_context[" in preview
    has_raw_audio_window_context = bool(
        normalize_audio_window_context_text(context.get("audio_window_context"))
    )
    has_audio_window_map = bool(
        normalize_live_audio_window_map_for_viber(context.get("audio_window_map"))
    )
    prompt_audio_window_context_seen = "audio_window_context[" in preview
    has_controller_signal = bool(mixer.get("connected")) if isinstance(mixer, dict) else False
    has_live_audio_window_signal = (
        bool(recent_moves)
        or has_controller_signal
        or bool(deck_state)
        or bool(context.get("audible"))
        or max_music >= _VIBER_LIVE_AUDIO_FLOOR
    )
    has_audio_window_context = has_raw_audio_window_context or (
        prompt_audio_window_context_seen and has_live_audio_window_signal
    )
    has_audio_part_context = has_raw_audio_part_context or (
        prompt_audio_part_context_seen and has_live_audio_window_signal
    )
    mixer_posture_sides = _viber_mixer_posture_sides(mixer)
    checks = {
        "frames_seen": frames_seen > 0,
        "flat_deck_frame_seen": bool(flat_deck_frame_seen),
        "live_context_schema_seen": schema_version >= _VIBER_LIVE_CONTEXT_SCHEMA_VERSION,
        "live_context_capabilities_seen": not missing_capabilities,
        "deck_state_resolved": bool(resolved_decks),
        "deck_state_citable_track": bool(citable_decks),
        "deck_state_source_provenance": bool(sourced_decks),
        "deck_state_pair_resolved": set(resolved_decks) >= {"A", "B"},
        "deck_state_pair_citable_tracks": set(citable_decks) >= {"A", "B"},
        "deck_state_pair_source_provenance": set(sourced_decks) >= {"A", "B"},
        "deck_lane_context_seen": has_deck_lane_context,
        "deck_reference_context_seen": has_deck_reference_context,
        "deck_source_context_seen": has_deck_source_context,
        "deck_source_status_seen": has_deck_source_status,
        "controller_connected": bool(mixer.get("connected")) if isinstance(mixer, dict) else False,
        "controller_deck_posture_seen": set(mixer_posture_sides) >= {"A", "B"},
        "recent_moves_seen": bool(recent_moves),
        "audio_part_context_seen": has_audio_part_context,
        "deck_audio_separation_context_seen": has_deck_audio_separation_context,
        "deck_audio_features_context_seen": has_deck_audio_features_context,
        "deck_audio_delta_context_seen": has_deck_audio_delta_context,
        "deck_audio_window_context_seen": has_deck_audio_window_context,
        "deck_pair_capture_configured": has_deck_pair_capture_configured,
        "deck_audio_capture_evidence_seen": has_deck_audio_capture_evidence,
        "deck_audio_capture_active": has_deck_audio_capture_active,
        "deck_audio_capture_both_active": has_deck_audio_capture_both_active,
        "deck_audio_features_evidence_seen": has_deck_audio_features_evidence,
        "deck_audio_delta_evidence_seen": has_deck_audio_delta_evidence,
        "deck_audio_window_evidence_seen": has_deck_audio_window_evidence,
        "audio_window_context_seen": has_audio_window_context,
        "audio_window_map_seen": has_audio_window_map,
        "audio_part_window_labels_consistent": (
            raw_audio_part_window_consistent and normalized_audio_part_window_consistent
        ),
        "audio_observed": bool(context.get("audible")) or max_music >= _VIBER_LIVE_AUDIO_FLOOR,
        "audio_delta_seen": bool(audio_delta),
        "live_evidence_seen": bool(evidence_items),
        "transition_gate_seen": has_transition_gate,
        "deck_lane_evidence_seen": has_deck_lane_evidence,
        "deck_lane_route_evidence_seen": has_deck_lane_route_evidence,
        "deck_reference_evidence_seen": has_deck_reference_evidence,
        "deck_reference_route_evidence_seen": has_deck_reference_route_evidence,
        "deck_source_evidence_seen": has_deck_source_evidence,
    }
    blockers: list[str] = []
    if not checks["frames_seen"]:
        blockers.append("no websocket frames arrived")
    if not checks["flat_deck_frame_seen"]:
        blockers.append("no flat deck frame was observed")
    if not checks["live_context_schema_seen"]:
        blockers.append("live socket did not advertise structured live-context schema v2")
    if not checks["live_context_capabilities_seen"]:
        blockers.append(
            "live socket capabilities missing " + ",".join(missing_capabilities)
            if missing_capabilities
            else "live socket capabilities were not observed"
        )
    if not checks["deck_state_resolved"]:
        blockers.append("deck_state had no resolved deck row")
        blockers.extend(deck_source_status_blockers)
    if not checks["deck_state_citable_track"]:
        blockers.append("deck_state had no citable track_id at confidence floor")
    if checks["deck_state_citable_track"] and not checks["deck_state_source_provenance"]:
        blockers.append("deck_state had no trusted source provenance for a citable track")
    if not checks["deck_state_pair_resolved"]:
        blockers.append("deck_state did not resolve both deck A and deck B")
        if checks["deck_state_resolved"]:
            blockers.extend(deck_source_status_blockers)
    if not checks["deck_state_pair_citable_tracks"]:
        blockers.append("deck_state did not have citable track_id for both deck A and deck B")
    if checks["deck_state_pair_citable_tracks"] and not checks["deck_state_pair_source_provenance"]:
        blockers.append("deck_state did not have trusted source provenance for both deck lanes")
    if not checks["deck_lane_context_seen"]:
        blockers.append("rendered live context had no per-deck lane map")
    if not checks["deck_reference_context_seen"]:
        blockers.append("rendered live context had no deck1/deck2 reference map")
    if not checks["deck_source_context_seen"]:
        blockers.append("rendered live context had no deck source/provenance map")
    if not checks["deck_source_status_seen"]:
        blockers.append("no structured deck_source_status was observed")
    if not checks["controller_connected"]:
        blockers.append("controller mixer posture was not connected")
    if not checks["controller_deck_posture_seen"]:
        blockers.append("controller mixer posture did not include both deck A and deck B")
    if not checks["recent_moves_seen"]:
        blockers.append("no recent controller moves were observed")
    if not checks["audio_part_context_seen"]:
        blockers.append("no audio_part_context part-role contract was observed")
    if not checks["deck_audio_separation_context_seen"]:
        blockers.append("no deck_audio_separation_context capture-separation contract was observed")
    if not checks["deck_audio_features_context_seen"]:
        blockers.append("no deck_audio_features_context per-deck audio descriptor was observed")
    if not checks["deck_audio_delta_context_seen"]:
        blockers.append("no deck_audio_delta_context per-deck change descriptor was observed")
    if not checks["deck_audio_window_context_seen"]:
        blockers.append("no deck_audio_window_context pre/current deck-lane window was observed")
    if not checks["deck_pair_capture_configured"]:
        blockers.append("deck-pair audio capture was not configured in the live packet")
        if has_deck_pair_setup_block:
            blockers.append(
                "deck-pair route hint requires a multichannel capture device/opened channels"
            )
    if not checks["deck_audio_capture_evidence_seen"]:
        blockers.append("live_evidence had no deck_audio_capture activity receipt")
    if not checks["deck_audio_capture_active"]:
        blockers.append("deck_audio_capture showed no active deck audio lane")
    if not checks["deck_audio_capture_both_active"]:
        blockers.append("deck_audio_capture did not show active audio on both deck lanes")
    if not checks["deck_audio_features_evidence_seen"]:
        blockers.append("live_evidence had no deck_audio_features descriptor receipt")
    if not checks["deck_audio_delta_evidence_seen"]:
        blockers.append("live_evidence had no deck_audio_delta descriptor receipt")
    if not checks["deck_audio_window_evidence_seen"]:
        blockers.append("live_evidence had no deck_audio_window pre/current descriptor receipt")
    if not checks["audio_window_context_seen"]:
        blockers.append("no time-aligned audio_window_context was observed")
    if not checks["audio_window_map_seen"]:
        blockers.append("no structured audio_window_map was observed")
    if not checks["audio_part_window_labels_consistent"]:
        blockers.append("audio Part labels disagreed with audio_window deck labels")
    if not checks["audio_observed"]:
        blockers.append("live master audio was not observed above the audible floor")
    if not checks["audio_delta_seen"]:
        blockers.append("no bounded audio_delta was observed")
    if not checks["live_evidence_seen"]:
        blockers.append("no structured live_evidence was observed")
    if not checks["transition_gate_seen"]:
        blockers.append("live_evidence had no transition block/watch/candidate gate")
    if not checks["deck_lane_evidence_seen"]:
        blockers.append("live_evidence had no citable deck_lanes atom")
    if not checks["deck_lane_route_evidence_seen"]:
        blockers.append("live_evidence deck_lanes atom had no concrete deck route tiers")
    if not checks["deck_reference_evidence_seen"]:
        blockers.append("live_evidence had no citable deck_reference atom")
    if not checks["deck_reference_route_evidence_seen"]:
        blockers.append("live_evidence deck_reference atom had no concrete deck route tiers")
    if not checks["deck_source_evidence_seen"]:
        blockers.append("live_evidence had no citable deck_source atom")
    stale_live_runtime = bool(
        checks["frames_seen"]
        and checks["flat_deck_frame_seen"]
        and (not checks["live_context_schema_seen"] or not checks["live_context_capabilities_seen"])
    )
    if stale_live_runtime:
        diagnosis = "stale_live_runtime"
        next_action = (
            "Restart the Vibemix live session so the socket advertises "
            f"live_context_schema_version={_VIBER_LIVE_CONTEXT_SCHEMA_VERSION} "
            "and required capabilities "
            + ",".join(sorted(_VIBER_LIVE_CONTEXT_REQUIRED_CAPABILITIES))
            + "; then rerun `vibemix library live-context --require-proof`."
        )
    elif not checks["frames_seen"] or not checks["flat_deck_frame_seen"]:
        diagnosis = "live_socket_missing"
        next_action = (
            "Start the Vibemix live session and keep it open, then rerun "
            "`vibemix library live-context --require-proof`."
        )
    elif blockers:
        diagnosis = "missing_physical_proof"
        next_action = (
            "Collect the missing live proof legs shown in blockers, then rerun "
            "`vibemix library live-context --require-proof`."
        )
    else:
        diagnosis = "ready"
        next_action = "Live Viber deck/audio context proof is ready."

    return {
        "ready": not blockers,
        "diagnosis": diagnosis,
        "next_action": next_action,
        "checks": checks,
        "blockers": blockers,
        "stale_live_runtime": stale_live_runtime,
        "resolved_decks": sorted(resolved_decks),
        "citable_decks": sorted(citable_decks),
        "sourced_decks": sorted(sourced_decks),
        "mixer_posture_sides": mixer_posture_sides,
        "max_music": max_music,
        "live_context_schema_version": schema_version,
        "missing_capabilities": missing_capabilities,
        "deck_source_status": deck_source_status,
        "session_snapshot_seen": bool(session_snapshot_seen),
    }


def _merge_viber_live_context_frame(
    context: dict[str, Any], frame: dict[str, Any]
) -> dict[str, bool]:
    """Merge one ws frame into the bounded Viber live-context draft.

    Flat 30 Hz frames carry ``deck_state``. Schema snapshots carry recent MIDI
    control labels. Keeping this pure lets tests pin the proof path without a
    live controller or socket.
    """
    from vibemix.library.codex_curate import (
        normalize_live_audio_window_map_for_viber,
        normalize_live_source_status_for_viber,
    )
    from vibemix.state.deck_context import (
        normalize_audio_part_context_text,
        normalize_audio_window_context_text,
        normalize_deck_audio_context_text,
        normalize_deck_audio_delta_context_text,
        normalize_deck_audio_features_context_text,
        normalize_deck_audio_separation_context_text,
        normalize_deck_audio_window_context_text,
        normalize_deck_lanes_context_text,
        normalize_deck_reference_context_text,
        normalize_deck_source_context_text,
    )

    flags = {"changed": False, "flat_deck_frame": False, "session_snapshot": False}
    if not isinstance(frame, dict):
        return flags

    if isinstance(frame.get("deck_state"), dict):
        flags["flat_deck_frame"] = True
        reset_live_evidence = "deck_state" in frame
        for key in (
            "live_context_schema_version",
            "live_context_capabilities",
            "deck",
            "audible",
            "music",
            "phase",
            "bpm",
            "deck_state",
            "deck_mixer",
            "deck_lanes_context",
            "deck_reference_context",
            "deck_source_context",
            "deck_source_status",
            "deck_audio_context",
            "deck_audio_separation_context",
            "deck_audio_features_context",
            "deck_audio_delta_context",
            "deck_audio_window_context",
            "audio_part_context",
            "audio_window_context",
            "audio_window_map",
            "audio_delta",
            "live_evidence",
        ):
            if key in frame:
                if key == "music":
                    context[key] = max(_float_or_zero(context.get(key)), _float_or_zero(frame[key]))
                elif key == "live_context_schema_version":
                    schema_version = _viber_live_context_schema_version(frame[key])
                    if schema_version:
                        context[key] = schema_version
                    else:
                        context.pop(key, None)
                elif key == "live_context_capabilities":
                    capabilities = sorted(_viber_live_context_capabilities(frame[key]))
                    if capabilities:
                        context[key] = capabilities
                    else:
                        context.pop(key, None)
                elif key == "audio_delta" and isinstance(frame[key], list):
                    if frame[key] or "audio_delta" not in context:
                        context[key] = frame[key]
                elif key == "audio_window_context":
                    text = normalize_audio_window_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "audio_part_context":
                    text = normalize_audio_part_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_lanes_context":
                    text = normalize_deck_lanes_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_reference_context":
                    text = normalize_deck_reference_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_source_context":
                    text = normalize_deck_source_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_source_status":
                    source_status = normalize_live_source_status_for_viber(frame[key])
                    if source_status:
                        context[key] = source_status
                    else:
                        context.pop(key, None)
                elif key == "deck_audio_context":
                    text = normalize_deck_audio_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_audio_separation_context":
                    text = normalize_deck_audio_separation_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_audio_features_context":
                    text = normalize_deck_audio_features_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_audio_delta_context":
                    text = normalize_deck_audio_delta_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "deck_audio_window_context":
                    text = normalize_deck_audio_window_context_text(frame[key])
                    if text:
                        context[key] = text
                    else:
                        context.pop(key, None)
                elif key == "audio_window_map":
                    audio_window_map = normalize_live_audio_window_map_for_viber(frame[key])
                    if audio_window_map:
                        context[key] = audio_window_map
                    else:
                        context.pop(key, None)
                elif key == "live_evidence" and isinstance(frame[key], dict):
                    if frame[key]:
                        existing = None if reset_live_evidence else context.get(key)
                        context[key] = _merge_viber_live_evidence(existing, frame[key])
                    elif reset_live_evidence:
                        context.pop(key, None)
                else:
                    context[key] = frame[key]
                flags["changed"] = True

    if frame.get("type") == "ipc.session.snapshot" or isinstance(
        (frame.get("payload") if isinstance(frame, dict) else None),
        dict,
    ):
        moves = _session_snapshot_recent_moves(frame)
        if moves:
            context["recent_moves"] = moves
            flags["changed"] = True
        if frame.get("type") == "ipc.session.snapshot":
            flags["session_snapshot"] = True
    return flags


def _viber_live_context_sample_complete(
    context: dict[str, Any],
    *,
    frames_seen: int,
    flat_deck_frame_seen: bool,
    session_snapshot_seen: bool,
    require_proof: bool,
) -> bool:
    if require_proof:
        readiness = _viber_live_context_readiness(
            context,
            frames_seen=frames_seen,
            flat_deck_frame_seen=flat_deck_frame_seen,
            session_snapshot_seen=session_snapshot_seen,
        )
        return bool(readiness.get("ready"))
    return bool(flat_deck_frame_seen and (session_snapshot_seen or "recent_moves" in context))


async def _sample_viber_live_context(
    timeout_s: float = 1.5,
    max_frames: int = 90,
    *,
    require_proof: bool = False,
) -> dict[str, Any]:
    import json as _json

    import websockets

    from vibemix.audio import WS_HOST, WS_PORT
    from vibemix.library.codex_curate import (
        normalize_live_context_for_viber,
        render_live_context_preview,
    )

    timeout_s = max(0.1, float(timeout_s))
    max_frames = max(1, int(max_frames))
    uri = f"ws://{WS_HOST}:{WS_PORT}"
    context: dict[str, Any] = {}
    frames_seen = 0
    flat_seen = False
    snapshot_seen = False
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    try:
        async with websockets.connect(uri) as ws:
            while frames_seen < max_frames:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except TimeoutError:
                    break
                frames_seen += 1
                try:
                    frame = _json.loads(raw)
                except (TypeError, ValueError):
                    continue
                flags = _merge_viber_live_context_frame(context, frame)
                flat_seen = flat_seen or flags["flat_deck_frame"]
                snapshot_seen = snapshot_seen or flags["session_snapshot"]
                if _viber_live_context_sample_complete(
                    context,
                    frames_seen=frames_seen,
                    flat_deck_frame_seen=flat_seen,
                    session_snapshot_seen=snapshot_seen,
                    require_proof=require_proof,
                ):
                    break
    except Exception as exc:
        source_status = _viber_local_source_status()
        normalized_context = normalize_live_context_for_viber(context) or context
        error = str(exc)
        readiness = _viber_live_context_readiness(
            normalized_context,
            frames_seen=frames_seen,
            flat_deck_frame_seen=flat_seen,
            session_snapshot_seen=snapshot_seen,
        )
        return {
            "ok": False,
            "source": uri,
            "frames_seen": frames_seen,
            "flat_deck_frame_seen": flat_seen,
            "session_snapshot_seen": snapshot_seen,
            "live_context": normalized_context,
            "preview": render_live_context_preview(normalized_context),
            "readiness": readiness,
            "source_status": source_status,
            "setup_hint": _viber_setup_hint_from_source_status(source_status, readiness),
            "error": error,
            "hint": _viber_live_context_hint(error, source_status),
        }

    normalized_context = normalize_live_context_for_viber(context) or context
    preview = render_live_context_preview(normalized_context)
    readiness = _viber_live_context_readiness(
        normalized_context,
        frames_seen=frames_seen,
        flat_deck_frame_seen=flat_seen,
        session_snapshot_seen=snapshot_seen,
    )
    source_status = _viber_local_source_status()
    return {
        "ok": bool(preview),
        "source": uri,
        "frames_seen": frames_seen,
        "flat_deck_frame_seen": flat_seen,
        "session_snapshot_seen": snapshot_seen,
        "live_context": normalized_context,
        "preview": preview,
        "readiness": readiness,
        "source_status": source_status,
        "setup_hint": _viber_setup_hint_from_source_status(source_status, readiness),
        "error": None if preview else "No deck/context frames were observed before timeout.",
        "hint": None
        if preview
        else "Keep the live session open and make sure the socket is emitting frames.",
    }


async def _sample_viber_live_context_until_ready(
    *,
    timeout_s: float,
    max_frames: int,
    require_proof: bool,
    wait_ready_s: float = 0.0,
    interval_s: float = 1.0,
) -> dict[str, Any]:
    """Sample once, or keep sampling until the physical proof packet is ready."""
    wait_ready_s = max(0.0, float(wait_ready_s or 0.0))
    interval_s = max(0.1, float(interval_s or 1.0))
    if wait_ready_s > 0:
        require_proof = True

    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_ready_s
    attempts = 0
    while True:
        attempts += 1
        result = await _sample_viber_live_context(
            timeout_s=timeout_s,
            max_frames=max_frames,
            require_proof=require_proof,
        )
        result["proof_attempts"] = attempts
        result["wait_ready_s"] = wait_ready_s
        result["wait_interval_s"] = interval_s

        readiness = result.get("readiness")
        ready = isinstance(readiness, dict) and readiness.get("ready")
        if ready or wait_ready_s <= 0 or not require_proof:
            return result

        remaining = deadline - loop.time()
        if remaining <= 0:
            return result
        await asyncio.sleep(min(interval_s, remaining))


def _cmd_library_live_context(args: argparse.Namespace) -> int:
    import json as _json

    wait_ready_s = float(getattr(args, "wait_ready", 0.0) or 0.0)
    require_proof = bool(getattr(args, "require_proof", False) or wait_ready_s > 0)
    result = asyncio.run(
        _sample_viber_live_context_until_ready(
            timeout_s=float(getattr(args, "timeout", 1.5) or 1.5),
            max_frames=int(getattr(args, "frames", 90) or 90),
            require_proof=require_proof,
            wait_ready_s=wait_ready_s,
            interval_s=float(getattr(args, "interval", 1.0) or 1.0),
        )
    )
    out_path_raw = getattr(args, "out", None)
    if out_path_raw:
        out_path = Path(str(out_path_raw)).expanduser()
        result = {**result, "proof_path": str(out_path)}
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(_json.dumps(result, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"live-context proof write failed: {exc}", file=sys.stderr)
            return 1
    if getattr(args, "json", False):
        _json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif result.get("ok"):
        print(result.get("preview") or "")
        if require_proof and not (
            isinstance(result.get("readiness"), dict) and result["readiness"].get("ready")
        ):
            blockers = (
                result.get("readiness", {}).get("blockers", [])
                if isinstance(result.get("readiness"), dict)
                else []
            )
            if blockers:
                print("live-context proof blockers:", file=sys.stderr)
                for blocker in blockers:
                    print(f"- {blocker}", file=sys.stderr)
            next_action = (
                result.get("readiness", {}).get("next_action")
                if isinstance(result.get("readiness"), dict)
                else None
            )
            if next_action:
                print(f"next action: {next_action}", file=sys.stderr)
            setup_hint = result.get("setup_hint")
            if isinstance(setup_hint, dict) and setup_hint.get("next_action"):
                print(f"setup hint: {setup_hint['next_action']}", file=sys.stderr)
    else:
        print(f"live-context unavailable: {result.get('error')}", file=sys.stderr)
        hint = result.get("hint")
        if hint:
            print(hint, file=sys.stderr)
        setup_hint = result.get("setup_hint")
        if isinstance(setup_hint, dict) and setup_hint.get("next_action"):
            print(f"setup hint: {setup_hint['next_action']}", file=sys.stderr)
    if not result.get("ok"):
        return 1
    if require_proof:
        readiness = result.get("readiness")
        return 0 if isinstance(readiness, dict) and readiness.get("ready") else 1
    return 0


def _cmd_library_curate_codex(args: argparse.Namespace, lib) -> int:
    """Codex backend for `library curate` — spawn `codex exec` + MCP server.

    No genai client needed here: Codex talks to the MCP server (which holds the
    embedder/store). We pass the loaded library only for result-boundary
    grounding re-validation.
    """
    import json as _json

    from vibemix.library.codex_curate import curate_with_codex

    result = curate_with_codex(args.theme, lib, name=args.name)
    out = result.to_dict()

    if result.stop_reason != "created":
        # Plan 100-04 / Decision 6: the clarification path SKIPS the JSON dump
        # + bracket-tagged single-line hint (those don't render the 2-block
        # question + numbered choices layout). The rich 2-block render lives
        # in the dedicated branch below. All other non-success stop_reasons
        # (timeout, codex_*, tool_starvation) keep the pre-100-04 print posture.
        if result.stop_reason == "clarification_needed":
            # Plan 100-04 / Decision 5: exit 11 — reserved range 10-19 for
            # stop_reasons (10 = tool_starvation, 11 = clarification_needed,
            # 12-19 = future). Plan 99-06 RESEARCH.md Pitfall 6 verified path-
            # free vs standard Unix conventions.
            # Decision 6 2-block stderr layout: header + question + numbered
            # choices + re-run hint. stdout stays clean — single-turn contract
            # (vibemix retains NO state; the user re-invokes manually with
            # `<theme> + <chosen option>`).
            print("[viber/codex] clarification_needed:", file=sys.stderr)
            print(f"  {result.question or '(no question)'}", file=sys.stderr)
            print("", file=sys.stderr)
            for i, choice in enumerate(result.choices or [], start=1):
                print(f"  {i}. {choice}", file=sys.stderr)
            print("", file=sys.stderr)
            print(
                f'  Re-run with: library curate "{args.theme} + <chosen option>"',
                file=sys.stderr,
            )
            return 11
        print(_json.dumps(out, indent=2), file=sys.stderr)
        hint = {
            "codex_not_installed": (
                "Install Codex: `npm i -g @openai/codex` (or `brew install "
                "codex`), then `codex login`."
            ),
            "codex_auth_required": "Run `codex login` to connect your ChatGPT plan.",
            "timeout": "Codex took too long — try a narrower theme.",
            # Plan 99-06 / Decision 6: exit 10 carries the propagated hint
            # from Plan 99-04's side-channel; result.error already holds the
            # _build_starvation_payload "hint" string.
            "tool_starvation": result.error or "no playlist (tool starvation)",
        }.get(result.stop_reason, result.error or "no playlist created")
        print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
        # Plan 99-06 / Decision 6: 10 = tool_starvation, 1 = other failures.
        # 11 = clarification_needed handled above (Plan 100-04).
        return 10 if result.stop_reason == "tool_starvation" else 1

    _json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    where = result.m3u_path or "~/.cache/vibemix/playlists/"
    print(
        f"-> playlist '{result.playlist_name}' ({len(result.track_ids)} tracks) "
        f"via Codex saved: {where}",
        file=sys.stderr,
    )
    return 0


def _cmd_library_build_set_codex(args: argparse.Namespace, lib) -> int:
    """Codex backend for `library build-set` — set-prep via `codex exec` + MCP.

    Codex drives the discover → sequence → export tool surface on the MCP server;
    we pass the loaded library only for result-boundary grounding re-validation.
    Emits the same JSON contract the Tauri `map_curate_result` bridge reads
    (playlist_name / track_ids / rationale / export_path).
    """
    import json as _json

    from vibemix.library.codex_curate import build_set_with_codex

    result = build_set_with_codex(
        args.brief,
        lib,
        curve=getattr(args, "curve", None),
        name=getattr(args, "name", None),
        n_slots=getattr(args, "n_slots", None),
        export=getattr(args, "export", None) == "rekordbox",
    )
    out = result.to_dict()

    if result.stop_reason not in ("created", "exported"):
        # Plan 100-04 / Decision 6: clarification path renders the 2-block
        # question + numbered choices layout BEFORE the single-line hint path.
        # Sibling parity with _cmd_library_curate_codex above; the re-run hint
        # uses `library build-set` and echoes args.brief (build-set takes brief,
        # curate takes theme).
        if result.stop_reason == "clarification_needed":
            # Plan 100-04 / Decision 5: exit 11 (reserved range 10-19).
            print("[viber/codex] clarification_needed:", file=sys.stderr)
            print(f"  {result.question or '(no question)'}", file=sys.stderr)
            print("", file=sys.stderr)
            for i, choice in enumerate(result.choices or [], start=1):
                print(f"  {i}. {choice}", file=sys.stderr)
            print("", file=sys.stderr)
            print(
                f'  Re-run with: library build-set "{args.brief} + <chosen option>"',
                file=sys.stderr,
            )
            return 11
        print(_json.dumps(out, indent=2), file=sys.stderr)
        hint = {
            "codex_not_installed": (
                "Install Codex: `npm i -g @openai/codex` (or `brew install "
                "codex`), then `codex login`."
            ),
            "codex_auth_required": "Run `codex login` to connect your ChatGPT plan.",
            "timeout": "Codex took too long — try a narrower brief.",
            # Plan 99-06 / Decision 6: same side-channel propagation surface
            # as curate above; result.error carries the hint.
            "tool_starvation": result.error or "no set (tool starvation)",
        }.get(result.stop_reason, result.error or "no set created")
        print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
        # Plan 99-06 / Decision 6: 10 = tool_starvation, 1 = other failures.
        # 11 = clarification_needed handled above (Plan 100-04).
        return 10 if result.stop_reason == "tool_starvation" else 1

    _json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    print(
        f"-> set '{result.playlist_name}' ({len(result.track_ids)} tracks) via Codex"
        + (f"; exported: {result.export_path}" if result.export_path else ""),
        file=sys.stderr,
    )
    return 0


def _cmd_library_build_set(args: argparse.Namespace) -> int:
    """Vibe Mix set-prep co-host — brief → discovered + sequenced set.

    Mirrors ``_cmd_library_curate``'s library-cache setup, then runs the local
    Codex/MCP set-prep surface. Prints the chosen sequence slot-by-slot + the
    agent's per-transition rationale + any export path. Fail-actionable when
    the library cache is missing.
    """
    import json as _json

    from vibemix.library import RekordboxLibrary

    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        print(
            _json.dumps(
                {
                    "error": (
                        "No library cache. Drag a Rekordbox XML onto "
                        "Settings → Library (or run `library embed-folder`) first."
                    ),
                    "set": None,
                }
            ),
            file=sys.stderr,
        )
        return 1

    backend = getattr(args, "backend", "codex")
    if backend != "codex":
        print(
            _json.dumps(
                {
                    "error": (
                        "Unsupported Viber backend. Library/Viber uses local "
                        "Codex; run `codex login` and retry with --backend codex."
                    ),
                    "set": None,
                }
            ),
            file=sys.stderr,
        )
        return 2

    # Codex talks to the MCP server (which holds embedder/store); no local
    # genai client needed. Mirrors `_cmd_library_curate_codex`.
    return _cmd_library_build_set_codex(args, lib)


def _validate_export_tracks_against_library(tracks: list, library) -> tuple[list, list[dict]]:
    """WR-03: re-validate each set item against the live library (grounding).

    A track resolves if its ``track_id`` is a known library id OR its
    ``filepath`` (normpath) matches a library entry's filepath. Unresolved
    items are dropped and returned in a ``dropped`` list (with a reason) so the
    caller can report the count honestly — the export must never reference a
    track the library does not contain.
    """
    import os as _os

    known_ids = set(library.tracks)
    known_paths = {
        _os.path.normpath(e.filepath)
        for e in library.tracks.values()
        if getattr(e, "filepath", None)
    }
    kept: list = []
    dropped: list[dict] = []
    for item in tracks:
        if not isinstance(item, dict):
            dropped.append({"item": repr(item)[:80], "reason": "not a track dict"})
            continue
        tid = item.get("track_id")
        fp = item.get("filepath")
        fp_norm = _os.path.normpath(str(fp)) if fp else None
        if (tid in known_ids) or (fp_norm is not None and fp_norm in known_paths):
            kept.append(item)
        else:
            dropped.append(
                {
                    "track_id": tid,
                    "title": item.get("title", ""),
                    "reason": "not in library (ungrounded)",
                }
            )
    return kept, dropped


def _cmd_library_export_set(args: argparse.Namespace) -> int:
    """Export a saved JSON set to a Rekordbox-importable XML.

    Reads ``set_json`` (a list of track dicts, or a ``{"tracks": [...]}``
    wrapper), and writes the XML via ``export_rekordbox.export_set``.

    WR-03 grounding: when a library cache is present, every track is
    re-validated against the live library (by track_id or filepath) and
    ungrounded entries are DROPPED before export (count reported). Without a
    cache the export still runs, but prints a clear "advanced/unvalidated"
    notice — the operator owns the JSON's correctness.
    """
    import json as _json

    from vibemix.library import RekordboxLibrary, export_rekordbox

    try:
        with open(args.set_json, encoding="utf-8") as fh:
            data = _json.load(fh)
    except OSError as e:
        print(_json.dumps({"error": f"cannot read set file: {e}"}), file=sys.stderr)
        return 1
    except ValueError as e:
        print(_json.dumps({"error": f"invalid JSON set: {e}"}), file=sys.stderr)
        return 1

    if isinstance(data, dict):
        tracks = data.get("tracks")
        name = data.get("name") or args.name
    else:
        tracks = data
        name = args.name
    if not isinstance(tracks, list) or not tracks:
        print(
            _json.dumps(
                {"error": "set file must be a non-empty list of track dicts (or {tracks:[...]})."}
            ),
            file=sys.stderr,
        )
        return 1

    # WR-03: re-validate against the live library when a cache is present.
    ungrounded: list[dict] = []
    lib = RekordboxLibrary()
    if lib.try_load_cache():
        tracks, ungrounded = _validate_export_tracks_against_library(tracks, lib)
        if ungrounded:
            print(
                f"-> dropped {len(ungrounded)} ungrounded track(s) (not in library)",
                file=sys.stderr,
            )
        if not tracks:
            print(
                _json.dumps(
                    {
                        "error": "no track resolved in the library — nothing to "
                        "export (all entries ungrounded).",
                        "dropped_ungrounded": ungrounded,
                    }
                ),
                file=sys.stderr,
            )
            return 1
    else:
        print(
            "-> WARNING: no library cache — exporting UNVALIDATED tracks "
            "(advanced mode). Import a Rekordbox XML or run `library "
            "embed-folder` to enable grounding.",
            file=sys.stderr,
        )

    try:
        result = export_rekordbox.export_set(tracks, name, args.out)
    except Exception as e:
        print(
            _json.dumps({"error": f"export failed: {type(e).__name__}: {e}"}),
            file=sys.stderr,
        )
        return 1

    summary = {
        "exported": True,
        "path": str(result.path),
        "written": result.written,
        "referenced": result.referenced,
        "dropped": result.dropped,
        "dropped_ungrounded": ungrounded,
    }
    _json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    print(
        f"-> set '{name}' exported: {result.path} "
        f"({result.written} tracks, {result.referenced} slots)",
        file=sys.stderr,
    )
    return 0


def _normalize_codex_curate_result(
    result: CodexCurateResult,
) -> dict | None:
    """Plan 99-06 / Decision 8 — Telegram ``curate_fn`` normalizer.

    When ``result.stop_reason == "tool_starvation"``, return the uniform
    starvation payload Plan 99-07's ``format_reply`` consumes::

        {"ok": False, "stop_reason": "tool_starvation", "hint": <error string>}

    When ``result.stop_reason == "clarification_needed"`` (Plan 100-04 sibling
    extension), return the uniform clarification payload Plan 100-05's
    ``format_reply`` branch consumes::

        {"ok": False, "stop_reason": "clarification_needed",
         "question": <str>, "choices": list[str]}

    For every OTHER ``stop_reason`` (``created`` / ``timeout`` / etc.), return
    ``None`` so ``curate_fn`` falls through to its existing happy-path /
    generic-error branches — pre-99-06 behavior preserved.

    Defensive: ``result.error`` may be ``None`` (the side-channel write loop
    always populates it, but the dataclass default is None). Similarly,
    ``result.question`` / ``result.choices`` default to None on the cold path
    and the Plan 100-03 wrapper's isinstance defenses may leave them None on
    malformed payloads. The ``or ""`` / ``or []`` fallbacks keep the payload
    dict-shape stable for ``format_reply`` — Plan 100-05 can iterate
    ``payload["choices"]`` without None-guards.
    """
    if result.stop_reason == "tool_starvation":
        return {
            "ok": False,
            "stop_reason": "tool_starvation",
            "hint": result.error or "",
        }
    # Plan 100-04: sibling extension. Telegram (Plan 100-05) format_reply
    # branches on stop_reason == "clarification_needed" and reads question +
    # choices to render the disambiguation prompt (leak-stripped + numbered).
    if result.stop_reason == "clarification_needed":
        return {
            "ok": False,
            "stop_reason": "clarification_needed",
            "question": result.question or "",
            "choices": list(result.choices or []),
        }
    return None


def _cmd_library_telegram(args: argparse.Namespace) -> int:
    """Run the Telegram mobile surface — curate playlists from your phone.

    Wires the same local Codex Viber backend behind a long-poll bot. A fresh
    Codex run is spawned per message, then the result is re-validated before it
    reaches chat. Blocking until Ctrl-C.
    """
    import json as _json

    from vibemix.library import RekordboxLibrary
    from vibemix.library.codex_curate import curate_with_codex
    from vibemix.library.telegram_bridge import (
        TelegramDependencyError,
        build_bridge_from_env,
        telegram_dependency_error,
    )

    dep_err = telegram_dependency_error()
    if dep_err is not None:
        print(_json.dumps({"error": dep_err}), file=sys.stderr)
        return 1

    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        print(
            _json.dumps(
                {
                    "error": (
                        "No library cache. Import a Rekordbox XML or run "
                        "`library embed-folder` first."
                    )
                }
            ),
            file=sys.stderr,
        )
        return 1

    def curate_fn(theme: str) -> dict:
        result = curate_with_codex(theme, lib)
        # Plan 99-06 / Decision 8: starvation gets the normalized payload
        # Plan 99-07's format_reply will branch on. Non-starvation falls
        # through to the existing happy-path / generic-error branches.
        normalized = _normalize_codex_curate_result(result)
        if normalized is not None:
            return normalized
        if result.playlist_name is None or not result.track_ids:
            return {
                "ok": False,
                "error": result.error or f"no playlist ({result.stop_reason})",
            }
        titles: list[str] = []
        for tid in result.track_ids:
            e = lib.lookup_by_id(tid)
            if e is None:
                continue  # grounding: only real tracks ever reach the chat
            titles.append(f"{e.artist} - {e.title}".strip(" -"))
        return {"ok": True, "name": result.playlist_name, "titles": titles}

    bridge, berr = build_bridge_from_env(curate_fn)
    if berr is not None:
        print(_json.dumps({"error": berr}), file=sys.stderr)
        print(f"[viber/telegram] {berr}", file=sys.stderr)
        return 1

    print("-> Telegram bridge: long-poll started (Ctrl-C to stop)", file=sys.stderr)
    try:
        assert bridge is not None
        bridge.run()  # blocking until interrupted
    except TelegramDependencyError as e:
        print(_json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    return 0


def _cmd_library_embed_folder(args: argparse.Namespace) -> int:
    """quick-260525-gz2 — embed a raw audio folder locally with CLAP ONNX."""
    import json as _json
    from pathlib import Path as _Path

    from vibemix.library import (
        build_embedder,
        ingest_folder,
        open_store,
    )

    folder = _Path(args.path)
    if not folder.is_dir():
        print(
            f"[FATAL] embed-folder: {args.path!r} is not a directory.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    strategy = getattr(args, "strategy", "mean_excerpt")
    embedder = build_embedder(embed_strategy=strategy)
    store = open_store()
    as_json = bool(getattr(args, "json", False))
    print("-> embed-folder: embedder=CLAP ONNX (local, keyless)", file=sys.stderr)
    if strategy != "mean_excerpt":
        print(f"-> embed-folder: strategy={strategy}", file=sys.stderr)

    def _progress(line: str) -> None:
        if not as_json:
            print(line, flush=True)

    try:
        report = ingest_folder(
            folder,
            embedder,
            store,
            persist_library=True,
            progress=_progress,
            embed_strategy=strategy,
        )
    finally:
        store.close()

    if as_json:
        _json.dump(report.as_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    from vibemix.library.rekordbox import RekordboxLibrary

    print(
        f"\nembed-folder done: embedded={report.embedded} "
        f"skipped_cached={report.skipped_cached} failed={report.failed} "
        f"total={report.total}  ~€{report.cost_estimate_eur:.4f}"
    )
    print(f"-> library cache: {RekordboxLibrary.CACHE_PATH}")
    print(
        '-> query it: `vibemix library search "<vibe text>"` or '
        "`vibemix library similar <folder:hash>` "
        "(re-run with --json to copy a track_id seed)."
    )
    return 0


def _cmd_library_ingest(args: argparse.Namespace) -> int:
    """Phase 89 Plan 01 — detect → parse → CLAP-embed → store one DJ library.

    KEYLESS + on-device: ingest embeds via ``ClapEngine`` — no genai client, no
    API cost, audio never leaves the machine. Auto-detects the Rekordbox
    collection.xml at its standard export location, or accepts an explicit
    ``path``.
    """
    import json as _json

    from vibemix.library.anlz_ingest import build_anlz_index
    from vibemix.library.clap_engine import ClapEngine
    from vibemix.library.ingest import ingest_source
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.library.sources.rekordbox import RekordboxSource
    from vibemix.library.store import open_store

    explicit = getattr(args, "path", None)
    source = RekordboxSource(xml_path=explicit) if explicit else RekordboxSource()

    if not source.detect():
        probed = ", ".join(str(p) for p in source.default_paths())
        print(
            "[FATAL] library ingest: no Rekordbox collection.xml found. Export "
            "one via Rekordbox → File → Export Collection in xml format, then "
            "re-run `vibemix library ingest <path>` (or place it at a standard "
            f"location). Probed: {probed}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        f"-> library ingest: source=rekordbox xml={source.resolved_path}",
        file=sys.stderr,
    )
    print("-> library ingest: embedder=ClapEngine (on-device, keyless)", file=sys.stderr)
    try:
        anlz_index = build_anlz_index()
        anlz_count = sum(len(items) for items in anlz_index.by_basename.values())
        if anlz_count:
            print(
                f"-> library ingest: ANLZ structure index={anlz_count} tracks",
                file=sys.stderr,
            )
        else:
            print(
                "-> library ingest: ANLZ structure index empty (DJ/auto-cue fallback remains)",
                file=sys.stderr,
            )
            anlz_index = None
    except Exception as e:
        print(
            f"-> library ingest: ANLZ structure index unavailable ({e}); "
            "DJ/auto-cue fallback remains",
            file=sys.stderr,
        )
        anlz_index = None

    # The embedder exposes embed_audio_file(path) -> np.ndarray; ingest_source
    # reads its .backend tag for the content-hash cache namespace.
    embedder = ClapEngine()
    store = open_store()
    as_json = bool(getattr(args, "json", False))

    def _progress(line: str) -> None:
        if not as_json:
            print(line, flush=True)

    try:
        report = ingest_source(
            source,
            embedder,
            store,
            persist_library=True,
            progress=_progress,
            anlz_index=anlz_index,
        )
    finally:
        store.close()

    if as_json:
        _json.dump(report.as_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(
        f"\nlibrary ingest done: embedded={report.embedded} "
        f"skipped_cached={report.skipped_cached} failed={report.failed} "
        f"total={report.total}"
    )
    print(f"-> library cache: {RekordboxLibrary.CACHE_PATH}")
    print(
        '-> query it: `vibemix library search "<vibe text>"` or '
        "`vibemix library similar <track_id>`."
    )
    return 0


def _cmd_library_budget(args: argparse.Namespace) -> int:
    """Legacy Gemini Embedding projection plus current runtime telemetry."""
    import json as _json
    from dataclasses import asdict as _asdict

    from vibemix.library._cosine import EMBED_BACKEND
    from vibemix.library.budget import (
        get_telemetry,
        project_monthly_cost,
    )

    p = project_monthly_cost(dau=args.dau)
    tel = get_telemetry()
    projection_kind = "legacy_gemini_embedding_what_if"

    if getattr(args, "json", False):
        _json.dump(
            {
                "projection": _asdict(p),
                "projection_kind": projection_kind,
                "active_embedding_backend": EMBED_BACKEND,
                "telemetry": tel.as_dict(),
                "dau": args.dau,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    print(f"\nLegacy Gemini Embedding Cost Projection @ DAU={args.dau}\n")
    print(f"  Active library embedding backend: {EMBED_BACKEND} (local; telemetry below)")
    print("  Projection kind: legacy Gemini Embedding what-if, not the CLAP default")
    print()
    print("  Feature                         Monthly (EUR)")
    print(f"  One-time library indexing       {p.indexing_eur:>8.2f}")
    print(f"  Vibe-search NL queries          {p.vibe_search_eur:>8.2f}")
    print(f'  "What\'s playing" grounding      {p.grounding_eur:>8.2f}')
    print(f"  Track-to-track similarity       {p.similar_eur:>8.2f}")
    print(f"  Session-end retrieval embed     {p.session_retrieval_eur:>8.2f}")
    print("  ────────────────────────────────────────────")
    print(f"  Total                           {p.total_eur:>8.2f}")
    print(f"  Ceiling                         {p.ceiling_eur:>8.2f}")
    print(f"  Under budget                    {p.under_budget}")
    print()
    print("Runtime telemetry (this process):")
    td = tel.as_dict()
    print(f"  audio_embeds:               {td['audio_embeds']}")
    print(f"  text_embeds:                {td['text_embeds']}")
    print(f"  cache_hits:                 {td['cache_hits']}")
    print(f"  current_cost_estimate_eur:  {td['current_cost_estimate_eur']:.4f}")
    print(f"  cost_warning_active:        {td['cost_warning_active']}")
    return 0


def _library_agent_setup_status() -> dict[str, object]:
    """Offline Viber backend setup status for app preflight UI.

    This is intentionally cheap: no network, no `codex exec`, no Gemini client
    construction. Runtime chat/curate/build still owns the authoritative run
    result; this only lets the app show obvious setup gaps before the user hits
    a failing Viber turn.
    """
    from vibemix.library.codex_curate import find_codex

    if find_codex() is None:
        return {
            "agent_backend": "codex",
            "agent_ready": False,
            "agent_status": "codex_not_installed",
            "agent_hint": (
                "Install Codex (`npm i -g @openai/codex` or "
                "`brew install codex`) and run `codex login`."
            ),
        }
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    if not (codex_home / "auth.json").exists():
        return {
            "agent_backend": "codex",
            "agent_ready": False,
            "agent_status": "codex_auth_required",
            "agent_hint": "Run `codex login` to connect your ChatGPT plan.",
        }
    return {
        "agent_backend": "codex",
        "agent_ready": True,
        "agent_status": "ready",
        "agent_hint": "",
    }


def _cmd_library_doctor(args: argparse.Namespace) -> int:
    """Live capability self-check. Runs every grounded-tool probe and prints a
    human table (or ``--json``). Exit 0 when all checks pass, else 1 — so it can
    gate a setup script. Never crashes: a failed probe is a finding, not a raise.
    """
    import json as _json

    from vibemix.library.doctor import format_report, run_doctor

    report = run_doctor()
    if getattr(args, "json", False):
        print(_json.dumps(report, indent=2))
    else:
        print(format_report(report), file=sys.stderr)
    return 0 if report["all_ok"] else 1


def _cmd_library_stats(args: argparse.Namespace) -> int:
    """Offline library-store stats for the desktop Vibe Engine header.

    Reads ONLY the local sqlite-vec / numpy store row count — no Gemini /
    genai / httpx call, mirroring ``library budget --json`` (offline by
    design). The Rust bridge (``library_cmds.rs::library_stats``) hardcodes
    ``indexed:0, failed:0`` today because no zero-network source existed;
    this is that source.

    Emits ``{"indexed": <row_count>, "backend": "sqlite-vec"|"numpy",
    "embedding_backend": "clap", "embedding_dim": 512, agent setup fields,
    "failed": 0}``. ``failed`` has no persisted source today, so it is honestly
    ``0`` (not invented). Never crashes / never networks: if the store cannot
    be opened, falls back to ``indexed:0, backend:"unknown"``.
    """
    import json as _json

    indexed = 0
    backend = "unknown"
    try:
        from vibemix.library.store import open_store

        store = open_store()
        try:
            # backend_name is the class name (SqliteVecStore / NumpyStore);
            # map to the friendly tag the header expects.
            cls = store.backend_name
            backend = "sqlite-vec" if cls == "SqliteVecStore" else "numpy"
            count = store.row_count()
            indexed = int(count) if count is not None else 0
        finally:
            store.close()
    except Exception as e:  # never network, never crash — header must render
        print(f"[library stats] store unavailable: {e}", file=sys.stderr)

    from vibemix.library._cosine import EMBED_BACKEND, EMBEDDING_DIM
    from vibemix.library.clap_engine import onnx_model_status

    model_status = onnx_model_status()

    payload = {
        "indexed": indexed,
        "backend": backend,
        "embedding_backend": EMBED_BACKEND,
        "embedding_dim": EMBEDDING_DIM,
        "clap_model_installed": bool(model_status["installed"]),
        "clap_model_path": model_status["path"],
        "clap_model_missing": model_status["missing"],
        **_library_agent_setup_status(),
        "failed": 0,
    }

    if getattr(args, "json", False):
        _json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print("\nLibrary stats")
    print(f"  indexed:  {indexed}")
    print(f"  backend:  {backend}")
    print(f"  embedder: {EMBED_BACKEND} ({EMBEDDING_DIM}d)")
    print(f"  agent:    {payload['agent_backend']} ({payload['agent_status']})")
    print(
        "  model:    "
        + ("installed" if payload["clap_model_installed"] else "missing")
        + f" ({payload['clap_model_path']})"
    )
    print("  failed:   0")
    return 0


def _cmd_library_models(args: argparse.Namespace) -> int:
    """Offline local-model status for setup/install UX."""
    import json as _json

    install_result = None
    if getattr(args, "install", None):
        from vibemix.library.model_assets import install_models

        progress = None
        if bool(getattr(args, "progress", False)):

            def progress(frame: dict[str, object]) -> None:
                sys.stderr.write(
                    "VIBEMIX_MODEL_PROGRESS " + _json.dumps(frame, separators=(",", ":")) + "\n"
                )
                sys.stderr.flush()

        if progress is None:
            install_result = install_models(
                str(args.install), force=bool(getattr(args, "force", False))
            )
        else:
            install_result = install_models(
                str(args.install),
                force=bool(getattr(args, "force", False)),
                progress=progress,
            )

    from vibemix.library.clap_engine import onnx_model_status
    from vibemix.library.cue_detr import model_status as cue_model_status
    from vibemix.library.model_assets import cue_model_installable

    clap = onnx_model_status()
    cue = cue_model_status()
    models = [
        {
            "id": "clap",
            "label": "CLAP ONNX",
            "role": "library embeddings/search/similarity",
            "required": True,
            "env": "VIBEMIX_CLAP_ONNX_DIR",
            "installed": bool(clap["installed"]),
            "installable": True,
            "path": clap["path"],
            "missing": clap["missing"],
            "mismatched": clap.get("mismatched", []),
        },
        {
            "id": "cue-detr",
            "label": "CUE-DETR ONNX",
            "role": "cue-anchored ingest and structural cue detection",
            "required": False,
            "env": "VIBEMIX_CUE_ONNX_PATH",
            "installed": bool(cue["installed"]),
            "installable": cue_model_installable(),
            "path": cue["path"],
            "missing": cue["missing"],
            "mismatched": cue.get("mismatched", []),
        },
    ]
    payload = {
        "models": models,
        "required_ready": all(bool(m["installed"]) for m in models if bool(m["required"])),
        "all_ready": all(bool(m["installed"]) for m in models),
    }
    if install_result is not None:
        payload["install"] = install_result
    exit_code = 0 if install_result is None or bool(install_result["ok"]) else 1

    if getattr(args, "json", False):
        _json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return exit_code

    if install_result is not None:
        print("\nModel install")
        for result in install_result["results"]:
            status = "ok" if not result["errors"] else "needs attention"
            print(f"  {result['id']}: {status}")
            for file_result in result["files"]:
                print(
                    f"    {file_result['status']}: "
                    f"{file_result['rel_path']} ({file_result['size']} bytes)"
                )
            for error in result["errors"]:
                print(f"    error: {error}")

    print("\nLocal model assets")
    for model in models:
        status = "installed" if model["installed"] else "missing"
        if model.get("mismatched"):
            status = "needs repair"
        requirement = "required" if model["required"] else "optional"
        print(f"  {model['label']}: {status} ({requirement})")
        print(f"    role:    {model['role']}")
        print(f"    path:    {model['path']}")
        if model["missing"]:
            print(f"    missing: {', '.join(model['missing'])}")
        if model.get("mismatched"):
            print(f"    repair:  {', '.join(model['mismatched'])}")
        print(f"    env:     {model['env']}")
    return exit_code


def cli_entry(argv: list[str] | None = None) -> None:
    """Synchronous CLI entry. Parses args (``--version`` short-circuits via
    argparse's ``action="version"``), then routes to one of three runtimes:

    * ``--wizard``           → ``run_wizard`` (first-run calibration flow)
    * ``--session``          → ``run_session`` (diagnostic/bootstrap IPC loop;
                                no cascade graph)
    * (default, both unset)  → ``main()`` (full live runtime — cascade agent +
                                audio I/O + ws_broadcast)

    The Tauri shell currently spawns ``vibemix --wizard`` on first run
    and ``vibemix`` (no flag — full runtime) thereafter.
    """
    _enable_line_buffering()
    # Phase 28 — `vibemix library <subcommand>` is dispatched BEFORE
    # _parse_args so the legacy --wizard / --session / --debrief flag layer
    # is untouched. Plan 28-03 owns `search`; Plan 28-05 will add `similar`,
    # Plan 28-08 will add `budget` via the same _build_library_subparsers
    # helper below.
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    # Packaged-Viber fix: Codex launches the STDIO MCP server as
    # ``sys.executable -m vibemix.library.mcp_server <flags>`` (see
    # library/codex_curate.py). A real interpreter consumes ``-m`` and runs the
    # module before main() is ever reached; a PyInstaller binary does NOT — the
    # bootloader passes ``-m`` straight through as argv[0]. Without this
    # intercept the bundled sidecar would treat ``-m`` as an unknown flag (or
    # fall through to the live session), Codex would get no grounded tools, and
    # shipped Viber would be dead (search_vibe et al. unreachable). Hand off to
    # the server's main(), rewriting argv so its sys.argv[1:] parser sees only
    # the trailing flags — i.e. exactly the ``python -m`` contract. In a real
    # interpreter this branch never triggers, so the dev path is untouched.
    if raw_argv[:2] == ["-m", "vibemix.library.mcp_server"]:
        from vibemix.library.mcp_server import main as _mcp_main

        sys.argv = [sys.argv[0], *raw_argv[2:]]
        _mcp_main()
        sys.exit(0)
    if raw_argv and raw_argv[0] == "library":
        sys.exit(_run_library_cli(raw_argv[1:]))
    # Phase 81 — `vibemix bench <sub>` (the validation-instrument produce step),
    # dispatched the same way as `library` so the legacy flag layer is untouched.
    if raw_argv and raw_argv[0] == "bench":
        sys.exit(_run_bench_cli(raw_argv[1:]))
    # Phase 92 (LESSON-03) — `vibemix learn <sub>` dispatch. v9.0 ships ONE
    # subcommand: `learn reset` (wipes ~/.cache/vibemix/learn-progress.json).
    # Dispatched the same way as `library` / `bench` — short-circuits BEFORE
    # `asyncio.run(main())` so the live runtime never starts when the CLI
    # subcommand is invoked (T-92-04-05 mitigation: no path where reset runs
    # concurrent with a live session). Idempotent — reset_progress is a no-op
    # when the file is already absent.
    if raw_argv and raw_argv[0] == "learn":
        if len(raw_argv) >= 2 and raw_argv[1] == "reset":
            from vibemix.learn.progress import reset_progress

            reset_progress()
            print("learn progress reset.", file=sys.stdout, flush=True)
            sys.exit(0)
        # Phase 93 (EXEMPLAR-01..05) — `vibemix learn exemplar <band>` dev-loop
        # surface. Dispatches `ExemplarFinder.find(band, k=1)` and prints the
        # 4-line `track:/path:/score:/why:` block when a pick resolves
        # (library OR packaged fallback); exits 1 ("honest null") when both
        # library and bank are empty; exits 2 on unknown bands (T-93-06-01:
        # band allow-list check BEFORE any SQL/file operation). Same
        # short-circuit semantics as `learn reset` — the live runtime never
        # starts when the CLI subcommand is invoked.
        if len(raw_argv) >= 3 and raw_argv[1] == "exemplar":
            band = raw_argv[2]
            if band not in ("sub", "low", "mid", "high"):
                print(
                    f"vibemix learn exemplar: unknown band {band!r}; "
                    "must be one of sub/low/mid/high",
                    file=sys.stderr,
                    flush=True,
                )
                sys.exit(2)
            from vibemix.learn.exemplar import ExemplarFinder

            finder = ExemplarFinder()
            result = finder.find(band, k=1)
            if not result:
                print(
                    f"learn exemplar {band}: no library track passed the floor; "
                    "no packaged fallback found either.",
                    file=sys.stdout,
                    flush=True,
                )
                sys.exit(1)
            pick = result[0]
            print(f"track: {pick.track_id}", file=sys.stdout)
            print(f"path:  {pick.file_path}", file=sys.stdout)
            print(f"score: {band}_share={pick.band_score:.3f}", file=sys.stdout)
            print(f"why:   {pick.reason}", file=sys.stdout)
            sys.exit(0)
        # Unknown `learn` subcommand — surface usage + exit 2 (argparse-style).
        print(
            f"vibemix learn: unknown subcommand {raw_argv[1:]!r}; "
            "available: reset, exemplar <sub|low|mid|high>",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)

    args = _parse_args(argv)
    # v8.0 LOG-04 — apply the verbose-logging switch before any dispatch so the
    # wizard / session / debrief / live-runtime paths all honour it. The env
    # (VIBEMIX_DEBUG_LOG) is the floor; the flag can only raise verbosity.
    from vibemix.runtime.debug_flags import set_debug_log

    set_debug_log(bool(getattr(args, "debug_log", False)))
    try:
        if args.debrief is not None:
            # Debrief sidecar. Dispatched before --wizard / --session because
            # it MUST NOT engage audio I/O or LiveKit.
            _run_debrief_sidecar(session_dir=args.debrief)
            return
        if args.wizard:
            # Deferred import — the live-runtime path doesn't need the
            # wizard module loaded.
            from vibemix.runtime.wizard import run_wizard

            asyncio.run(run_wizard())
        elif args.session:
            # Sidecar-only session loop for diagnostic/bootstrap checks against
            # a real Python WS bus.
            from vibemix.runtime.session_loop import run_session

            asyncio.run(run_session())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli_entry()
