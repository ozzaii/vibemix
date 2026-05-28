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
import signal
import sys
import threading
from collections import deque
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv

from vibemix import __version__
from vibemix._main_helpers import apply_genre_env

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
from vibemix.audio.recorder import sweep_crashed_sessions
from vibemix.audio.resample import resample_audio
from vibemix.coach import (
    STRIPPED_RATE_THRESHOLD,
    CitationIpcShim,
    CitationLinter,
    StrippedRateTracker,
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
):
    """Verbatim port of cohost_v4.py:912-945 input stream callback."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(indata.tobytes())

        music48 = indata.mean(axis=1).astype(np.float32)
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

    # ----- Phase 5 mode dispatch -----
    mode = os.environ.get("VIBEMIX_LLM_MODE", "direct").lower()
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
    try:
        input_idx = audio_backend.find_device(INPUT_DEVICE, "input")
        output_idx = audio_backend.find_device(OUTPUT_DEVICE, "output")
    except RuntimeError as e:
        # Most common real-world fail: BlackHole 2ch isn't installed
        # (INPUT_DEVICE missing). Exit 3 is the sidecar's "audio-device-
        # missing" sentinel — the Tauri shell shows a setup banner with
        # the BlackHole install link rather than the generic crash UI.
        is_input_miss = INPUT_DEVICE in str(e)
        device_kind = "input" if is_input_miss else "output"
        device_name = INPUT_DEVICE if is_input_miss else OUTPUT_DEVICE
        print(
            f"[FATAL] required audio device missing: {device_name!r} ({device_kind})",
            file=sys.stderr,
            flush=True,
        )
        print(f"[FATAL] {e}", file=sys.stderr, flush=True)
        if is_input_miss:
            print(
                "[FATAL] install BlackHole 2ch via `brew install blackhole-2ch` "
                "or https://existential.audio/blackhole/",
                file=sys.stderr,
                flush=True,
            )
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
    # In-process IpcBus shim — Plan 20-04's coach_loop publish gate
    # duck-types against ``await ipc_bus.emit(dict)``. The shim buffers each
    # SessionCitation envelope into a bounded deque (no I/O). v2.x follow-up
    # multiplexes the buffer onto the mascot ws_broadcast clients (the WS
    # port is already owned by ws_broadcast — see citation_ipc_shim docstring
    # for the two-option v2.x wiring path).
    citation_shim: CitationIpcShim | None = CitationIpcShim() if anti_slop_enabled else None

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
    recall_enabled = os.environ.get("VIBEMIX_RECALL_ENABLED", "0").strip().lower() not in (
        "0",
        "off",
        "false",
        "",
    )
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

    # ── Plan 28-07 — 30-day staleness nudge ──
    # Once-per-boot check. emit_ipc currently logs to stdout; the renderer
    # IpcBus subscription is added in the same wave's UI banner spec. Plan
    # 28-09's ipc.library.staleness_nudge schema validates the payload shape.
    try:
        from vibemix.library import emit_nudge_if_stale as _emit_staleness

        def _staleness_emit(msg_type: str, payload: dict) -> None:
            # v1: log a structured line; the WS bus broadcast path lands
            # alongside the Plan 28-06 drag-drop wiring (same renderer
            # subscription pipeline).
            print(
                f"-> [ipc.outbound] {msg_type} {payload}",
                flush=True,
            )

        _emit_staleness(_staleness_emit, library_cache)
    except Exception as e:
        print(f"-> staleness check failed: {e}", file=sys.stderr)

    # ── Plan 28-04 — grounding pipeline (event-gated, local CLAP) ──
    # Build Grounding lazily when a library cache exists. Embeddings are local
    # CLAP ONNX/512 through build_embedder(); the Gemini client is for the live
    # co-host brain/TTS only, not for library grounding embeddings.
    grounding = None
    suggestion_service = None
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

    session = AgentSession(llm=llm_inst, tts=tts_inst)
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
    from vibemix.runtime.settings import SettingsApplier
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
        _settings_config = load_config()
        _live_settings_applier = SettingsApplier(
            config_store=_settings_config,
            music_state=state,  # mood applies live + emits mascot.mood_change
            ws_bus=ipc_router,  # mood-change + acks reach every connected client
            recordings_root=recordings_root,
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
    lesson_runtime = LessonRuntime(
        learn_state=_learn_state,
        midi_mirror=midi_mirror,
        controller_state=midi_macos.controller_state,
        ipc_router=_lesson_ipc_adapter,
        progress_store=_learn_progress,
    )
    print("-> lesson_runtime wired", file=sys.stderr)

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
            ipc_bus=citation_shim,
            citation_telemetry=_citation_telemetry if anti_slop_enabled else None,
            suggestion_service=suggestion_service,
            tracer=tracer,
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
        channels=2,
        block_size=INPUT_CHUNK_FRAMES,
        callback=_input_callback_factory(
            levels, passthrough, mic, audio_buf, clean_audio_buf, recorder
        ),
    )
    print(f"-> listening to {INPUT_DEVICE} @ {INPUT_SR_NATIVE}Hz -> audio_buf + clean_audio_buf")

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


def _run_library_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="vibemix library")
    _build_library_subparsers(parser)
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


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

    result = chat_with_codex(args.message, lib, history=history)
    _json.dump(result.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    print(
        f"-> viber chat [codex] ({len(result.tools_used)} tools, stop={result.stop_reason})",
        file=sys.stderr,
    )
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
        print(_json.dumps(out, indent=2), file=sys.stderr)
        hint = {
            "codex_not_installed": (
                "Install Codex: `npm i -g @openai/codex` (or `brew install "
                "codex`), then `codex login`."
            ),
            "codex_auth_required": "Run `codex login` to connect your ChatGPT plan.",
            "timeout": "Codex took too long — try a narrower theme.",
        }.get(result.stop_reason, result.error or "no playlist created")
        print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
        return 1

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
        print(_json.dumps(out, indent=2), file=sys.stderr)
        hint = {
            "codex_not_installed": (
                "Install Codex: `npm i -g @openai/codex` (or `brew install "
                "codex`), then `codex login`."
            ),
            "codex_auth_required": "Run `codex login` to connect your ChatGPT plan.",
            "timeout": "Codex took too long — try a narrower brief.",
        }.get(result.stop_reason, result.error or "no set created")
        print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
        return 1

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
